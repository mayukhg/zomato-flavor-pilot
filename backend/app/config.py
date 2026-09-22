"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/flavorpilot"
    
    # MCP Configuration — official hosted server via mcp-remote (OAuth in the browser)
    use_mock_mcp: bool = False
    zomato_mcp_transport: Literal["http", "sse", "stdio"] = "stdio"
    zomato_mcp_server_url: str = "https://mcp-server.zomato.com/mcp"
    zomato_mcp_stdio_cmd: str = "npx -y mcp-remote https://mcp-server.zomato.com/mcp"
    zomato_address_id: str = "217570301"
    zomato_api_key: str = ""
    
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    smart_intern_model: str = "meta-llama/llama-3.3-70b-instruct"
    phd_reasoner_model: str = "anthropic/claude-sonnet-4"
    routing_threshold: float = 0.75
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
