# Movie Recommender via Neural Collaborative Filtering (NeuMF)

A full-stack movie recommendation system built on **MovieLens 20M**: a PyTorch NeuMF model
(GMF + MLP, per He et al., WWW 2017) benchmarked against matrix-factorization and popularity
baselines, served through FastAPI over PostgreSQL, with a React analytics dashboard that
reports only measured results.

**Polaris School of Technology — On-the-Job Training project**
Student: Ipshita Baral (MS240410700118) · Mentor: Kanak Upadhyay · Track: Advanced Data Science

---

## 1. Project overview

The system learns user and movie representations from 20 million explicit ratings and uses them to

- generate personalised **Top-N recommendations** (excluding anything the user has already seen),
- predict a **calibrated 0.5–5.0 star rating** for a given user/movie pair,
- compare **NeuMF against a matrix-factorization baseline and a popularity baseline** under one
  evaluation protocol, and
- expose all of it through a REST API and a cinematic React front end with an ML analytics dashboard.

## 2. Problem statement

Recommendation stacks built on classical collaborative filtering score a user–item pair with a
**fixed inner product**. That functional form cannot represent the non-linear structure in real
preference data, which caps the relevance of "top picks for you" surfaces. Neural Collaborative
Filtering replaces the inner product with a learned interaction function: a generalized
matrix-factorization branch preserves the linear view, an MLP branch learns an arbitrary one, and
NeuMF fuses the two.

## 3. Project objectives

| Objective | Status |
|---|---|
| Train NeuMF on MovieLens and learn latent user/item representations | Done — see §12 |
| Strong HR@10 / NDCG@10 under leave-one-out, benchmarked against MF | Done — **HR@10 0.9087**, +5.04% over MF |
| Serve recommendations with inference latency under 200 ms | Done — measured **p50 2.73 ms / p95 3.17 ms** (§17) |
| Full-stack demo: PyTorch + FastAPI + React, dashboard, auth, reproducible docs | Done |

## 4. Dataset source

