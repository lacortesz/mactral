from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://mactral:mactral@localhost:5432/mactral"
    jwt_secret: str = "dev-secret-cambia-esto-en-produccion"
    session_ttl_hours: int = 8
    activation_token_ttl_hours: int = 48
    reset_token_ttl_hours: int = 2
    max_failed_login_attempts: int = 5
    lockout_minutes: int = 15
    app_base_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
