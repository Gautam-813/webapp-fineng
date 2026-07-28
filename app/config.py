from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "TheFinanceCompany"
    environment: str = "development"
    debug: bool = False
    database_url: str = "sqlite:///./thefinancecompany.db"
    auto_create_tables: bool = True
    secret_key: str = "change-me-in-production"
    secure_cookies: bool = False
    cookie_samesite: str = "lax"
    allowed_hosts: str = "*"
    cors_origins: str = ""
    csrf_protection_enabled: bool = True
    csrf_exempt_paths: str = "/api/payments/webhook"
    rate_limit_enabled: bool = True
    max_upload_size_mb: int = 5
    resend_api_key: str = ""
    email_from_login: str = "login@thefinanceengine.com"
    email_enabled: bool = False
    otp_expiry_minutes: int = 10
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 5
    registration_allowed_domains: str = "gmail.com"

    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""

    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_mode: str = "sandbox"

    site_url: str = "http://localhost:8000"

    @property
    def trusted_host_list(self) -> list[str]:
        return _split_csv(self.allowed_hosts) or ["*"]

    @property
    def cors_origin_list(self) -> list[str]:
        return _split_csv(self.cors_origins) or [self.site_url]

    @property
    def csrf_exempt_path_list(self) -> list[str]:
        return _split_csv(self.csrf_exempt_paths)

    @property
    def max_upload_size_bytes(self) -> int:
        return max(self.max_upload_size_mb, 1) * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def registration_domain_list(self) -> list[str]:
        return [item.lower() for item in _split_csv(self.registration_allowed_domains)]

    class Config:
        env_file = ".env"
        case_sensitive = False


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
