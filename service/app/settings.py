from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    api_token: str
    mcp_token: str
    forge_enabled: bool = False
    forge_url: str = "https://forge.millyweb.com"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
