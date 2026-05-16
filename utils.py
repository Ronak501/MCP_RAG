import cv2
from pathlib import Path


SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov"}


def extract_frames(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)

    cap.release()
    return frames


def discover_videos(data_root, class_names=None, max_videos_per_class=None):
    root = Path(data_root)
    if not root.exists():
        raise FileNotFoundError(f"Data root not found: {root}")

    classes = class_names or [d.name for d in root.iterdir() if d.is_dir()]
    videos = []

    for class_name in classes:
        class_dir = root / class_name
        if not class_dir.exists() or not class_dir.is_dir():
            continue

        class_videos = sorted(
            p
            for p in class_dir.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
        )

        if max_videos_per_class is not None:
            class_videos = class_videos[:max_videos_per_class]

        for video in class_videos:
            videos.append((class_name, video))

    return videos
