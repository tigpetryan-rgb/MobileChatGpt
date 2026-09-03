from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mobile ChatGpt Project Brain"
    database_url: str = "sqlite:///./mobile_chatgpt.db"
    openai_api_key: str | None = None
    openai_manager_model: str = "gpt-5.6-terra"
    openai_worker_model: str = "gpt-5.6-terra"
    openai_trace_include_sensitive_data: bool = False
    mcp_auth_issuer_url: str | None = None
    mcp_resource_server_url: str | None = None
    mcp_token_introspection_url: str | None = None
    mcp_introspection_client_id: str | None = None
    mcp_introspection_client_secret: str | None = None
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


settings = Settings()
