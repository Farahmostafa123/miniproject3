from flask import Flask, jsonify
from flask_cors import CORS
import json, os, glob
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from the dashboard HTML page

OUTPUT_DIR = '/data/output'
def read_latest_json_files(directory: str, limit: int = 20) -> list:
    """Read the N most recently created JSON files from a directory."""
    files = sorted(
        glob.glob(f'{directory}/**/*.json', recursive=True) +
        glob.glob(f'{directory}/*.json'),
        key=os.path.getmtime,
        reverse=True
    )[:limit]

    records = []
    for f in files:
        try:
            with open(f) as fp:
                data = json.load(fp)
                if isinstance(data, list):
                    records.extend(data)
                else:
                    records.append(data)
        except Exception:
            pass  # Skip corrupt files
    return records


def read_latest_jsonl_files(directory: str, limit: int = 200) -> list:
    """Read newline-delimited JSON (Spark output format)."""
    files = sorted(
        glob.glob(f'{directory}/*.json'),
        key=os.path.getmtime,
        reverse=True
    )[:10]

    records = []
    for f in files:
        try:
            with open(f) as fp:
                for line in fp:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except Exception:
                            pass
        except Exception:
            pass
    return records[:limit]

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.utcnow().isoformat()})


@app.route('/api/recommendations')
def recommendations():
    """Return the latest recommendations from all epochs."""
    records = read_latest_json_files(f'{OUTPUT_DIR}/recommendations', limit=10)

    # Flatten all recommendations from all epoch files
    all_recs = []
    latencies = []
    for record in records:
        if 'recommendations' in record:
            all_recs.extend(record['recommendations'])
        if 'latency_ms' in record:
            latencies.append(record['latency_ms'])

    # Count strategies
    als_count  = sum(1 for r in all_recs if r.get('strategy') == 'ALS')
    cold_count = sum(1 for r in all_recs if r.get('strategy') == 'POPULARITY_FALLBACK')

    return jsonify({
        'total': len(all_recs),
        'als_count': als_count,
        'cold_start_count': cold_count,
        'avg_latency_ms': round(sum(latencies) / len(latencies), 1) if latencies else 0,
        'max_latency_ms': max(latencies) if latencies else 0,
        'latest': all_recs[:50],  # Return most recent 50
    })


@app.route('/api/window_stats')
def window_stats():
    """Return windowed item analytics."""
    records = read_latest_jsonl_files(f'{OUTPUT_DIR}/window_stats', limit=100)

    # Sort by engagement_score descending
    records.sort(key=lambda x: x.get('engagement_score', 0), reverse=True)

    # Top trending items by engagement score
    trending = records[:10]

    # Compute summary stats
    if records:
        avg_rating = sum(r.get('avg_rating', 0) for r in records) / len(records)
        total_interactions = sum(r.get('interaction_count', 0) for r in records)
    else:
        avg_rating = 0
        total_interactions = 0

    return jsonify({
        'total_windows': len(records),
        'overall_avg_rating': round(avg_rating, 3),
        'total_interactions': total_interactions,
        'trending_items': trending,
        'all_stats': records[:50],
    })


@app.route('/api/alerts')
def alerts():
    """Return all recent alerts (trending items + activity spikes)."""
    item_alerts = read_latest_jsonl_files(f'{OUTPUT_DIR}/alerts/items', limit=50)
    user_alerts = read_latest_jsonl_files(f'{OUTPUT_DIR}/alerts/users', limit=50)

    all_alerts = []
    for a in item_alerts:
        a['category'] = 'TRENDING_ITEM'
        all_alerts.append(a)
    for a in user_alerts:
        a['category'] = 'ACTIVITY_SPIKE'
        all_alerts.append(a)

    # Sort by alert_time descending
    all_alerts.sort(key=lambda x: x.get('alert_time', ''), reverse=True)

    return jsonify({
        'total': len(all_alerts),
        'trending_item_count': len(item_alerts),
        'activity_spike_count': len(user_alerts),
        'alerts': all_alerts[:30],
    })


@app.route('/api/metrics')
def metrics():
    """Return high-level system metrics for the dashboard header."""
    rec_records  = read_latest_json_files(f'{OUTPUT_DIR}/recommendations', limit=5)
    stat_records = read_latest_jsonl_files(f'{OUTPUT_DIR}/window_stats',   limit=20)

    total_recs    = sum(len(r.get('recommendations', [])) for r in rec_records)
    latencies     = [r['latency_ms'] for r in rec_records if 'latency_ms' in r]
    avg_latency   = round(sum(latencies) / len(latencies), 1) if latencies else 0

    total_interactions = sum(r.get('interaction_count', 0) for r in stat_records)
    avg_engagement     = 0
    if stat_records:
        scores = [r.get('engagement_score', 0) for r in stat_records if r.get('engagement_score')]
        avg_engagement = round(sum(scores) / len(scores), 4) if scores else 0

    return jsonify({
        'total_recommendations_served': total_recs,
        'avg_latency_ms': avg_latency,
        'total_interactions_streamed': total_interactions,
        'avg_engagement_score': avg_engagement,
        'stream_active': os.path.exists(f'{OUTPUT_DIR}/recommendations'),
        'last_updated': datetime.utcnow().isoformat() + 'Z',
    })


if __name__ == '__main__':
    os.makedirs(f'{OUTPUT_DIR}/recommendations', exist_ok=True)
    os.makedirs(f'{OUTPUT_DIR}/alerts/items',    exist_ok=True)
    os.makedirs(f'{OUTPUT_DIR}/alerts/users',    exist_ok=True)
    os.makedirs(f'{OUTPUT_DIR}/window_stats',    exist_ok=True)
    print('Dashboard API starting on port 5050...')
    app.run(host='0.0.0.0', port=5050, debug=False)