import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Dict

from ra_service.models import MultimodalMetadata

logger = logging.getLogger(__name__)


class RAGAnythingInstanceManager:
    """按知识库管理 RAGAnything/LightRAG 实例，懒加载 + LRU 淘汰。"""

    def __init__(
        self,
        base_storage_dir: str = "/app/data",
        max_instances: int = 20,
    ):
        self.base_storage_dir = base_storage_dir
        self.max_instances = max_instances
        self._instances: OrderedDict = OrderedDict()
        self._metadata_cache: Dict[str, MultimodalMetadata] = {}

    async def get_instance(self, kb_id: str):
        """获取或创建知识库对应的 RAGAnything 实例"""
        if kb_id in self._instances:
            self._instances.move_to_end(kb_id)
            return self._instances[kb_id]

        if len(self._instances) >= self.max_instances:
            evicted_id, evicted = self._instances.popitem(last=False)
            logger.info("Evicting LRU instance: %s", evicted_id)

        working_dir = str(Path(self.base_storage_dir) / kb_id)
        Path(working_dir).mkdir(parents=True, exist_ok=True)
        instance = await self._create_instance(working_dir)
        self._instances[kb_id] = instance
        return instance

    async def _create_instance(self, working_dir: str):
        """创建 RAGAnything 实例

        使用 OpenAI 兼容 API（通过环境变量配置）。
        RAGAnything 内部管理 LightRAG 实例和模型函数。
        """
        from ra_service.config import config

        try:
            from lightrag import LightRAG
            from lightrag.llm.openai import openai_complete_if_cache, openai_embed
            from raganything import RAGAnything

            # 创建 LightRAG 实例
            lightrag = LightRAG(
                working_dir=working_dir,
                llm_model_func=openai_complete_if_cache,
                llm_model_name=config.LLM_MODEL,
                llm_model_kwargs={
                    "api_key": config.LLM_API_KEY,
                    "base_url": config.LLM_BASE_URL,
                },
                embedding_func=openai_embed,
                embedding_model_name=config.EMBEDDING_MODEL,
                embedding_model_kwargs={
                    "api_key": config.EMBEDDING_API_KEY or config.LLM_API_KEY,
                    "base_url": config.EMBEDDING_BASE_URL or config.LLM_BASE_URL,
                },
            )

            # 创建 RAGAnything 实例
            rag = RAGAnything(rag=lightrag)
            return rag
        except ImportError as e:
            logger.error("Failed to import RAGAnything/LightRAG: %s", e)
            raise

    def get_metadata(self, kb_id: str) -> MultimodalMetadata:
        if kb_id in self._metadata_cache:
            return self._metadata_cache[kb_id]
        return self._load_metadata_from_disk(kb_id)

    def _load_metadata_from_disk(self, kb_id: str) -> MultimodalMetadata:
        meta_path = Path(self.base_storage_dir) / kb_id / "metadata.json"
        if meta_path.exists():
            data = json.loads(meta_path.read_text())
            meta = MultimodalMetadata(**data)
            self._metadata_cache[kb_id] = meta
            return meta
        return MultimodalMetadata()

    async def update_metadata(
        self, kb_id: str, doc_id: str, doc_stats: Dict
    ) -> None:
        meta = self.get_metadata(kb_id)
        meta.doc_stats[doc_id] = doc_stats
        self._recalculate_aggregates(meta)
        self._metadata_cache[kb_id] = meta
        await self._persist_metadata(kb_id, meta)

    async def delete_doc_metadata(self, kb_id: str, doc_id: str) -> None:
        meta = self.get_metadata(kb_id)
        meta.doc_stats.pop(doc_id, None)
        self._recalculate_aggregates(meta)
        self._metadata_cache[kb_id] = meta
        await self._persist_metadata(kb_id, meta)

    @staticmethod
    def _recalculate_aggregates(meta: MultimodalMetadata) -> None:
        meta.image_count = sum(
            d.get("image_count", 0) for d in meta.doc_stats.values()
        )
        meta.table_count = sum(
            d.get("table_count", 0) for d in meta.doc_stats.values()
        )
        meta.equation_count = sum(
            d.get("equation_count", 0) for d in meta.doc_stats.values()
        )
        meta.entity_count = sum(
            d.get("entity_count", 0) for d in meta.doc_stats.values()
        )
        meta.has_images = meta.image_count > 0
        meta.has_tables = meta.table_count > 0
        meta.has_equations = meta.equation_count > 0

    async def _persist_metadata(
        self, kb_id: str, meta: MultimodalMetadata
    ) -> None:
        meta_path = Path(self.base_storage_dir) / kb_id / "metadata.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(meta.model_dump_json(indent=2))

    async def remove_instance(self, kb_id: str) -> None:
        if kb_id in self._instances:
            del self._instances[kb_id]
        self._metadata_cache.pop(kb_id, None)
