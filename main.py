import argparse
import time
from pathlib import Path

from ultralytics import YOLO

from agent import format_agent_response, reason_with_agent
from evaluation import (
    BaselineEvaluator,
    EvaluationLogger,
    FrameMetric,
    expected_action_for_class,
    is_action_correct,
)
from mcp import execute_action
from rag import query_rag
from utils import discover_videos, extract_frames

model = YOLO("yolov8n.pt")
TARGET_CLASSES = ["Abuse", "Arrest", "Arson", "Assault"]


def detect_objects(frame, confidence_threshold=0.25):
    results = model(frame, verbose=False)
    detections = []

    for result in results:
        for box in result.boxes:
            conf = float(box.conf)
            if conf < confidence_threshold:
                continue
            cls = int(box.cls)
            label = model.names[cls]
            detections.append(label)

    return sorted(set(detections))


def convert_to_text(detections, class_hint=None):
    detection_set = set(detections)
    weapons = {"knife", "scissors", "baseball bat", "gun"}
    fire_related = {"fire", "smoke"}

    if detection_set & fire_related or class_hint == "Arson":
        base_event = "possible arson incident"
    elif detection_set & weapons or class_hint == "Assault":
        base_event = "possible assault incident"
    elif class_hint == "Abuse":
        base_event = "possible abuse incident"
    elif class_hint == "Arrest":
        base_event = "possible arrest incident"
    elif "person" in detection_set:
        base_event = "person detected"
    else:
        base_event = "normal scene"

    object_summary = ", ".join(detections[:8]) if detections else "none"
    if class_hint:
        return f"{base_event} in {class_hint.lower()} context; objects: {object_summary}"
    return f"{base_event}; objects: {object_summary}"


def run_pipeline(
    video_path,
    frame_stride=30,
    class_hint=None,
    confidence_threshold=0.25,
    eval_logger=None,
    baseline_mode=None,
):
    frames = extract_frames(video_path)

    if not frames:
        print(f"Skipping empty or unreadable video: {video_path}")
        return

    print(f"Processing video: {video_path}")
    print(f"Baseline mode: {baseline_mode if baseline_mode else 'Full (Agent + RAG)'}")
    
    frame_count = 0
    for frame_idx, frame in enumerate(frames[::frame_stride]):
        frame_start = time.time()
        frame_count += 1
        detections = detect_objects(frame, confidence_threshold=confidence_threshold)
        text = convert_to_text(detections, class_hint=class_hint)

        rag_action = query_rag(text)

        if baseline_mode == "rag_only":
            decision = BaselineEvaluator.baseline_rag_only(rag_action)
        elif baseline_mode == "detection_only":
            decision = BaselineEvaluator.baseline_detection_only(detections, class_hint)
        else:
            decision = reason_with_agent(text, detections, rag_action, class_hint=class_hint)

        mcp_action = execute_action(rag_action, detections=detections)
        expected_action = expected_action_for_class(class_hint)
        action_correct = is_action_correct(expected_action, decision.get("primary_action", ""))
        frame_total_time_ms = round((time.time() - frame_start) * 1000, 2)

        print(f"Frame {frame_count}: {text}")
        print(f"  → Agent: {format_agent_response(decision)}")
        print(f"  → MCP: {mcp_action}")
        print(f"  → Eval: expected='{expected_action}', correct={action_correct}, total={frame_total_time_ms}ms")

        if eval_logger:
            metric = FrameMetric(
                run_id=eval_logger.run_id,
                baseline_mode=baseline_mode or "full_agent_rag",
                video_path=str(video_path),
                class_hint=class_hint or "unknown",
                frame_index=frame_idx,
                detections=detections,
                event_text=text,
                rag_action=rag_action,
                mcp_action=mcp_action,
                agent_severity=decision.get("severity", "unknown"),
                agent_confidence=decision.get("confidence", 0.0),
                agent_primary_action=decision.get("primary_action", "N/A"),
                expected_action=expected_action,
                action_correct=action_correct,
                inference_time_ms=decision.get("inference_time_ms", 0.0),
                frame_total_time_ms=frame_total_time_ms,
                timestamp=time.time(),
            )
            eval_logger.log_frame(metric)

        print("------")


