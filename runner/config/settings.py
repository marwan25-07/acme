from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file= ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"   
    )
    
    # main model
    main_endpoint: str = "https://example.invalid"
    main_model_name: str = "gpt-4.1"
    main_deployment: str = "gpt-4.1"
    main_api_key: str = ""
    main_api_version: str = "2025-04-01-preview"

    # mini model
    mini_endpoint: str = "https://example.invalid"
    mini_model_name: str = "gpt-4.1-mini"
    mini_deployment: str = "gpt-4.1-mini"
    mini_api_key: str = ""
    mini_api_version: str = "2025-04-01-preview"

    # keycloak configuration
    keycloak_url: str = "http://localhost:8080"
    realm_name: str = "acme"
    client_id: str = "acme-client"

    # redis configuration 
    redis_url: str = "https://example.invalid"
    agent_memory_expiry_ttl:int = 0

    # postgresql configuration 
    postgresql_url: str = "https://example.invalid"
    postgresql_host: str = ""
    postgresql_port: int = 0
    postgresql_database: str = ""
    postgresql_user: str = ""
    postgresql_password: str = ""

acme_settings = Settings()