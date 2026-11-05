from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    public_origin: str = "http://localhost:5173"
    secure_cookies: bool = True
    session_hours: int = 8
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_from: str = "no-reply@academic-integrity.local"
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    environment: str = "production"
    storage_root: str = "/var/lib/academic-integrity/documents"
    max_file_bytes: int = 25 * 1024 * 1024
    max_request_bytes: int = 64 * 1024 * 1024
    max_batch_files: int = 100
    max_pdf_pages: int = 300
    max_zip_bytes: int = 100 * 1024 * 1024
    max_zip_entries: int = 2000
    max_document_chars: int = 500_000
    extraction_timeout: int = 45
    bibliography_external_enabled: bool = False
    openalex_api_key: str = ""
    max_audit_sources: int = 20
    max_audit_chars: int = 1_000_000
    max_literal_findings: int = 500
    max_literal_seeds: int = 50_000
    max_literal_checks: int = 2_000_000

    @model_validator(mode="after")
    def production(self) -> "Settings":
        if self.environment not in {"development", "test", "production"}:
            raise ValueError("Entorno inválido")
        if self.environment == "production":
            if not self.secure_cookies or not self.public_origin.startswith("https://"):
                raise ValueError("Producción requiere HTTPS y cookies Secure")
            if not self.smtp_starttls:
                raise ValueError("Producción requiere SMTP con STARTTLS")
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
