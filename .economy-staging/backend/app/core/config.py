from functools import lru_cache

from pydantic import computed_field
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
