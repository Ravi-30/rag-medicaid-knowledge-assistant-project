"""Infrastructure settings — delegates to unified config."""

from healthcare_agents.config import settings


class InfrastructureSettings:
    cloud_provider: str = settings.cloud_provider
    compute: str = settings.compute
    region: str = settings.aws_region
    observability: str = settings.observability
    waf_enabled: bool = True
    kms_encryption: bool = True


class DataStoreSettings:
    postgres_url: str = settings.postgres_url
    redis_url: str = settings.redis_url
    s3_bucket: str = settings.s3_bucket
    vector_store_url: str = settings.vector_store_url
    opensearch_url: str = settings.opensearch_url
    policy_db_url: str = "memory"
