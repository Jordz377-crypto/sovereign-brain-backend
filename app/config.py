from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    app_name: str = "AI Automation Systems (PTY) LTD — Sovereign Brain"
    app_version: str = "1.0.0"
    debug: bool = False

    aigos_internal_secret: str = ""
    groq_api_key: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    evolution_api_token: str = ""
    n8n_webhook_url: str = ""
    n8n_handoff_webhook_url: str = ""
    redis_url: str = "redis://localhost:6379"

    cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:3000,"
        "https://*.lovable.app"
    )

    za_founder_1_name: str = "Jordan"
    za_founder_1_phone: str = "+27704592553"
    za_founder_2_name: str = "Jevon"
    za_founder_2_phone: str = "+27738916611"

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            o.strip() for o in self.cors_origins.split(",")
            if o.strip() and "*" not in o
        ]

    @property
    def cors_origin_regex(self) -> str | None:
        patterns = [
            o.strip().replace(".", r"\.").replace("*", r"[^/]+")
            for o in self.cors_origins.split(",")
            if o.strip() and "*" in o
        ]
        if not patterns:
            return None
        return "|".join(patterns)

    @field_validator("supabase_url")
    @classmethod
    def strip_rest_v1(cls, v: str) -> str:
        if v:
            v = v.rstrip("/")
            if v.endswith("/rest/v1"):
                v = v[: -len("/rest/v1")]
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()