[MovieLens 20M](https://grouplens.org/datasets/movielens/20m/) (GroupLens), downloaded directly from
`https://files.grouplens.org/datasets/movielens/ml-20m.zip`. Used under the GroupLens research
licence. The data is already anonymised; the application stores no personal data beyond the
account details a demo user supplies.

Files used: `ratings.csv`, `movies.csv`, `links.csv` (for TMDB ids), `tags.csv` (counted only).

## 5. Dataset version clarification — please read

> The PRD specifies **MovieLens 25M**. This project uses **MovieLens 20M**, which is the dataset
> that was actually supplied (the Kaggle MovieLens 20M release) and the one the original Colab
> notebook was built on. Every number in this repository comes from MovieLens 20M.
> **No result here was produced on MovieLens 25M.**

This deviation is surfaced in three places so it cannot be overlooked: `/model/info` and `/metrics`
responses, the analytics dashboard banner, and the footer of every application page.

Measured dataset shape after cleaning and filtering:

| Quantity | Value |
|---|---|
| Raw ratings | 20,000,263 |
| Ratings after cleaning | 20,000,263 (0 removed — no missing values, duplicates or orphan ids) |
| Ratings after the ≥5 activity filter | **19,984,024** |
| Users | **138,493** |
| Movies in the model index | **18,345** (27,278 in the raw catalog) |
| Sparsity | **99.213%** (2,540,654,085 cells if dense) |
| Positive interactions (rating ≥ 4.0) | 9,991,556 (49.998%) |
| Global mean rating (train) | 3.5239 |

## 6. System architecture

```
MovieLens 20M (ratings · movies · links)
        │
        ▼
┌───────────────────────────────┐
│ Preprocessing (ml/preprocessing)
│  clean → filter(≥5) → re-index → leave-one-out split
│  → Parquet splits, mappings, seen-indexes, EDA summary
└───────────────────────────────┘
        │
        ├──────────────┬────────────────────┬──────────────────┐
        ▼              ▼                    ▼                  ▼
  Popularity      Matrix Factorization    NeuMF            RatingPredictor
  (train counts)  (dot product + bias)  (GMF ⊕ MLP)     (NeuMF trunk + σ head)
        │              │                    │                  │
        └──────────────┴─────────┬──────────┴──────────────────┘
                                 ▼
                  Evaluation on ONE shared candidate file
                  HR@10 · NDCG@10 · Precision · Recall · F1 · ROC-AUC · RMSE
                                 │
                                 ▼
              artifacts/ (checkpoints · mappings · metrics · metadata)
                                 │
                                 ▼
        ┌────────────────────────────────────────┐
        │ FastAPI (backend/app)                  │
        │  loads checkpoints once on CPU         │──► PostgreSQL
        │  auth · recommendations · predict      │    (users, movies, ratings,
        │  metrics · movies · users · fold-in    │     preferences, history,
        └────────────────────────────────────────┘     embeddings, TMDB cache)
                                 │ REST + JWT
                                 ▼
        ┌────────────────────────────────────────┐
        │ React + Vite + Tailwind (frontend/)    │
        │  landing · auth · onboarding · discover│
        │  browse · detail · recommendations     │
        │  profile · ML analytics dashboard      │
        └────────────────────────────────────────┘
```

## 7. NeuMF architecture

Two branches that deliberately **do not share embeddings** (`ml/models/neumf.py`):

**GMF branch** — user embedding ⊙ item embedding (element-wise product), dimension 32.
This generalizes matrix factorization: with an identity output layer it *is* MF.

**MLP branch** — a second, independent pair of 32-dimensional embeddings, concatenated into a
64-dimensional vector and passed through `64 → 32 → 16` fully-connected layers with ReLU and
dropout 0.1.

**NeuMF fusion** — the 32-dimensional GMF vector and the 16-dimensional MLP vector are
concatenated into 48 dimensions and mapped by a single linear layer to one logit.

```
user ──┬─► GMF user emb (32) ──┐
       │                        ⊙ ──────────────► (32) ──┐
item ──┼─► GMF item emb (32) ──┘                         ├─► concat (48) ─► Linear ─► logit
       ├─► MLP user emb (32) ──┐                         │
       └─► MLP item emb (32) ──┴─► concat (64) ─► 64→32→16 ─┘
```

The output is a **ranking logit**, not a rating. It is never displayed as stars anywhere in the
application — see §9.

## 8. Data preprocessing methodology

`ml/preprocessing/run_preprocessing.py` is a reproducible port of the original Colab notebook
(preserved at `notebooks/movielens20m_with_baselines_simple_3.ipynb`). All thresholds are
unchanged from that notebook and recorded in `artifacts/metrics/preprocessing_config.json`.

1. **Validation** — dimensions, dtypes, rating range, timestamp range.
2. **Missing values / duplicates / orphan ids** — quantified before anything is dropped. All four
   came back zero on this dataset.
3. **Cleaning** — drop null key fields, keep ratings within 0.5–5.0, drop exact duplicates, drop
   ratings whose movie is absent from `movies.csv`.
4. **Activity filtering** — `MIN_USER_RATINGS = 5`, `MIN_MOVIE_RATINGS = 5`, applied explicitly and
   recorded, not silently.
5. **Re-indexing** — `user_idx ∈ [0, 138492]`, `movie_idx ∈ [0, 18344]` via sorted category codes,
   with mapping tables saved so predictions translate back to MovieLens ids.
6. **Feature engineering** — genre multi-hot columns, release year extracted from the title,
   timestamps converted, TMDB ids joined from `links.csv`.
7. **Train-only popularity** — rating counts and means computed from the training split only, so no
   test information leaks into the popularity baseline or the movie feature table.

### Audited changes from the notebook

| Change | Why |
|---|---|
| Parquet instead of CSV for the large splits | A 20M-row CSV is ~1.5 GB and slow to re-read |
| **Two** seen-indexes: train-only and full-history | Training negatives drawn against train-only history; evaluation negatives against the full history. The notebook used the full history for both, which leaks held-out items out of the training negatives |
| `eda_summary.json` emitted | So the dashboard renders measured values instead of hardcoded ones |
| `links.csv` joined | Exact TMDB ids, so artwork is never matched by fuzzy title |
| Vectorised negative sampling | The notebook's per-sample Python `while` loop does not scale to 25M samples per epoch |

## 9. Negative sampling methodology

MovieLens contains only observed interactions, so unobserved items must be sampled. **An unrated
movie is never treated as a confirmed dislike** — it is a sampled unobserved interaction.

- **Training**: 4 negatives per positive, **resampled every epoch**, drawn uniformly from movies the
  user did not interact with *in the training split*. Vectorised rejection sampling
  (`ml/training/data.py`).
- **Evaluation**: 99 negatives per user, drawn from movies the user never interacted with *anywhere*
  (train, validation or test) — the He et al. protocol. Built once into
  `artifacts/metrics/eval_candidates.npz` with seed 42, asserted to contain no observed item and no
  duplicate within a row, and **reused unchanged by all three models**.

## 10. Training procedure

| | Matrix Factorization | NeuMF | Rating predictor |
|---|---|---|---|
| Objective | BCEWithLogits | BCEWithLogits | MSE |
| Optimizer | Adam, lr 1e-3, wd 1e-6 | Adam, lr 1e-3, wd 1e-6 | Adam, lr 1e-3 |
| Batch size | 8192 | 8192 | 8192 |
| Training rows | 5,000,000 positives (×5 with negatives = 25M samples/epoch) | same | 8,000,000 ratings |
| Early stopping | val HR@10, patience 2 | val HR@10, patience 2 | val RMSE, patience 2 |
| Result | best epoch 6 of 8, 134 s | **best epoch 9 of 10, 242 s** | best epoch 3 of 5, 25 s |

**Training-set size is an explicit, recorded decision.** Preprocessing, EDA and evaluation use the
full 19,984,024 interactions; the implicit ranking models train on a seeded 5,000,000-positive
subsample (`MAX_POSITIVE_TRAIN_ROWS` in `ml/config.py`), which is stored in the checkpoint and shown
on the dashboard. Set it to `None` and re-run `scripts/train_all.sh` to train on all 9.99M positives.

Validation and test interactions are never used as training examples. Per-epoch monitoring scores
the **validation** leave-one-out interaction against its own fixed 10,000-user candidate cache;
the test candidates are touched only by the final evaluation.

## 11. Evaluation methodology

- **Protocol**: chronological leave-one-out. Each user's last interaction is the test item, the
  second-to-last is validation, everything earlier is training.
- **Relevance**: a held-out interaction counts as relevant only when its rating is ≥ 4.0. That
  leaves **80,331 eligible test users**, all of whom are evaluated (no sampling).
- **Candidates**: 1 held-out positive + 99 sampled unobserved movies = 100 per user, from one shared
  file, identical for every model.
- **Ties** are broken *pessimistically* for the positive item, so a constant scorer scores zero
  rather than being flattered by ordering accidents. This is asserted in `ml/tests/test_ml.py`.
- **Precision@10 / Recall@10 / F1@10** are reported because the PRD asks for them. With exactly one
  relevant item per user they are fixed functions of HR@10 — `Precision@10 = HR@10 / 10` and
  `Recall@10 = HR@10` — and are presented as such rather than as independent evidence.
- **RMSE** comes from a separate explicit-rating model (§13), never from a ranking score.

## 12. Results and baseline comparison

All figures below were produced by `ml/evaluation/evaluate_all.py` over **80,331 held-out users** on
identical candidate sets, and are reproduced verbatim in `artifacts/metrics/evaluation.json`.

| Model | HR@10 | NDCG@10 | MRR | ROC-AUC | Precision@10 | Recall@10 | F1@10 |
|---|---|---|---|---|---|---|---|
| Popularity (non-personalised) | 0.7916 | 0.5159 | 0.4415 | 0.9349 | 0.0792 | 0.7916 | 0.1439 |
| Matrix Factorization | 0.8651 | 0.5975 | 0.5207 | 0.9544 | 0.0865 | 0.8651 | 0.1573 |
| **NeuMF** | **0.9087** | **0.6596** | **0.5854** | **0.9682** | 0.0909 | 0.9087 | 0.1652 |

**NeuMF vs Matrix Factorization: +5.04% HR@10, +10.40% NDCG@10.**
**NeuMF vs Popularity: +14.79% HR@10, +27.86% NDCG@10.**

The popularity baseline scoring 0.79 is expected under this protocol, not a bug: negatives are drawn
uniformly from 18,345 movies, so they are mostly long-tail titles that a popular held-out movie
easily outranks. That is exactly why the baseline is reported — it is the bar NeuMF has to clear.

### Explicit rating prediction

| Predictor | RMSE | MAE |
|---|---|---|
| **Rating predictor** (NeuMF trunk + calibrated head) | **0.9064** | 0.6951 |
| Item-mean baseline | 0.9990 | 0.7800 |
| Global-mean baseline | 1.0825 | 0.8600 |

Evaluated on all 138,493 held-out ratings. Predictions span 0.549 – 4.971, inside the MovieLens
scale by construction.

### Recommendation analytics (2,000 sampled users, actual top-10 output)

| | NeuMF | Popularity |
|---|---|---|
| Catalog coverage | **3.52%** (646 distinct movies) | 0.71% (131 distinct movies) |
| Share from the most-rated 20% of the catalog | 99.94% | 100% |

NeuMF surfaces roughly **5× more of the catalog** than the popularity baseline, though both remain
strongly head-concentrated — an honest limitation, noted in §20.

### Hybrid re-ranking (stretch goal)

`hybrid = α·norm(NeuMF) + β·genre similarity + γ·norm(popularity)`, normalised within each candidate
list, genre profiles built from training positives only. Every blend in the grid was evaluated:

| α | β | γ | HR@10 | NDCG@10 |
|---|---|---|---|---|
| 1.0 | 0.0 | 0.0 | 0.90865 | 0.65964 | *(pure NeuMF, reference)* |
| **0.9** | **0.1** | **0.0** | **0.91089** | **0.66604** | *(best)* |
| 0.8 | 0.2 | 0.0 | 0.90382 | 0.65169 |
| 0.8 | 0.1 | 0.1 | 0.91001 | 0.66350 |
| 0.7 | 0.2 | 0.1 | 0.90469 | 0.65189 |
| 0.6 | 0.3 | 0.1 | 0.88701 | 0.62239 |

**Lift over pure NeuMF: +0.25% HR@10, +0.97% NDCG@10.** A real but small improvement. Pure NeuMF
remains a separate, selectable mode, and these results are stored in their own file
(`hybrid_evaluation.json`) so an experimental number is never mistaken for the headline result.

### Experiment comparison

| Experiment | Embedding | Negatives | Positives | HR@10 | NDCG@10 |
|---|---|---|---|---|---|
| MatrixFactorization | 32 | 4 | 5,000,000 | 0.86507 | 0.59748 |
| **NeuMF (production)** | 32 | 4 | 5,000,000 | **0.90865** | **0.65964** |
| NeuMF d16-neg2 (ablation) | 16 | 2 | 2,000,000 | 0.85053 | 0.57475 |

Add more with `scripts/run_experiment.py`; only executed runs are ever listed.

## 13. Rating prediction is a separate model — by design

A NeuMF ranking logit is unbounded and uncalibrated. Presenting it as a star rating would be
fabrication, so `ml/models/rating_predictor.py` is a **separate model** trained with MSE on the real
ratings, whose output is squashed:

```
predicted_rating = 0.5 + 4.5 · sigmoid(x)
```

Every prediction is therefore inside 0.5–5.0 structurally, not by clipping. `POST /predict` returns
the model name, the `rating_scale`, and the representation it used. A unit test drives the trunk to
extremes in both directions and asserts the bounds still hold.

## 14. Cold start: how a new account gets real personalisation

MovieLens user ids are anonymised **dataset** identifiers and are kept strictly separate from
application accounts. A newly registered account has no trained embedding, so:

1. **< 3 ratings** — the API serves the **popularity fallback** and says so explicitly in
   `fallback_reason`. Nothing pretends to be personalised.
2. **≥ 3 ratings** — the backend fits that one user's GMF and MLP vectors by gradient descent with
   **every item parameter frozen** (`fit_user_embedding`). Measured at ~540 ms for 6 ratings on CPU.
   From then on the account gets genuine NeuMF recommendations.
3. Re-fitting happens automatically whenever the user rates or un-rates a movie, and the
   recommendation cache for that user is invalidated.

A dataset profile can also be linked via `users.movielens_user_id` for demo purposes.

## 15. Technology stack

| Layer | Technology |
|---|---|
| ML | PyTorch 2.15, NumPy, pandas, pyarrow, scikit-learn |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Uvicorn, PyJWT, bcrypt, httpx |
| Database | PostgreSQL 17 |
| Frontend | React 19, Vite, Tailwind CSS v4, React Router, Axios, Recharts, Lucide, Framer Motion |
| Tests | pytest, Vitest, Testing Library |

Training uses GPU when available (CUDA or Apple MPS); **the inference backend runs on CPU** and
never imports a training entrypoint.

## 16. Folder structure

```
.
├── ml/                      # dataset → models → metrics (no web dependencies)
│   ├── config.py            # single source of truth for paths + hyperparameters
│   ├── preprocessing/run_preprocessing.py
│   ├── models/              # neumf.py · matrix_factorization.py · rating_predictor.py
│   ├── training/            # trainer.py · train_{mf,neumf,rating}.py · data.py
│   ├── evaluation/          # build_candidates · metrics · score · evaluate_all · evaluate_hybrid
│   ├── inference/recommender.py   # the only module the backend imports
│   └── tests/
├── backend/
│   ├── app/{api,core,db,models,schemas,services}/ · main.py
│   ├── alembic/             # migrations
│   └── tests/
├── frontend/src/{components,pages,layouts,hooks,services,context,charts}/
├── artifacts/{checkpoints,mappings,metrics,metadata}/
├── data/{raw,processed}/    # gitignored
├── notebooks/               # the original Colab export, preserved
├── scripts/                 # setup_db · train_all · run_experiment · benchmark_latency · …
└── README.md
```

`data/`, model checkpoints and `.env` are gitignored; no dataset, credential or large binary is
committed.

## 17. Measured performance

The PRD targets **< 200 ms** per single-user recommendation request. Measured by
`scripts/benchmark_latency.py` (200 requests per scenario, a different user each time so the
response cache cannot flatter the result), against the local API with a warm metadata cache:

| Scenario | p50 | p95 |
|---|---|---|
| **`GET /recommendations/{user_id}` (NeuMF, k=10)** | **2.73 ms** | **3.07 ms** |
| `GET /recommendations/{user_id}` (NeuMF, k=50) | 3.60 ms | 4.13 ms |
| `GET /recommendations/{user_id}` (hybrid, k=10) | 2.89 ms | 3.24 ms |
| `GET /recommendations/{user_id}` (popularity fallback) | 1.58 ms | 1.76 ms |
| `POST /predict` | 1.11 ms | 1.20 ms |
| `GET /movies` (title search) | 14.40 ms | 15.87 ms |
| `GET /metrics` | 0.51 ms | 0.72 ms |

Every row is an **uncached** request: the benchmark draws a different random user per run, so the
response cache never serves it. (A cache *hit* returns in ~0.01 ms, which is why the benchmark
deliberately avoids a fixed seed — replaying one user sequence would report cache-hit times as if
they were model latency.)

Scoring the **entire 18,345-movie catalog** for one user takes 0.88 ms (NeuMF) on CPU, so no
candidate pre-filtering is needed at this scale.

**Measured on an Apple M5 Pro development machine, not a production deployment.** One cold-path
caveat remains: a result containing movies with no cached TMDB metadata pays the external API
round-trip. Before the catalog head was prewarmed, an uncached k=50 list showed a p95 of ~280 ms;
after `python scripts/prewarm_tmdb.py 9000` it is 4.13 ms. Lookups are concurrent and capped at 24
per request, and the application is fully usable with no TMDB key at all.

Optimisations applied: weights loaded once at startup, batched tensor scoring, a TTL response cache
invalidated on rating changes, indexed Postgres queries, concurrent and budget-capped TMDB lookups.

## 18. Installation and setup

### Prerequisites
Python 3.12 (PyTorch does not yet support 3.14), Node 18+, PostgreSQL 16+ running locally.

### Step 1 — Python environment
```bash
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Step 2 — Environment configuration
```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET
```

| Variable | Meaning |
|---|---|
| `DATABASE_URL` / `TEST_DATABASE_URL` | PostgreSQL DSNs (`postgresql+psycopg://…`) |
| `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Auth |
| `TMDB_API_KEY` | **Optional.** Without it the app uses genre placeholder artwork and makes no external calls |
| `CORS_ORIGINS` | Comma-separated front-end origins |
| `RECOMMENDATION_CACHE_TTL` | Response cache TTL in seconds |

`.env` is gitignored — never commit a real key.

### Step 3 — Data, training and artifacts
```bash
./scripts/train_all.sh
```
Downloads MovieLens 20M (~190 MB), preprocesses, builds candidates, trains all three models and
evaluates. End-to-end runtime on an M5 Pro: **about 8 minutes**.

### Step 4 — Database
```bash
./scripts/setup_db.sh          # creates databases, runs migrations, seeds 27,278 movies
```

### Step 5 — Optional metadata prewarm
```bash
./venv/bin/python scripts/prewarm_tmdb.py 9000
```

## 19. Running the application

```bash
./scripts/run_backend.sh       # FastAPI  → http://127.0.0.1:8011  (docs at /docs)
./scripts/run_frontend.sh      # Vite     → http://localhost:5173
```

Ports are configurable with `PORT=…`. If a port is taken, Vite picks the next one — add that origin
to `CORS_ORIGINS` and set `VITE_API_URL` in `frontend/.env` to match the backend.

### API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | API, database, model-loading status and active model version |
| POST | `/auth/register` · `/auth/login` · `/auth/logout` | Account lifecycle (bcrypt + JWT) |
| GET | `/auth/me` | Current account |
| GET | `/recommendations/{user_id}` | Top-N for a **MovieLens dataset user**. `limit`, `model=neumf\|mf\|hybrid\|popularity`, `genre`, `min_year`, `max_year` |
| GET | `/recommendations/me` | Top-N for the signed-in **application account** |
| POST | `/predict` | Calibrated rating for `{user_id?, movie_id}` |
| GET | `/movies` | Search, genre/year filters, sorting, pagination |
| GET | `/movies/{movie_id}` | Detail + genre-similar titles + predicted rating |
| GET | `/movies/genres` | Genre vocabulary |
| GET/PUT | `/users/me/preferences` | Favourite genres, default model |
| POST/DELETE | `/users/me/ratings` | Submit / remove a rating (triggers re-fit) |
| GET | `/users/me/ratings` · `/history` · `/status` | Ratings, served recommendations, personalisation status |
| POST | `/users/me/onboarding` | Genres + initial ratings → fits the user embedding |
| GET | `/metrics` | Evaluation results (`"Not evaluated"` where a metric does not exist) |
| GET | `/metrics/eda` · `/training` · `/experiments` · `/latency` · `/app` | Dashboard data |
| GET | `/model/info` | Architecture, dims, training config, dataset version, evaluation |

Interactive OpenAPI docs at `/docs`.

## 20. Testing

```bash
./scripts/run_tests.sh
```

| Suite | Count | Covers |
|---|---|---|
| ML (`ml/tests`) | 19 | NDCG against a hand computation, pessimistic tie-breaking, Precision/Recall identity, seen-index membership, negatives never observed, candidate uniqueness, mapping round-trips, split disjointness and chronology, NeuMF shapes and branch independence, vector-path equivalence, rating calibration bounds, checkpoint load, fold-in, genre filtering |
| Backend (`backend/tests`) | 44 | Health/DB, registration, duplicate and weak-password rejection, login failure, token guards, logout revocation, all four models, unknown-user fallback, seen-item exclusion, fold-in personalisation, calibrated prediction, validation errors, search/filter/sort/pagination, preferences, rating upsert and delete, history, 401s |
| Frontend (`frontend`) | 22 | Card rendering, poster fallback, half-star control, recommendation rendering, model switching, fallback disclosure, search debounce, genre filter, empty states, API-error retry, dashboard tabs, "Not evaluated" labelling |

**Current status: 85 / 85 passing.** Backend tests run against a separate `movierec_test` database
and never touch development data; the suites make no network calls.

## 21. Deployment

> **Docker is not included in this repository.** It was dropped by an explicit project decision, so
> the "runs via Docker Compose" acceptance item from the original brief is **not met**. Everything
> below is written guidance, not a verified deployment — the application has been run and tested
> locally only.

**Backend** (Render / Railway / Hugging Face Spaces): Python 3.12, `pip install -r requirements.txt`,
start `uvicorn app.main:app --host 0.0.0.0 --port $PORT` with `PYTHONPATH=<repo>:<repo>/backend`.
Set `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, optionally `TMDB_API_KEY`. Run
`alembic upgrade head` and `scripts/seed_movies.py` on first deploy. CPU-only is sufficient.

**Model artifacts** (~75 MB) are gitignored. Either attach a persistent volume and upload
`artifacts/`, or fetch it from object storage at container start. The API starts without them and
reports `degraded` health while serving popularity fallbacks.

**Frontend** (Vercel / Netlify): `npm ci && npm run build`, publish `dist/`, set `VITE_API_URL` to
the deployed backend and add that origin to the backend's `CORS_ORIGINS`.

**Database**: any managed PostgreSQL 16+. The schema is small; the seeded catalog is 27,278 rows.

## 22. Known limitations and future work

1. **Dataset version** — MovieLens 20M throughout, not the 25M named in the PRD (§5).
2. **Training subsample** — 5M of 9.99M positives, a recorded decision; set
   `MAX_POSITIVE_TRAIN_ROWS = None` to use all of them.
3. **Sampled-negative evaluation** — the standard He et al. protocol, but 99 uniformly sampled
   negatives make the task easier than full-catalog ranking, which is why the popularity baseline
   already reaches 0.79. Full-catalog evaluation would be a stronger, more expensive test.
4. **Popularity bias** — NeuMF covers 5× more of the catalog than popularity, but 99.9% of its
   recommendations still come from the most-rated 20%. Long-tail exposure is unsolved here.
5. **No pretraining** — He et al. initialise NeuMF from separately trained GMF and MLP models;
   this implementation trains from scratch, which likely leaves some headroom.
6. **Fold-in is not retraining** — a new account's item embeddings stay frozen. Periodic full
   retraining would be needed in production.
7. **Fold-in rating predictions saturate on uniform input** — an account whose onboarding ratings
   are all 4.5–5.0 gives the regression head no spread to fit, so it predicts at or near 5.0 for
   most titles. The value stays inside the rating scale and the ranking path is unaffected, but
   the predicted rating only becomes informative once the account has rated across the range. The
   RMSE in §12 is measured on dataset users with full histories, not on fold-in accounts.
8. **Docker omitted** (§21).
9. **Latency measured locally**, single process, warm metadata cache (§17).
10. **No Precision/Recall beyond k=10** and no diversity-aware objective.
11. **TMDB coverage** — 27,026 of 27,278 movies carry a TMDB id; the rest always use placeholders.

## 23. Reproducing everything from scratch

```bash
python3.12 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env            # set JWT_SECRET (and TMDB_API_KEY if you have one)
./scripts/train_all.sh          # data → preprocessing → training → evaluation  (~8 min)
./scripts/setup_db.sh           # databases, migrations, catalog seed
./scripts/run_backend.sh &      # http://127.0.0.1:8011
./scripts/run_frontend.sh       # http://localhost:5173
./scripts/run_tests.sh          # 85 tests
./venv/bin/python scripts/benchmark_latency.py    # writes artifacts/metrics/latency.json
```

Seeds are fixed (`SEED = 42`) across preprocessing, splitting, negative sampling, candidate
construction and training.

---

*MovieLens data is used under the GroupLens research licence. Movie metadata and artwork, when a
TMDB key is configured, come from The Movie Database; this product uses the TMDB API but is not
endorsed or certified by TMDB.*
