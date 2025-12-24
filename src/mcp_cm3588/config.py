"""Configuration for MCP CM3588 server."""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class SSHConfig(BaseModel):
    """SSH connection configuration for CM3588."""

    host: str = Field(default_factory=lambda: os.getenv("CM3588_HOST", ""))
    user: str = Field(default_factory=lambda: os.getenv("CM3588_USER", "root"))
    ssh_key: str | None = Field(default_factory=lambda: os.getenv("CM3588_SSH_KEY"))
    password: str | None = Field(default_factory=lambda: os.getenv("CM3588_PASSWORD"))
    port: int = Field(default=22)


class QdrantConfig(BaseModel):
    """Qdrant configuration."""

    host: str = Field(default_factory=lambda: os.getenv("QDRANT_HOST", "localhost"))
    port: int = Field(default_factory=lambda: int(os.getenv("QDRANT_PORT", "6333")))
    collection: str = Field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION", "cm3588_knowledge")
    )


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""

    model_name: str = Field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
    )


class Config(BaseModel):
    """Main configuration."""

    ssh: SSHConfig = Field(default_factory=SSHConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    knowledge_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("KNOWLEDGE_DIR", "./knowledge"))
    )


config = Config()
