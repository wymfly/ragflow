"""RAG-Anything 入库协调器

从 STORAGE_IMPL 获取文件二进制后，通过 HTTP multipart 上传到 RA Service。
不依赖共享文件系统。
"""

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class MultimodalIndexer:
    """RAGFlow 与 RA Service（:8770）之间的 HTTP 客户端桥梁。

    所有方法捕获异常后 log warning 并返回 None/False，
    不向上抛异常（故障隔离原则）。
    """

    def __init__(self, ra_service_url: str | None = None) -> None:
        self.ra_service_url: str = ra_service_url or os.environ.get(
            "RA_SERVICE_URL", "http://localhost:8770"
        )
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=self.ra_service_url,
            timeout=httpx.Timeout(connect=10, read=600, write=60, pool=10),
        )

    async def index_document(
        self,
        kb_id: str,
        doc_id: str,
        file_binary: bytes,
        file_name: str,
        tenant_id: str,
        config: dict,
    ) -> Optional[dict]:
        """将文件二进制上传到 RA Service 构建多模态索引。

        使用 multipart/form-data 上传，config 通过 config_json 字段
        以 JSON 字符串传递。
        """
        try:
            response = await self.client.post(
                "/index",
                files={"file": (file_name, file_binary)},
                data={
                    "kb_id": kb_id,
                    "doc_id": doc_id,
                    "tenant_id": tenant_id,
                    "config_json": json.dumps({
                        "enable_image": config.get("enable_image", True),
                        "enable_table": config.get("enable_table", True),
                        "enable_equation": config.get("enable_equation", True),
                        "parser": config.get("parser", "mineru"),
                        "context_window": config.get("context_window", 1),
                    }),
                },
            )
            response.raise_for_status()
            return response.json().get("multimodal_metadata")
        except Exception as e:
            logger.warning("RA indexing failed for doc %s: %s", doc_id, e)
            return None

    async def delete_document(self, kb_id: str, doc_id: str) -> bool:
        """删除文档的多模态索引。"""
        try:
            response = await self.client.post(
                "/delete", json={"kb_id": kb_id, "doc_id": doc_id}
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning("RA index deletion failed for doc %s: %s", doc_id, e)
            return False

    async def query(
        self, kb_id: str, query: str, mode: str = "mix"
    ) -> Optional[dict]:
        """查询 RA Service 获取多模态上下文。"""
        try:
            response = await self.client.post(
                "/query", json={"kb_id": kb_id, "query": query, "mode": mode}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.warning("RA query failed for kb %s: %s", kb_id, e)
            return None

    async def get_metadata(self, kb_id: str) -> Optional[dict]:
        """获取知识库多模态元数据。"""
        try:
            response = await self.client.get(f"/metadata/{kb_id}")
            if response.status_code == 200:
                return response.json().get("metadata")
            return None
        except Exception as e:
            logger.warning("RA metadata fetch failed for kb %s: %s", kb_id, e)
            return None

    async def close(self) -> None:
        """关闭 httpx client。"""
        await self.client.aclose()
