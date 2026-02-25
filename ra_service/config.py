import os


class RAServiceConfig:
    STORAGE_DIR: str = os.environ.get("RA_STORAGE_DIR", "/app/data")
    LLM_MODEL: str = os.environ.get("RA_LLM_MODEL", "qwen-plus")
    LLM_API_KEY: str = os.environ.get("RA_LLM_API_KEY", "")
    LLM_BASE_URL: str = os.environ.get(
        "RA_LLM_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    EMBEDDING_MODEL: str = os.environ.get("RA_EMBEDDING_MODEL", "text-embedding-v3")
    EMBEDDING_API_KEY: str = os.environ.get("RA_EMBEDDING_API_KEY", "")
    EMBEDDING_BASE_URL: str = os.environ.get(
        "RA_EMBEDDING_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    MAX_INSTANCES: int = int(os.environ.get("RA_MAX_INSTANCES", "20"))
    HOST: str = os.environ.get("RA_SERVICE_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("RA_SERVICE_PORT", "8770"))


config = RAServiceConfig()
