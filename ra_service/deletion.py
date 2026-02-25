import logging
from typing import Dict

logger = logging.getLogger(__name__)


async def delete_document_from_lightrag(
    instance,
    doc_id: str,
) -> Dict[str, int]:
    """从 LightRAG 存储中删除指定文档的全部数据

    操作顺序：
    1. text_chunks KV store — 按 full_doc_id 过滤
    2. chunks_vdb — 删除对应向量
    3. chunk_entity_relation_graph (NetworkX) — 移除关联节点和边
    4. entities_vdb / relationships_vdb — 同步清理
    5. doc_status — 删除状态记录
    """
    # RAGAnything 实例的 LightRAG 在 .rag 属性中
    lightrag = (
        getattr(instance, "rag", None)
        or getattr(instance, "lightrag", None)
        or instance
    )
    deleted_counts = {"chunks": 0, "entities": 0, "relationships": 0}

    # Step 1: 找到该文档的所有 chunk IDs
    chunk_ids = []
    if hasattr(lightrag, "text_chunks"):
        try:
            all_chunks = await lightrag.text_chunks.get_all()
            for cid, chunk_data in all_chunks.items():
                if chunk_data.get("full_doc_id") == doc_id:
                    chunk_ids.append(cid)
        except Exception as e:
            logger.warning("Failed to enumerate text_chunks: %s", e)

    # Step 2: 删除 chunks
    for cid in chunk_ids:
        try:
            if hasattr(lightrag, "text_chunks"):
                await lightrag.text_chunks.delete(cid)
            if hasattr(lightrag, "chunks_vdb"):
                await lightrag.chunks_vdb.delete(cid)
            deleted_counts["chunks"] += 1
        except Exception as e:
            logger.warning("Failed to delete chunk %s: %s", cid, e)

    # Step 3: 清理图谱实体
    if hasattr(lightrag, "chunk_entity_relation_graph"):
        graph = lightrag.chunk_entity_relation_graph
        nodes_to_remove = [
            node
            for node in graph.nodes()
            if graph.nodes[node].get("source_doc_id") == doc_id
        ]

        edges_to_remove = set()
        for node in nodes_to_remove:
            for u, v in graph.edges(node):
                edges_to_remove.add((u, v))

        for node in nodes_to_remove:
            graph.remove_node(node)
            deleted_counts["entities"] += 1

        # Step 4: 同步清理 VDB（使用 compute_mdhash_id 生成 hash key）
        try:
            from lightrag.utils import compute_mdhash_id

            if hasattr(lightrag, "entities_vdb"):
                for node in nodes_to_remove:
                    entity_vdb_id = compute_mdhash_id(node, prefix="ent-")
                    await lightrag.entities_vdb.delete(entity_vdb_id)

            if hasattr(lightrag, "relationships_vdb"):
                for u, v in edges_to_remove:
                    relation_vdb_id = compute_mdhash_id(
                        u + v, prefix="rel-"
                    )
                    await lightrag.relationships_vdb.delete(relation_vdb_id)
                    deleted_counts["relationships"] += 1
        except ImportError:
            logger.warning(
                "lightrag.utils not available, skipping VDB cleanup"
            )

    # Step 5: 更新 doc_status
    if hasattr(lightrag, "doc_status"):
        try:
            await lightrag.doc_status.delete(doc_id)
        except Exception as e:
            logger.warning(
                "Failed to delete doc_status for %s: %s", doc_id, e
            )

    return deleted_counts
