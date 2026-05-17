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
    model_config = ConfigDict(frozen=False)  # allow mutation for key rotation state

    groq_api_keys: list[SecretStr]
    google_api_keys: list[SecretStr]
    supabase_service_role_key: SecretStr
    supabase_url: str
    model_name: str
    temperature: float
    embedding_model_name: str
    gemini_model_name: str = "gemini-2.5-flash"
    chat_host: str = "127.0.0.1"
    chat_port: int = 8000
    rag_top_k: int = 5
    rag_min_context_similarity: float = 0.45

    # Rotation state
    _groq_index: int = 0
    _google_index: int = 0
    _groq_exhausted: bool = False  # True = semua Groq key limit, switch ke Gemini

    def get_groq_key(self) -> str:
        if not self.groq_api_keys:
            raise ValueError("Tidak ada Groq API key yang tersedia.")
        return self.groq_api_keys[self._groq_index].get_secret_value()

    def rotate_groq_key(self) -> str:
        if len(self.groq_api_keys) > 1:
            self._groq_index = (self._groq_index + 1) % len(self.groq_api_keys)
        return self.get_groq_key()

    def get_google_key(self) -> str:
        if not self.google_api_keys:
            raise ValueError("Tidak ada Google API key yang tersedia.")
        return self.google_api_keys[self._google_index].get_secret_value()

    def rotate_google_key(self) -> str:
        if len(self.google_api_keys) > 1:
            self._google_index = (self._google_index + 1) % len(self.google_api_keys)
        return self.get_google_key()

    def get_llm_api_key(self) -> tuple[str, str]:
        """
        Return (api_key, model_name) untuk LLM chat calls.
        Strategy: Groq dulu, Gemini Flash 2.5 fallback.
        Jika semua Groq key limit/error → switch ke Gemini.
        """
        # Phase 1: Coba Groq
        if not self._groq_exhausted:
            for _ in range(len(self.groq_api_keys)):
                try:
                    key = self.get_groq_key()
                    return key, self.model_name
                except Exception:
                    if len(self.groq_api_keys) > 1:
                        self.rotate_groq_key()
            # Semua Groq gagal
            self._groq_exhausted = True

        # Phase 2: Gemini fallback
        for _ in range(len(self.google_api_keys)):
            try:
                key = self.get_google_key()
                return key, self.gemini_model_name
            except Exception:
                if len(self.google_api_keys) > 1:
                    self.rotate_google_key()

        raise ValueError("Semua API key (Groq + Gemini) tidak tersedia.")

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
# Digunakan oleh: model_ai/extractor/doc_extractor.py; model_ai/extractor/schema_differ.py; model_ai/loader/supabase_ingest.py; model_ai/docx/style_mapping_pipeline.py; dst.
# Menjalankan fungsi `get_config` sebagai bagian alur `config`.
# ---------------------------------------------------------------------------
def _load_api_key_list(prefix: str, suffix_max: int = 5) -> list[SecretStr]:
    """Load all numbered API keys (GROQ_API_KEY, GROQ_API_KEY_2, ..., GOOGLE_API_KEY_5)."""
    keys: list[SecretStr] = []
    for i in range(1, suffix_max + 1):
        env_name = f"{prefix}_{i}" if i > 1 else prefix
        value = os.getenv(env_name, "").strip()
        if value:
            keys.append(SecretStr(value))
    return keys


def get_config() -> AppConfig:
    return AppConfig(
        groq_api_keys=_load_api_key_list("GROQ_API_KEY"),
        google_api_keys=_load_api_key_list("GOOGLE_API_KEY"),
        supabase_service_role_key=SecretStr(
            _get_required_env("SUPABASE_SERVICE_ROLE_KEY")
        ),
        supabase_url=_get_required_env("SUPABASE_URL"),
        model_name=_get_required_env("MODEL_NAME"),
        temperature=float(_get_required_env("TEMPERATURE")),
        embedding_model_name=_get_required_env("EMBEDDING_MODEL_NAME"),
        gemini_model_name=os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
        chat_host=os.getenv("CHAT_HOST", "127.0.0.1").strip() or "127.0.0.1",
        chat_port=int(os.getenv("CHAT_PORT", "8000")),
        rag_top_k=int(os.getenv("RAG_TOP_K", "5")),
        rag_min_context_similarity=float(
            os.getenv("RAG_MIN_CONTEXT_SIMILARITY", "0.45")
        ),
    )
