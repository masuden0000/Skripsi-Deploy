"""
Fungsi: Memuat konfigurasi environment (ai/.env) dan konstanta global untuk layanan AI/pipeline.

Digunakan oleh: model_ai/extractor/doc_extractor.py; model_ai/extractor/schema_differ.py; model_ai/loader/supabase_ingest.py; model_ai/docx/style_mapping_pipeline.py

Tujuan: Memusatkan konfigurasi supaya modul lain tidak hardcode nilai environment.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, SecretStr

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `APP_DIR` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parents[1]
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `ENV_FILE` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
ENV_FILE = APP_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Mendefinisikan class `AppConfig` untuk kebutuhan modul `config`.
# ---------------------------------------------------------------------------
class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    groq_api_key: SecretStr
    google_api_key: SecretStr | None = None
    supabase_service_role_key: SecretStr
    supabase_url: str
    model_name: str
    temperature: float
    embedding_model_name: str
    chat_host: str = "127.0.0.1"
    chat_port: int = 8000
    rag_top_k: int = 5
    rag_min_context_similarity: float = 0.45

    def require_google_api_key(self) -> str:
        if self.google_api_key is None:
            raise ValueError(
                "GOOGLE_API_KEY wajib di-set di file ai/.env untuk proses embedding."
            )
        return self.google_api_key.get_secret_value()

    def disable_blackhole_proxies(self) -> None:
        proxy_keys = [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ]
        blackhole_proxy_targets = {"http://127.0.0.1:9", "https://127.0.0.1:9"}

        for key in proxy_keys:
            value = os.getenv(key, "").strip().lower()
            # Sebagian environment menyetel localhost:9 sebagai proxy "buang trafik".
            if value in blackhole_proxy_targets:
                os.environ.pop(key, None)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_get_required_env` sebagai bagian alur `config`.
# ---------------------------------------------------------------------------
def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} belum di-set di file ai/.env.")
    return value


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_get_optional_env` sebagai bagian alur `config`.
# ---------------------------------------------------------------------------
def _get_optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py; model_ai/extractor/schema_differ.py; model_ai/loader/supabase_ingest.py; model_ai/docx/style_mapping_pipeline.py; dst.
# Menjalankan fungsi `get_config` sebagai bagian alur `config`.
# ---------------------------------------------------------------------------
def get_config() -> AppConfig:
    google_api_key = _get_optional_env("GOOGLE_API_KEY")
    return AppConfig(
        groq_api_key=SecretStr(_get_required_env("GROQ_API_KEY")),
        google_api_key=SecretStr(google_api_key) if google_api_key else None,
        supabase_service_role_key=SecretStr(
            _get_required_env("SUPABASE_SERVICE_ROLE_KEY")
        ),
        supabase_url=_get_required_env("SUPABASE_URL"),
        model_name=_get_required_env("MODEL_NAME"),
        temperature=float(_get_required_env("TEMPERATURE")),
        embedding_model_name=_get_required_env("EMBEDDING_MODEL_NAME"),
        chat_host=os.getenv("CHAT_HOST", "127.0.0.1").strip() or "127.0.0.1",
        chat_port=int(os.getenv("CHAT_PORT", "8000")),
        rag_top_k=int(os.getenv("RAG_TOP_K", "5")),
        rag_min_context_similarity=float(
            os.getenv("RAG_MIN_CONTEXT_SIMILARITY", "0.45")
        ),
    )
