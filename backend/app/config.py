"""Configuration de l'application, lue depuis l'environnement.

Les identifiants n'ont volontairement aucune valeur par défaut : mieux vaut
un démarrage qui échoue clairement qu'un secret en dur dans le dépôt.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BA_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "body-analysis-photos"
    minio_secure: bool = False


settings = Settings()  # type: ignore[call-arg]
