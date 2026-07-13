from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://mactral:mactral@localhost:5432/mactral"
    jwt_secret: str = "dev-secret-cambia-esto-en-produccion"
    cors_origins: list[str] = ["http://localhost:5173"]
    # E2-H4: services/projects — para crear el Registro Maestro al clasificar
    # un lead como Vendido (GM/Stock), reenviando el JWT del actor.
    projects_service_url: str = "http://localhost:8100"


settings = Settings()
