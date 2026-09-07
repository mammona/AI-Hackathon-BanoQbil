from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Fasal Shield Backend"
    app_env: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./fasal_guard.db"
    data_dir: Path = Path("data/reports")
    auto_seed_demo_devices: bool = True
    demo_devices_file: Path = Path("data/demo_devices.json")

    max_image_mb: int = 15
    min_image_width: int = 128
    min_image_height: int = 128
    min_brightness: float = 16.0
    max_brightness: float = 246.0
    min_contrast_std: float = 6.0

    # Trained disease models supplied by the project. Keep the .pt files and
    # class_mappings.json together under models/disease/.
    cotton_model_path: Path = Path("models/disease/cotton_disease_classifier.pt")
    rice_model_path: Path = Path("models/disease/rice_disease_classifier.pt")
    disease_class_mappings_path: Path = Path("models/disease/class_mappings.json")
    disease_threshold: float = 0.70
    disease_min_margin: float = 0.10
    allow_missing_disease_model: bool = True

    # Deterministic outbreak engine settings for the prototype.
    outbreak_radius_km: float = 5.0
    # Farmer notification delivery radius is intentionally separate from the
    # outbreak-linking radius. The demo alerts nearby same-crop devices within
    # 2 km of the calculated alert center.
    notification_radius_km: float = 2.0
    outbreak_time_window_days: int = 7
    outbreak_monitoring_min_reports: int = 2
    outbreak_amber_min_reports_with_image: int = 3
    outbreak_amber_min_symptom_only_reports: int = 4

    # Local generative Qwen for Q1 span separation and Q2-Q4 normalization.
    qwen_base_url: str = "http://localhost:11434"
    qwen_model: str = "qwen3:1.7b"
    qwen_timeout_seconds: float = 120.0
    qwen_allow_fallback: bool = True

    # Multilingual symptom semantic retrieval / RAG.
    # Default: local Qwen3-Embedding via the same Ollama server.
    symptom_embedding_backend: str = "ollama"  # ollama | hf_e5
    symptom_embedding_model: str = "qwen3-embedding:0.6b"
    symptom_embedding_device: str = "cpu"  # only used by hf_e5 backend
    symptom_embedding_timeout_seconds: float = 120.0
    symptom_rag_top_k: int = 5
    # Deprecated in V10 and ignored. Kept only so older .env files remain valid.
    # V10 uses one meaning-only embedding per concept.
    symptom_rag_identity_weight: float = 0.60

    # Starter values only. Tune with scripts/evaluate_multilingual_retrieval.py.
    # Precision is intentionally favored: uncertain symptoms become OTHERS_MAP.
    # V13 retrieve -> rerank gates. Embeddings retrieve candidates; they are
    # no longer treated as the final classifier when the result is ambiguous.
    symptom_match_threshold: float = 0.55
    symptom_min_margin: float = 0.05
    symptom_retrieval_floor: float = 0.45
    symptom_direct_accept_threshold: float = 0.65
    symptom_direct_accept_margin: float = 0.08
    symptom_rerank_enabled: bool = True
    # V17: dedicated cross-encoder reranker. The generative qwen3:1.7b model is
    # no longer used for symptom ranking.
    symptom_rerank_top_k: int = 3
    symptom_reranker_model: str = "Qwen/Qwen3-Reranker-0.6B"
    symptom_reranker_device: str = "auto"  # auto | cpu | cuda
    symptom_reranker_max_length: int = 512
    symptom_reranker_min_score: float = 0.50
    symptom_reranker_min_margin: float = 0.00
    symptom_reranker_local_files_only: bool = False
    # Kept for backward-compatible .env files; unused by the dedicated reranker.
    symptom_rerank_timeout_seconds: float = 60.0

    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
