"""Configuration management using Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # LLM Configuration
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.1
    
    # NCBI/PubMed
    ncbi_api_key: str | None = None
    ncbi_email: str = "user@example.com"
    
    # Search parameters
    max_pubmed_results: int = 50
    max_gwas_results: int = 100
    enable_cache: bool = True
    
    # Rate limiting
    requests_per_second: float = 3.0
    
    def get_llm_provider(self) -> str:
        """Determine which LLM provider to use."""
        if self.openai_api_key:
            return "openai"
        elif self.anthropic_api_key:
            return "anthropic"
        raise ValueError("No LLM API key configured")


# Global settings instance
settings = Settings()
