# Real-Time E-Commerce Recommendation System
**Big Data Analytics — Mini Project 3**  
Domain: Amazon E-Commerce Products | Focus: Personalization (Cold-Start + User Segmentation)

---

## System Architecture

```
Amazon Electronics CSV (1.6M reviews)
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BATCH LAYER (Notebook 1)                                           │
│  Spark MLlib ALS ──► Trained Model ──► /data/als_model             │
│  User Segmentation ──► /data/user_segments                         │
│  Popularity Fallback ──► /data/popularity_fallback                 │
└─────────────────────────────────────────────────────────────────────┘
         │                                │
         ▼                                ▼
┌─────────────────┐            ┌──────────────────────────────────────┐
│  KAFKA PRODUCER │            │  STREAMING LAYER (Notebook 3)        │
│  (Notebook 2)   │ ─events──► │  Spark Structured Streaming          │
│                 │            │  ├── Window Analytics (30s/10s)      │
│  P0: cold_start │            │  ├── ALS Recommendations             │
│  P1: power/reg  │            │  ├── Popularity Fallback (cold-start)│
└─────────────────┘            │  ├── Alert System                    │
                               │  └── Late Data (Watermark 2min)      │
                               └──────────────────────────────────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │  DASHBOARD           │
                               │  Flask API :5050     │
                               │  index.html          │
                               └──────────────────────┘
```

---

## Prerequisites
- Docker Desktop (4GB+ RAM recommended)
- ~10GB free disk space (Spark images are large)

---

## Quick Start

### Step 1 — Build and start all containers
```bash
docker-compose up --build -d
```
Wait ~3 minutes for Spark to initialize. Check status:
```bash
docker-compose logs -f spark-master
```

### Step 2 — Verify services are running
| Service | URL |
|---------|-----|
| JupyterLab | http://localhost:8888 |
| Spark Master UI | http://localhost:8080 |
| Spark Worker 1 UI | http://localhost:8081 |
| Spark Worker 2 UI | http://localhost:8082 |
| Spark App UI | http://localhost:4040 (active during job) |
| Dashboard | Open `dashboard/index.html` in browser |
| Dashboard API | http://localhost:5050/api/health |

### Step 3 — Run Notebook 1 (Data + ALS Training)
1. Open http://localhost:8888
2. Open `notebooks/01_data_preprocessing_and_als.ipynb`
3. Run all cells top to bottom
4. Expect ~15-20 minutes for download + training
5. Final output: `RMSE: X.XXXX` — should be < 1.5

### Step 4 — Start Streaming (Notebook 3 FIRST, then Notebook 2)
1. Open `notebooks/03_spark_streaming.ipynb` in a new tab
2. Run all cells — leave the monitor cell running
3. Open `notebooks/02_kafka_producer.ipynb` in another new tab
4. Run all cells — watch events flow in Notebook 3's output

### Step 5 — Open Dashboard
Open `dashboard/index.html` directly in your browser.
It auto-refreshes every 5 seconds from the Flask API.

---

## Dataset Details

**Amazon Product Reviews — Electronics**
- Source: UCSD Julian McAuley Research Lab
- URL: https://snap.stanford.edu/data/amazon/productGraph/categoryFiles/ratings_Electronics.csv
- Size: ~1.69 million reviews
- Format: `user_id (str), item_id (str), rating (float), timestamp (unix int)`
- Time range: 1998–2014

**Why distributed processing is needed:**
- 1.69M rows × string ID encoding → cannot fit in single-node memory for ALS matrix factorization
- Collaborative filtering requires O(users × items × rank) factor matrices
- Window analytics over streaming data require parallel partition processing

---

## Partitioning Strategy

2 Kafka partitions routed by user segment:
- **Partition 0** → `cold_start` users (5–9 historical ratings)
- **Partition 1** → `power_user` (≥20) and `regular_user` (10–19)

**Justification:** Each partition is handled by a separate Spark executor. Since cold-start users need a completely different code path (popularity fallback instead of ALS), keeping them in a separate partition avoids contention and improves cache locality for the ALS model lookup in Partition 1.

---

## Cold-Start Handling

| Segment | Criteria | Strategy |
|---------|----------|----------|
| `power_user` | ≥ 20 ratings | Full ALS Top-5 |
| `regular_user` | 10–19 ratings | ALS Top-5 |
| `cold_start` | 5–9 ratings | Top-5 from popularity Bayesian ranking |
| `new_user` | 0–4 ratings (streaming only) | Popularity fallback |

**Popularity score formula:**
```
bayesian_score = (count × avg_rating + 50 × global_mean) / (count + 50)
```
The constant `50` smooths scores for items with few ratings toward the global mean.

---

## Custom Streaming Metric: Engagement Score

```
engagement_score = (avg_rating / 5.0) × log(interaction_count + 1)
```

**Interpretation:** An item with avg_rating=4.8 and 1 interaction scores lower than an item with avg_rating=4.5 and 20 interactions. This rewards items that are both well-rated AND actively engaged with in the current time window.

---

## Late Data Handling

Watermark is set to **2 minutes** in Notebook 3:
```python
.withWatermark('event_time', '2 minutes')
```
- Events arriving ≤ 2 minutes late → **processed** in their correct window
- Events arriving > 2 minutes late → **dropped** (not included in any window)
- The Kafka producer injects 5% late events (60–120 seconds old) for testing

---

## Alert Thresholds

| Alert Type | Trigger | Example |
|------------|---------|---------|
| TRENDING_ITEM | `avg_rating > 4.5` AND `interactions ≥ 3` in 30s window | `ALERT: Item 120 is trending! avg_rating=4.8, interactions=15` |
| ACTIVITY_SPIKE | `interaction_count > 8` per user in 30s window | `ALERT: User 42 spike! 11 interactions in 30s window` |

---

## Stopping the System
```bash
# Stop just the streaming (in Jupyter: hit ■ Stop button)
# Then stop all containers:
docker-compose down

# To also remove volumes (clean slate):
docker-compose down -v
```
