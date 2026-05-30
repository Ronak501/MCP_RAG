import csv
import json
from pathlib import Path

RUNS_DIR = Path("eval_results/runs")
OUT_PATH = Path("eval_results/final_conclusions.csv")

THRESHOLD = 0.55
MIN_SEG_LEN = 2

files = sorted(RUNS_DIR.glob('run_*.csv'))

results = []

for f in files:
    with f.open('r', encoding='utf-8') as fh:
        reader = csv.reader(fh)
        header = next(reader)
        if 'anomaly_score' not in header:
            continue
        idx = header.index('anomaly_score')
        vid_idx = header.index('video_path') if 'video_path' in header else None
        frame_idx = header.index('frame_index') if 'frame_index' in header else None
        rag_idx = header.index('rag_action') if 'rag_action' in header else None
        mcp_idx = header.index('mcp_action') if 'mcp_action' in header else None

        rows_by_video = {}
        for row in reader:
            try:
                a = float(row[idx])
            except Exception:
                continue
            video = row[vid_idx]
            fi = int(row[frame_idx]) if frame_idx is not None else None
            rag = row[rag_idx] if rag_idx is not None else ''
            mcp = row[mcp_idx] if mcp_idx is not None else ''
            rows_by_video.setdefault(video, []).append({
                'frame_index': fi,
                'anomaly': a,
                'rag_action': rag,
                'mcp_action': mcp,
                'row': row,
            })

        for video, rows in rows_by_video.items():
            rows_sorted = sorted(rows, key=lambda r: (r['frame_index'] is None, r['frame_index']))
            vals = [r['anomaly'] for r in rows_sorted]
            mean_anom = sum(vals)/len(vals) if vals else 0.0
            peak_anom = max(vals) if vals else 0.0
            peak_idx = next((r['frame_index'] for r in rows_sorted if r['anomaly']==peak_anom), None)
            peak_row = next((r for r in rows_sorted if r['anomaly']==peak_anom), None)

            # find temporal segments
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
            # finalize
            if seg_start is not None:
                length = len(seg_scores)
                if length >= MIN_SEG_LEN:
                    segments.append({'start': seg_start, 'end': rows_sorted[-1]['frame_index'], 'length': length, 'mean': sum(seg_scores)/length, 'peak': max(seg_scores)})

            anomaly_detected = len(segments) > 0
            rag_at_peak = peak_row['rag_action'] if peak_row else ''
            mcp_at_peak = peak_row['mcp_action'] if peak_row else ''
            suggested_action = mcp_at_peak if mcp_at_peak else rag_at_peak

            results.append({
                'run_file': f.name,
                'video_path': video,
                'anomaly_detected': anomaly_detected,
                'peak_anomaly': round(peak_anom,4),
                'mean_anomaly': round(mean_anom,4),
                'peak_frame_index': peak_idx,
                'rag_action_at_peak': rag_at_peak,
                'mcp_action_at_peak': mcp_at_peak,
                'suggested_action': suggested_action,
                'temporal_segments': json.dumps(segments),
            })

# write CSV
with OUT_PATH.open('w', newline='', encoding='utf-8') as out:
    writer = csv.writer(out)
    writer.writerow(['run_file','video_path','anomaly_detected','peak_anomaly','mean_anomaly','peak_frame_index','rag_action_at_peak','mcp_action_at_peak','suggested_action','temporal_segments'])
    for r in results:
        writer.writerow([r['run_file'], r['video_path'], r['anomaly_detected'], r['peak_anomaly'], r['mean_anomaly'], r['peak_frame_index'], r['rag_action_at_peak'], r['mcp_action_at_peak'], r['suggested_action'], r['temporal_segments']])

print('Wrote', OUT_PATH, 'with', len(results), 'rows')
