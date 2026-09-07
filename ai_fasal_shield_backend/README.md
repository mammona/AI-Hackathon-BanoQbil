# AI Fasal Shield Backend

**AI-powered crop disease detection and outbreak alert system for Pakistani farmers.**

AI Fasal Shield processes multilingual farmer reports (English, Urdu, Punjabi/Shahmukhi) through an AI pipeline that combines image-based disease classification, semantic symptom retrieval (RAG), and deterministic outbreak detection — all running locally with **zero paid API costs**.

---

## Key Features

| Feature | Description |
|---|---|
| **Multilingual Symptom RAG** | Farmers report symptoms in Urdu, Punjabi, or English — no translation needed. Local Qwen3 embeddings retrieve canonical symptom matches. |
| **Image Disease Classification** | Cotton and rice crop images are classified using trained EfficientNet models for disease detection. |
| **Deterministic Outbreak Engine** | Geo-temporal clustering (5 km / 7 days) automatically detects outbreak patterns from multiple farmer reports. |
| **Expert Review Dashboard** | Admin interface for reviewing reports, confirming amber alerts to red, and managing outbreak responses. |
| **Farmer Notifications** | Punjabi (Shahmukhi) push notifications sent to nearby registered devices when alerts are confirmed. |
| **Dedicated Reranker** | Qwen3-Reranker-0.6B cross-encoder ensures accurate symptom-to-canonical mapping. |
| **Docker-Ready** | One-command startup with Docker Compose. No manual Python/setup required. |

---

## Tech Stack

- **API:** FastAPI 0.116.1 + Uvicorn
- **Database:** SQLAlchemy 2.0 + SQLite (zero-config) or PostgreSQL (optional)
- **ML/Image:** PyTorch, torchvision, timm, Pillow
- **LLM/NLP:** Transformers, HuggingFace Hub, httpx (Ollama API)
- **Local AI Models:**
  - `qwen3:1.7b` — farmer answer extraction (Q1–Q4)
  - `qwen3-embedding:0.6b` — multilingual symptom embeddings
  - `Qwen/Qwen3-Reranker-0.6B` — symptom candidate reranking
- **Validation:** Pydantic v2, pydantic-settings
- **Testing:** pytest

---

## Quick Start with Docker (Recommended)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Ollama](https://ollama.com/) running on your host machine with required models:

```bash
ollama pull qwen3:1.7b
ollama pull qwen3-embedding:0.6b
```

### Run

```bash
# Clone the repository
git clone https://github.com/mammona/AI-Hackathon-BanoQabil.git
cd AI-Hackathon-BanoQbil/ai_fasal_shield_backend

# Build and start the container
docker compose up --build

# The API is ready when you see:
# INFO: Uvicorn running on http://0.0.0.0:8000
```

### Access

| URL | Description |
|---|---|
| http://localhost:8000/docs | **Swagger API Documentation** — test all endpoints interactively |
| http://localhost:8000/admin | **Admin/Expert Dashboard** — review reports and manage alerts |
| http://localhost:8000/health | Health check endpoint |

### Stop

