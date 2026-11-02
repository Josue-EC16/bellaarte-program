from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "development"
    frontend_url: str = "http://localhost:5173"

    database_url: str | None = None
    db_host: str | None = None
    db_name: str | None = None
    db_user: str | None = None
    db_pass: str | None = None
    db_port: int | None = None

    jwt_secret_key: str = "bellaarte-dev-access-secret"
    jwt_refresh_secret_key: str = "bellaarte-dev-refresh-secret"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    jwt_algorithm: str = "HS256"

    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "Admin12345!"
    bootstrap_admin_email: str = "admin@bellaarte.local"
    bootstrap_admin_names: str = "ADMIN"
    bootstrap_admin_last_name: str = "BELLAARTE"
    bootstrap_admin_mother_last_name: str = "SISTEMA"
    bootstrap_admin_ci: str = "1000000"
    bootstrap_admin_cellphone: str = "70000000"
    bootstrap_admin_zone: str = "CENTRAL"
    bootstrap_admin_address: str = "OFICINA PRINCIPAL"
    bootstrap_admin2_username: str = "admin2"
    bootstrap_admin2_password: str = "Admin22345!"
    bootstrap_admin2_email: str = "admin2@bellaarte.local"
    bootstrap_admin2_names: str = "ADMIN DOS"
    bootstrap_admin2_last_name: str = "BELLAARTE"
    bootstrap_admin2_mother_last_name: str = "SISTEMA"
    bootstrap_admin2_ci: str = "1000001"
    bootstrap_admin2_cellphone: str = "70000001"
    bootstrap_admin2_zone: str = "CENTRAL"
    bootstrap_admin2_address: str = "OFICINA PRINCIPAL"

    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_username: str | None = None
    smtp_password: str | None = None

    backup_dir: str = "./storage/backups"
    pg_dump_path: str | None = None
    backup_timezone: str = "America/La_Paz"
    backup_filename_prefix: str = "bellaarte_backup"

    leny_enabled: bool = True
    # FastAPI owns only children it starts; existing Ollama/manual workers are borrowed.
    leny_runtime_autostart: bool = True
    leny_ollama_executable: str | None = None
    leny_runtime_startup_seconds: float = Field(default=20, ge=1, le=120)
    leny_runtime_shutdown_seconds: float = Field(default=240, ge=5, le=360)
    leny_ollama_url: str = "http://127.0.0.1:11434"
    leny_model: str = "qwen3.5:4b-q4_K_M"
    leny_num_ctx: int = Field(default=4096, ge=2048, le=32768)
    leny_num_predict: int = Field(default=768, ge=32, le=4096)
    leny_temperature: float = Field(default=0.3, ge=0, le=2)
    leny_keep_alive: str = "5m"
    leny_connect_timeout: float = Field(default=5, gt=0, le=60)
    leny_first_token_timeout: float = Field(default=90, gt=0, le=600)
    leny_idle_timeout: float = Field(default=30, gt=0, le=300)
    leny_total_timeout: float = Field(default=120, gt=0, le=900)
    leny_max_message_chars: int = Field(default=2000, ge=1, le=10000)
    leny_max_body_bytes: int = Field(default=16384, ge=1024, le=65536)
    leny_max_response_bytes: int = Field(default=32768, ge=1024, le=262144)
    leny_retention_days: int = Field(default=0, ge=0, le=36500)
    leny_rate_limit: int = Field(default=5, ge=1, le=100)
    leny_rate_window_seconds: int = Field(default=60, ge=1, le=3600)
    leny_output_holdback_chars: int = Field(default=256, ge=256, le=2048)
    leny_classifier_timeout: float = Field(default=20, gt=0, le=60)

    # Optional library: activation requires its additive migration and parsers.
    leny_documents_enabled: bool = False
    leny_documents_root: str | None = None
    leny_documents_max_body_bytes: int = Field(default=12 * 1024 * 1024, ge=1024, le=12 * 1024 * 1024)
    leny_documents_max_file_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=10 * 1024 * 1024)
    leny_documents_image_bytes: int = Field(default=5 * 1024 * 1024, ge=1024, le=5 * 1024 * 1024)
    leny_documents_max_pixels: int = Field(default=12_000_000, ge=1)
    leny_documents_pdf_pages: int = Field(default=50, ge=1)
    leny_documents_zip_entries: int = Field(default=1000, ge=1)
    leny_documents_zip_bytes: int = Field(default=32 * 1024 * 1024, ge=1024)
    leny_documents_zip_entry_bytes: int = Field(default=8 * 1024 * 1024, ge=1024)
    leny_documents_zip_ratio: int = Field(default=100, ge=1)
    leny_documents_validation_seconds: int = Field(default=30, ge=1, le=120)
    leny_documents_validation_memory_mb: int = Field(default=768, ge=128, le=2048)
    leny_documents_upload_seconds: int = Field(default=180, ge=1, le=600)
    leny_documents_idle_seconds: int = Field(default=30, ge=1, le=120)
    leny_documents_capacity_bytes: int = Field(default=5 * 1024**3, ge=1024)
    leny_documents_min_free_bytes: int = Field(default=1024**3, ge=0)
    leny_documents_max_folders: int = Field(default=1000, ge=1)
    leny_documents_max_depth: int = Field(default=8, ge=1, le=32)
    leny_documents_batch_size: int = Field(default=5, ge=1, le=5)
    leny_documents_max_documents: int = Field(default=10000, ge=1)
    leny_documents_max_versions: int = Field(default=100, ge=1)
    leny_documents_max_total_versions: int = Field(default=100000, ge=1, le=100000)
    leny_documents_rate_limit: int = Field(default=5, ge=1, le=100)
    leny_documents_rate_window_seconds: int = Field(default=60, ge=1, le=3600)
    leny_documents_retention_days: int = Field(default=10, ge=10, le=365)
    leny_documents_maintenance_seconds: int = Field(default=900, ge=30)

    # SPEC-02 is opt-in only after native tools, vector extension and migration.
    leny_rag_enabled: bool = False
    leny_rag_chat_enabled: bool = False
    leny_rag_top_k: int = Field(default=5, ge=1, le=5)
    leny_rag_candidates: int = Field(default=20, ge=5, le=20)
    # Candidate is opt-in until the isolated and real-document acceptance gates pass.
    leny_rag_profile: Literal['legacy', 'rag4_v1'] = 'legacy'
    leny_rag_evidence_mode: Literal['fixed', 'adaptive'] = 'fixed'
    leny_rag_adaptive_token_probe: bool = False
    leny_rag_ranking: Literal['semantic', 'hybrid'] = 'semantic'
    leny_rag_neighbor_chunks: bool = False
    leny_rag_max_context_bytes: int = Field(default=2048, ge=256, le=2560)
    leny_rag_query_max_bytes: int = Field(default=1536, ge=128, le=1536)
    leny_rag_search_timeout_seconds: float = Field(default=2, gt=0, le=5)
    leny_rag_query_embed_timeout_seconds: float = Field(default=20, gt=0, le=30)
    leny_rag_allow_source_download: bool = True
    leny_rag_model: str = 'qwen3-embedding:0.6b'
    leny_rag_model_digest: str = 'ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d'
    leny_rag_dimension: int = Field(default=1024, ge=1024, le=1024)
    leny_rag_tesseract_path: str | None = None
    leny_rag_tessdata_path: str | None = None
    leny_rag_cpu_threads: int = Field(default=4, ge=1, le=4)
    leny_rag_batch_size: int = Field(default=2, ge=1, le=4)
    leny_rag_num_ctx: int = Field(default=4096, ge=2048, le=4096)
    leny_rag_connect_seconds: float = Field(default=5, gt=0, le=30)
    leny_rag_read_seconds: float = Field(default=120, gt=0, le=180)
    leny_rag_batch_seconds: float = Field(default=150, gt=0, le=180)
    leny_rag_job_seconds: int = Field(default=1800, ge=60, le=1800)
    leny_rag_max_attempts: int = Field(default=3, ge=1, le=3)
    leny_rag_heartbeat_seconds: int = Field(default=5, ge=1, le=10)
    leny_rag_lease_seconds: int = Field(default=60, ge=30, le=120)
    leny_rag_poll_seconds: float = Field(default=2, ge=1, le=30)
    leny_rag_rate_limit: int = Field(default=5, ge=1, le=20)
    leny_rag_queue_limit: int = Field(default=100, ge=1, le=100)
    leny_rag_max_text_bytes: int = Field(default=1024**2, ge=1024, le=1024**2)
    leny_rag_max_chunks: int = Field(default=1000, ge=1, le=1000)
    leny_rag_max_total_chunks: int = Field(default=100000, ge=1, le=100000)
    leny_rag_capacity_bytes: int = Field(default=2 * 1024**3, ge=1024**2, le=2 * 1024**3)
    leny_rag_chunk_target: int = Field(default=1600, ge=100, le=1600)
    leny_rag_chunk_chars: int = Field(default=2000, ge=200, le=2000)
    leny_rag_chunk_bytes: int = Field(default=3072, ge=1024, le=3072)
    leny_rag_overlap_chars: int = Field(default=240, ge=0, le=240)
    leny_rag_ocr_pages: int = Field(default=20, ge=1, le=20)
    leny_rag_ocr_dpi: int = Field(default=200, ge=100, le=200)
    leny_rag_render_pixels: int = Field(default=12000000, ge=1000000, le=12000000)
    leny_rag_ocr_seconds: int = Field(default=30, ge=1, le=30)
    leny_rag_parser_memory_mb: int = Field(default=1536, ge=256, le=1536)
    leny_rag_temp_bytes: int = Field(default=256 * 1024**2, ge=1024**2, le=256 * 1024**2)
    leny_rag_min_free_bytes: int = Field(default=2 * 1024**3, ge=0)
    leny_rag_min_ram_bytes: int = Field(default=2 * 1024**3, ge=0)
    leny_rag_min_resident_ram_bytes: int = Field(default=1024**3, ge=0)
    leny_rag_staging_retention_days: int = Field(default=7, ge=1, le=30)

    @field_validator('leny_rag_model')
    @classmethod
    def validate_embedding_model(cls, value: str) -> str:
        if value != 'qwen3-embedding:0.6b':
            raise ValueError('SPEC-02 requiere qwen3-embedding:0.6b sin sustitución automática.')
        return value

    @field_validator('leny_rag_model_digest')
    @classmethod
    def validate_embedding_digest(cls, value: str) -> str:
        import re
        if not re.fullmatch(r'[0-9a-f]{64}', value):
            raise ValueError('El manifest de embeddings requiere un SHA-256 válido.')
        return value

    @field_validator("leny_ollama_url")
    @classmethod
    def validate_leny_url(cls, value: str) -> str:
        from urllib.parse import urlsplit
        parsed = urlsplit(value)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise ValueError("LENY requiere una URL HTTP de Ollama en loopback, sin credenciales ni rutas.")
        return value.rstrip("/")

    @field_validator("leny_model")
    @classmethod
    def validate_leny_model(cls, value: str) -> str:
        if not value.strip() or "cloud" in value.lower() or len(value) > 120:
            raise ValueError("LENY requiere un modelo instalado localmente.")
        return value.strip()

    @computed_field
    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        required = [self.db_user, self.db_pass, self.db_host, self.db_port, self.db_name]
        if not all(required):
            raise ValueError(
                "DATABASE_URL o las variables DB_HOST, DB_NAME, DB_USER, DB_PASS y DB_PORT son obligatorias."
            )

        return (
            f"postgresql://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
