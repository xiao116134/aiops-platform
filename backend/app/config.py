from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'AiOps API'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    jwt_secret_key: str = 'change-this-in-production'
    jwt_expire_minutes: int = 120
    database_url: str = ''

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False)

    @property
    def cors_origin_list(self) -> list[str]:
        origins: list[str] = []
        for item in self.cors_origins.split(','):
            origin = item.strip().rstrip('/')
            if origin:
                origins.append(origin)
        return origins


settings = Settings()
