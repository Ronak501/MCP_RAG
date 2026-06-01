import csv
import json
from pathlib import Path

RUNS_DIR = Path("eval_results/runs")
OUT_PATH = Path("eval_results/final_conclusions.csv")

THRESHOLD = 0.55
MIN_SEG_LEN = 2
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}


def collect_run_rows():
    files = sorted(RUNS_DIR.glob('run_*.csv'))
    all_rows = []
    for f in files:
        try:
            with f.open('r', encoding='utf-8') as fh:
                reader = csv.reader(fh)
                header = next(reader)
                # try to locate expected columns
                if 'anomaly_score' not in header:
                    continue
                idx = header.index('anomaly_score')
                vid_idx = header.index('video_path') if 'video_path' in header else None
                frame_idx = header.index('frame_index') if 'frame_index' in header else None
                rag_idx = header.index('rag_action') if 'rag_action' in header else None
                mcp_idx = header.index('mcp_action') if 'mcp_action' in header else None

                for row in reader:
                    try:
                        a = float(row[idx])
                    except Exception:
                        continue
                    video = row[vid_idx] if vid_idx is not None else ''
                    fi = int(row[frame_idx]) if frame_idx is not None and row[frame_idx] else None
                    rag = row[rag_idx] if rag_idx is not None else ''
                    mcp = row[mcp_idx] if mcp_idx is not None else ''
                    all_rows.append({
                        'run_file': f.name,
                        'video_path': video,
                        'frame_index': fi,
                        'anomaly': a,
                        'rag_action': rag,
                        'mcp_action': mcp,
                        'row': row,
                    })
        except Exception:
            continue
    return all_rows


def find_videos(root=Path('data')):
    vids = []
    if not root.exists():
        return vids
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS:
            vids.append(p)
    return sorted(vids)


def aggregate_for_video(video_name, rows):
    # rows: list of dicts for this video
    if not rows:
        return {
            'video_path': video_name,
            'anomaly_detected': False,
            'peak_anomaly': 0.0,
            'mean_anomaly': 0.0,
            'peak_frame_index': None,
            'rag_action_at_peak': '',
            'mcp_action_at_peak': '',
            'suggested_action': '',
            'temporal_segments': json.dumps([]),
            'source_runs': json.dumps([]),
        }

    rows_sorted = sorted(rows, key=lambda r: (r['frame_index'] is None, r['frame_index']))
    vals = [r['anomaly'] for r in rows_sorted]
    mean_anom = sum(vals)/len(vals) if vals else 0.0
    peak_anom = max(vals) if vals else 0.0
    peak_row = next((r for r in rows_sorted if r['anomaly']==peak_anom), None)

    # temporal segments
    segments = []
    seg_start = None
    seg_scores = []
    for r in rows_sorted:
        if r['anomaly'] >= THRESHOLD:
            if seg_start is None:
                seg_start = r['frame_index']
                seg_scores = [r['anomaly']]
            else:
                seg_scores.append(r['anomaly'])
        else:
            if seg_start is not None:
                length = len(seg_scores)
                if length >= MIN_SEG_LEN:
                    segments.append({'start': seg_start, 'end': r['frame_index']-1, 'length': length, 'mean': sum(seg_scores)/length, 'peak': max(seg_scores)})
                seg_start = None
                seg_scores = []
    if seg_start is not None:
        length = len(seg_scores)
        if length >= MIN_SEG_LEN:
            segments.append({'start': seg_start, 'end': rows_sorted[-1]['frame_index'], 'length': length, 'mean': sum(seg_scores)/length, 'peak': max(seg_scores)})

    anomaly_detected = len(segments) > 0
    rag_at_peak = peak_row['rag_action'] if peak_row else ''
    mcp_at_peak = peak_row['mcp_action'] if peak_row else ''
    suggested_action = mcp_at_peak if mcp_at_peak else rag_at_peak

    return {
        'video_path': video_name,
        'anomaly_detected': anomaly_detected,
        'peak_anomaly': round(peak_anom,4),
        'mean_anomaly': round(mean_anom,4),
        'peak_frame_index': peak_row['frame_index'] if peak_row else None,
        'rag_action_at_peak': rag_at_peak,
        'mcp_action_at_peak': mcp_at_peak,
        'suggested_action': suggested_action,
        'temporal_segments': json.dumps(segments),
        'source_runs': json.dumps(sorted({r['run_file'] for r in rows})),
    }


def main():
    rows = collect_run_rows()
    videos = find_videos()

    # map by video identifier (try full path match first, then filename)
    rows_by_video = {}
    for r in rows:
        key = r['video_path'] or ''
        rows_by_video.setdefault(key, []).append(r)

    results = []
    for v in videos:
        v_str = v.as_posix()
        v_name = v.name
        matched = []
        # prefer exact match
        if v_str in rows_by_video:
            matched = rows_by_video[v_str]
        else:
            # fallback: match by filename substring
            for k, rs in rows_by_video.items():
                if not k:
                    continue
                if v_name in k or k in v_str:
                    matched.extend(rs)

        agg = aggregate_for_video(v_str, matched)
        results.append(agg)

    # also include videos that only appear in runs but not on disk
    seen_video_keys = {r['video_path'] for r in rows}
    for key in seen_video_keys:
        if not key:
            continue
        if any(r['video_path'] == key for r in rows) and not any(key == res['video_path'] for res in results):
            matched = [r for r in rows if r['video_path'] == key]
            results.append(aggregate_for_video(key, matched))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open('w', newline='', encoding='utf-8') as out:
        writer = csv.writer(out)
        writer.writerow(['video_path','anomaly_detected','peak_anomaly','mean_anomaly','peak_frame_index','rag_action_at_peak','mcp_action_at_peak','suggested_action','temporal_segments','source_runs'])
        for r in results:
            writer.writerow([r['video_path'], r['anomaly_detected'], r['peak_anomaly'], r['mean_anomaly'], r['peak_frame_index'], r['rag_action_at_peak'], r['mcp_action_at_peak'], r['suggested_action'], r['temporal_segments'], r['source_runs']])

    print('Wrote', OUT_PATH, 'with', len(results), 'rows')


if __name__ == '__main__':
    main()