def run_dataset(
    data_root,
    class_names,
    frame_stride=30,
    max_videos_per_class=1,
    confidence_threshold=0.25,
    eval_logger=None,
    baseline_mode=None,
):
    videos = discover_videos(
        data_root=data_root,
        class_names=class_names,
        max_videos_per_class=max_videos_per_class,
    )

    if not videos:
        raise FileNotFoundError(
            f"No videos found in {data_root} for classes: {', '.join(class_names)}"
        )

    print(f"Found {len(videos)} videos across classes: {', '.join(class_names)}")
    for class_name, video_path in videos:
        print(f"\n=== Class: {class_name} ===")
        run_pipeline(
            str(video_path),
            frame_stride=frame_stride,
            class_hint=class_name,
            confidence_threshold=confidence_threshold,
            eval_logger=eval_logger,
            baseline_mode=baseline_mode,
        )

    if eval_logger:
        print("\n=== Evaluation Summary ===")
        summary = eval_logger.get_summary()
        if summary:
            print(f"Run ID: {summary['run_id']}")
            print(f"Total frames processed: {summary['total_frames']}")
            print(f"Unique videos: {summary['unique_videos']}")
            print(f"Decision accuracy: {summary['decision_accuracy']:.2%}")
            print(f"Avg inference time: {summary['avg_inference_time_ms']:.2f}ms")
            print(f"Avg frame total time: {summary['avg_frame_total_time_ms']:.2f}ms")
            print(f"Avg confidence: {summary['avg_confidence']:.2%}")
            print(f"Severity distribution: {summary['severity_distribution']}")
            if summary.get("csv_path"):
                print(f"CSV log: {summary['csv_path']}")
            if summary.get("jsonl_path"):
                print(f"JSONL log: {summary['jsonl_path']}")


def parse_args():
    parser = argparse.ArgumentParser(description="YOLO -> RAG -> MCP -> Agent pipeline")
    parser.add_argument(
        "--video",
        type=str,
        default=None,
        help="Path to one input video. If omitted, dataset mode is used.",
    )
    parser.add_argument(
        "--data-root",
        type=str,
        default="data/ucf_crime",
        help="Dataset root folder with class subfolders.",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        default=TARGET_CLASSES,
        help="Class folders to include (default: Abuse Arrest Arson Assault).",
    )
    parser.add_argument(
        "--max-videos-per-class",
        type=int,
        default=1,
        help="Maximum videos to process per class in dataset mode.",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=30,
        help="Process every Nth frame",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Minimum YOLO confidence threshold.",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Enable structured evaluation logging (JSONL/CSV, one-by-one real-time).",
    )
    parser.add_argument(
        "--log-format",
        type=str,
        choices=["csv", "jsonl", "both"],
        default="both",
        help="Logging format for evaluation output.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional custom run id for log files.",
    )
    parser.add_argument(
        "--max-log-runs",
        type=int,
        default=20,
        help="Max number of run log files retained in eval_results/runs.",
    )
    parser.add_argument(
        "--baseline",
        type=str,
        choices=["rag_only", "detection_only"],
        default=None,
        help="Run baseline comparison (rag_only or detection_only).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    eval_logger = None
    if args.eval:
        eval_logger = EvaluationLogger(
            run_id=args.run_id,
            log_format=args.log_format,
            max_log_runs=args.max_log_runs,
        )

    if args.video:
        video_file = Path(args.video)
        if not video_file.exists():
            raise FileNotFoundError(f"Video file not found: {video_file}")

        class_hint = video_file.parent.name if video_file.parent.name in TARGET_CLASSES else None
        run_pipeline(
            str(video_file),
            frame_stride=args.stride,
            class_hint=class_hint,
            confidence_threshold=args.conf,
            eval_logger=eval_logger,
            baseline_mode=args.baseline,
        )
        if eval_logger:
            summary = eval_logger.get_summary()
            if summary:
                print("\n=== Evaluation Summary ===")
                print(f"Run ID: {summary['run_id']}")
                print(f"Total frames processed: {summary['total_frames']}")
                print(f"Decision accuracy: {summary['decision_accuracy']:.2%}")
                print(f"Avg inference time: {summary['avg_inference_time_ms']:.2f}ms")
                print(f"Avg frame total time: {summary['avg_frame_total_time_ms']:.2f}ms")
                if summary.get("csv_path"):
                    print(f"CSV log: {summary['csv_path']}")
                if summary.get("jsonl_path"):
                    print(f"JSONL log: {summary['jsonl_path']}")
    else:
        run_dataset(
            data_root=args.data_root,
            class_names=args.classes,
            frame_stride=args.stride,
            max_videos_per_class=args.max_videos_per_class,
            confidence_threshold=args.conf,
            eval_logger=eval_logger,
            baseline_mode=args.baseline,
        )
