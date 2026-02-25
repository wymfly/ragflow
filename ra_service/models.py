from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field

from typing import Literal


class ModalType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    EQUATION = "equation"


class IndexConfig(BaseModel):
    enable_image: bool = True
    enable_table: bool = True
    enable_equation: bool = True
    parser: str = "mineru"
    context_window: int = 1
    max_context_tokens: int = 2000


class MultimodalMetadata(BaseModel):
    has_images: bool = False
    has_tables: bool = False
    has_equations: bool = False
    image_count: int = 0
    table_count: int = 0
    equation_count: int = 0
    entity_count: int = 0
    relationship_count: int = 0
    doc_stats: Dict[str, Dict[str, int]] = Field(default_factory=dict)


class DeleteRequest(BaseModel):
    kb_id: str
    doc_id: str


class QueryRequest(BaseModel):
    kb_id: str
    query: str
    mode: Literal["local", "global", "hybrid", "naive", "mix"] = "mix"


class QueryResponse(BaseModel):
    context: str
    context_with_images: Optional[str] = None
    modal_entities_found: Dict[str, int] = Field(default_factory=dict)
    query_mode: str


class IndexResponse(BaseModel):
    status: str
    multimodal_metadata: MultimodalMetadata
    doc_id: str


class DeleteResponse(BaseModel):
    status: str
    deleted_counts: Dict[str, int] = Field(default_factory=dict)


class MetadataResponse(BaseModel):
    kb_id: str
    metadata: MultimodalMetadata


class StatusResponse(BaseModel):
    kb_id: str
    doc_id: str
    status: str
    progress: float = 0.0
