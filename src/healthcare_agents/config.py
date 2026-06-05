from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Unified application settings (runtime + infrastructure)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_env: str = "development"
    app_name: str = "classroom-Healthcare-Medicaid-customer-service-agenticAI"

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"

    # Safety
    phi_redaction_enabled: bool = True
    clinical_disclaimer_enabled: bool = True

    # Logging & audit
    log_level: str = "INFO"
    audit_log_path: str = "logs/audit.log"

    # Integrations
    fhir_base_url: str = "https://hapi.fhir.org/baseR4"
    rag_base_url: str = "memory"
    api_gateway_url: str = "local"
    api_gateway_key: str = ""

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Infrastructure (Layer 7)
    cloud_provider: str = "aws"
    compute: str = "eks"
    aws_region: str = "us-east-1"
    observability: str = "cloudwatch"

    # Data stores (Layer 6)
    postgres_url: str = "postgresql://localhost:5432/healthcare"
    redis_url: str = "redis://localhost:6379/0"
    s3_bucket: str = "xyz-healthcare-documents"
    vector_store_url: str = "memory"
    opensearch_url: str = ""


settings = Settings()
