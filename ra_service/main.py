import json
import logging
import re
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, File, Form, UploadFile

from ra_service.config import config
from ra_service.instance_manager import RAGAnythingInstanceManager
from ra_service.models import (
    DeleteRequest,
    DeleteResponse,
    IndexConfig,
    IndexResponse,
    MetadataResponse,
    QueryRequest,
    QueryResponse,
    StatusResponse,
)

logger = logging.getLogger(__name__)

instance_manager: RAGAnythingInstanceManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and cleanup resources."""
    global instance_manager
    instance_manager = RAGAnythingInstanceManager(
        base_storage_dir=config.STORAGE_DIR,
        max_instances=config.MAX_INSTANCES,
    )
    logger.info(
        "RA Service started — storage=%s, max_instances=%d",
        config.STORAGE_DIR,
        config.MAX_INSTANCES,
    )
    yield
    logger.info("RA Service shutting down")


app = FastAPI(title="RA Service", version="0.1.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


@app.post("/index")
async def index_document(
    file: UploadFile = File(...),
    kb_id: str = Form(...),
    doc_id: str = Form(...),
    tenant_id: str = Form(...),
    config_json: str = Form("{}"),
) -> IndexResponse:
    index_config = IndexConfig(**json.loads(config_json))
    instance = await instance_manager.get_instance(kb_id)

    # 写入临时文件
    suffix = Path(file.filename or "doc").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 调用 RAGAnything ainsert
        await instance.ainsert(file_path=tmp_path)

        # 统计多模态内容
        doc_stats = _count_multimodal_content(instance, doc_id, index_config)

        await instance_manager.update_metadata(kb_id, doc_id, doc_stats)
        metadata = instance_manager.get_metadata(kb_id)

        return IndexResponse(
            status="completed",
            multimodal_metadata=metadata,
            doc_id=doc_id,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@app.post("/delete")
async def delete_index(request: DeleteRequest) -> DeleteResponse:
    instance = await instance_manager.get_instance(request.kb_id)

    from ra_service.deletion import delete_document_from_lightrag

    deleted_counts = await delete_document_from_lightrag(
        instance, request.doc_id
    )

    await instance_manager.delete_doc_metadata(request.kb_id, request.doc_id)

    return DeleteResponse(status="deleted", deleted_counts=deleted_counts)


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


@app.post("/query")
async def query(request: QueryRequest) -> QueryResponse:
    instance = await instance_manager.get_instance(request.kb_id)
    lightrag = (
        getattr(instance, "rag", None)
        or getattr(instance, "lightrag", None)
        or instance
    )

    from lightrag import QueryParam

    param = QueryParam(mode=request.mode, only_need_context=True)
    context = await lightrag.aquery(request.query, param=param)

    modal_entities = _count_modal_entities(context or "")

    return QueryResponse(
        context=context or "",
        query_mode=request.mode,
        modal_entities_found=modal_entities,
    )


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


@app.get("/metadata/{kb_id}")
async def get_metadata(kb_id: str) -> MetadataResponse:
    metadata = instance_manager.get_metadata(kb_id)
    return MetadataResponse(kb_id=kb_id, metadata=metadata)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


@app.get("/status/{kb_id}/{doc_id}")
async def get_status(kb_id: str, doc_id: str) -> StatusResponse:
    metadata = instance_manager.get_metadata(kb_id)
    if doc_id in metadata.doc_stats:
        return StatusResponse(
            kb_id=kb_id,
            doc_id=doc_id,
            status="completed",
            progress=1.0,
        )
    return StatusResponse(
        kb_id=kb_id,
        doc_id=doc_id,
        status="not_found",
        progress=0.0,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_modal_entities(context: str) -> Dict[str, int]:
    """从 LightRAG 返回的上下文文本中统计模态实体"""
    if not context:
        return {}
    counts: Dict[str, int] = {}
    image_markers = len(
        re.findall(r"\[image\]|\[图片\]|<image>", context, re.IGNORECASE)
    )
    table_markers = len(
        re.findall(r"\[table\]|\[表格\]|<table>", context, re.IGNORECASE)
    )
    equation_markers = len(
        re.findall(
            r"\[equation\]|\[公式\]|<equation>", context, re.IGNORECASE
        )
    )
    if image_markers:
        counts["image"] = image_markers
    if table_markers:
        counts["table"] = table_markers
    if equation_markers:
        counts["equation"] = equation_markers
    return counts


def _count_multimodal_content(
    instance, doc_id: str, config: IndexConfig
) -> Dict[str, int]:
    """统计入库后的多模态内容"""
    stats = {
        "image_count": 0,
        "table_count": 0,
        "equation_count": 0,
        "entity_count": 0,
    }
    lightrag = (
        getattr(instance, "rag", None)
        or getattr(instance, "lightrag", None)
        or instance
    )

    # 尝试从知识图谱统计
    if hasattr(lightrag, "chunk_entity_relation_graph"):
        graph = lightrag.chunk_entity_relation_graph
        for node in graph.nodes():
            node_data = graph.nodes[node]
            if node_data.get("source_doc_id") == doc_id:
                entity_type = node_data.get("entity_type", "").lower()
                if "image" in entity_type:
                    stats["image_count"] += 1
                elif "table" in entity_type:
                    stats["table_count"] += 1
                elif "equation" in entity_type:
                    stats["equation_count"] += 1
                stats["entity_count"] += 1

    return stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=config.HOST, port=config.PORT)
