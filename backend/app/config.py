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