```bash
docker compose down        # Stop container
docker compose down -v     # Stop and delete data volumes (fresh start)
```

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11
- [Ollama](https://ollama.com/) running with models pulled

### Setup & Run

```powershell
# Windows — one-click setup
SETUP_BACKEND.bat
START_BACKEND.bat

# Or manually:
python -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Prepare the Reranker (First Time Only)

```powershell
python -m scripts.prepare_qwen_reranker
```

---

## API Endpoints

### Reports

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/reports/process` | Submit a farmer report (image + Q1–Q4 answers) |
| `GET` | `/api/v1/reports` | List all reports |
| `POST` | `/api/v1/reports/{id}/review` | Expert review (VALID / INVALID / FOLLOW_UP) |

### Alerts & Outbreaks

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/alerts` | List active outbreak alerts |
| `POST` | `/api/v1/alerts/{id}/confirm` | Expert confirms AMBER → RED alert |

### Devices & Notifications

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/devices/register` | Register a farmer device |
| `GET` | `/api/v1/devices/{id}/notifications` | Get device notifications |

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/dashboard/summary` | Dashboard statistics |
| `GET` | `/admin` | Admin HTML dashboard |

---

## Report Processing Pipeline

```
Farmer Report (image + Q1–Q4 in Urdu/Punjabi/English)
   │
   ├─ Image submitted?
   │   ├─ YES → Validate image → Classify disease (cotton/rice model)
   │   └─ NO  → Skip image analysis
   │
   ├─ Qwen3 1.7B extracts:
   │   ├─ Q1: Symptom spans + affected plant part
   │   ├─ Q2: Problem duration
   │   ├─ Q3: Affected area extent
   │   └─ Q4: Spread status
   │
   ├─ Symptom RAG Pipeline:
   │   ├─ qwen3-embedding:0.6b encodes symptoms
   │   ├─ Top-5 cosine similarity retrieval
   │   └─ Qwen3-Reranker-0.6B scores candidates
   │
   ├─ Evidence Assessment:
   │   ├─ MULTIMODAL (image + symptoms)
   │   ├─ IMAGE_ONLY
   │   ├─ SYMPTOM_ONLY
   │   └─ CONTEXT_ONLY
   │
   ├─ Disease-Symptom Consistency Check
   │
   ├─ Save Report → SQLite
   │
   └─ Outbreak Engine (5 km / 7 days):
       ├─ NO_ALERT → MONITORING → AMBER → RED
       └─ Farmer notifications in Punjabi
```

---

## Project Structure

```
ai_fasal_shield_backend/
├── app/
│   ├── api/                  # FastAPI route handlers
│   │   ├── admin_dashboard.py    # Admin dashboard + expert review
│   │   ├── alerts.py             # Alert & outbreak endpoints
│   │   ├── devices.py            # Device registration
│   │   ├── rag_debug.py          # RAG testing endpoints
│   │   └── reports.py            # Report submission & listing
│   ├── constants/            # Symptom dictionary, plant parts
│   ├── models/               # SQLAlchemy models + Pydantic schemas
│   ├── repositories/         # Database access layer
│   ├── services/             # Core business logic
│   │   ├── disease_model_service.py      # Image classification
│   │   ├── symptom_rag_service.py        # Multilingual RAG pipeline
│   │   ├── qwen_report_service.py        # Qwen Q1-Q4 extraction
│   │   ├── outbreak_service.py           # Geo-temporal clustering
│   │   ├── notification_service.py       # Farmer notifications
│   │   └── disease_symptom_consistency.py # Cross-validation
│   ├── static/               # Admin dashboard HTML
│   ├── config.py             # Pydantic settings
│   ├── database.py           # SQLAlchemy engine setup
│   └── main.py               # FastAPI application entry
├── data/                     # Demo device/report fixtures
├── models/disease/           # Trained cotton/rice classifiers
├── scripts/                  # Evaluation & seed scripts
├── tests/                    # Pytest test suite
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # One-command container startup
├── .env.docker               # Docker environment config
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## Environment Configuration

Key settings (via `.env` or `.env.docker`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./fasal_guard.db` | Database connection |
| `QWEN_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `QWEN_MODEL` | `qwen3:1.7b` | Farmer extraction model |
| `SYMPTOM_EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | Embedding model |
| `SYMPTOM_RERANKER_MODEL` | `Qwen/Qwen3-Reranker-0.6B` | Reranker model |
| `OUTBREAK_RADIUS_KM` | `5.0` | Outbreak clustering radius |
| `NOTIFICATION_RADIUS_KM` | `2.0` | Farmer notification radius |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

---

## Testing

```powershell
# Run full test suite
python -m pytest -q

# Run specific test categories
python -m pytest tests/test_symptom_rag.py tests/test_outbreak_engine.py
python -m pytest tests/test_notification_flow.py tests/test_disease_symptom_consistency.py

# Run evaluation benchmarks
python scripts/evaluate_multilingual_pipeline.py --case 1
python scripts/evaluate_punjabi_rag_reports.py
```

---

## Demo

1. Start the backend: `docker compose up --build`
2. Open http://localhost:8000/docs
3. Submit a report via `POST /api/v1/reports/process`:
   - Select crop: `cotton` or `rice`
   - Select language: `urdu`, `punjabi`, or `english`
   - Enter Q1 (symptoms): e.g., `پتے پیلے ہو رہے ہیں اور مڑ رہے ہیں` (Punjabi: leaves yellowing and curling)
   - Optionally upload a crop image
   - Provide GPS coordinates for outbreak clustering
4. View results at http://localhost:8000/admin

---

## License

This project was developed for the AI Hackathon Bano Qabil competition.
