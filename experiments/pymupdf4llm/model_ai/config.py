import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, SecretStr

APP_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = APP_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)


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
                "GOOGLE_API_KEY wajib di-set di file .env untuk proses embedding."
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


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} belum di-set di file .env.")
    return value


def _get_optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


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
