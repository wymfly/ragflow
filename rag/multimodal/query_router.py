"""检索路由器：决定检索执行策略"""
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class RetrievalMode(str, Enum):
    STANDARD = "standard"
    MULTIMODAL = "multimodal"
    AUTO = "auto"


@dataclass
class ExecutionPlan:
    run_standard: bool
    run_ra: bool
    ra_kb_ids: List[str] = field(default_factory=list)
    mode_used: str = "auto"
    reason: str = ""


class QueryRouter:
    def __init__(self, ra_service_url: str | None = None):
        self.ra_service_url = ra_service_url or os.environ.get(
            "RA_SERVICE_URL", "http://localhost:8770"
        )
        self._metadata_cache: Dict[str, Dict] = {}
        self._cache_ttl = 300

    async def decide(
        self,
        kb_ids: List[str],
        retrieval_mode: RetrievalMode = RetrievalMode.AUTO,
        kb_parser_configs: Optional[Dict[str, dict]] = None,
    ) -> ExecutionPlan:
        """三模式路由决策：
        - STANDARD: 只执行标准检索
        - MULTIMODAL: 只执行 RA 检索（跳过标准）
        - AUTO: 基于元数据自动判断，有多模态实体则两路并行
        """
        if retrieval_mode == RetrievalMode.STANDARD:
            return ExecutionPlan(
                run_standard=True,
                run_ra=False,
                mode_used="standard",
                reason="用户指定仅标准检索",
            )

        if retrieval_mode == RetrievalMode.MULTIMODAL:
            ra_kb_ids = self._get_mm_enabled_kb_ids(kb_ids, kb_parser_configs)
            if not ra_kb_ids:
                return ExecutionPlan(
                    run_standard=True,
                    run_ra=False,
                    mode_used="standard",
                    reason="指定多模态但无知识库启用，回退标准检索",
                )
            return ExecutionPlan(
                run_standard=False,
                run_ra=True,
                ra_kb_ids=ra_kb_ids,
                mode_used="multimodal",
                reason="用户指定仅多模态检索",
            )

        # AUTO 模式
        ra_kb_ids = []
        for kb_id in kb_ids:
            config = (kb_parser_configs or {}).get(kb_id, {})
            if not config.get("multimodal_enhance", {}).get(
                "use_multimodal", False
            ):
                continue
            metadata = await self._get_metadata(kb_id)
            if metadata and (
                metadata.get("has_images")
                or metadata.get("has_tables")
                or metadata.get("has_equations")
            ):
                ra_kb_ids.append(kb_id)

        if ra_kb_ids:
            return ExecutionPlan(
                run_standard=True,
                run_ra=True,
                ra_kb_ids=ra_kb_ids,
                mode_used="auto",
                reason=f"知识库 {ra_kb_ids} 含多模态实体，启用并联检索",
            )
        return ExecutionPlan(
            run_standard=True,
            run_ra=False,
            mode_used="auto",
            reason="无知识库含多模态实体",
        )

    def _get_mm_enabled_kb_ids(
        self, kb_ids: List[str], configs: Optional[Dict[str, dict]]
    ) -> List[str]:
        return [
            kb_id
            for kb_id in kb_ids
            if (configs or {})
            .get(kb_id, {})
            .get("multimodal_enhance", {})
            .get("use_multimodal", False)
        ]

    async def _get_metadata(self, kb_id: str) -> Optional[dict]:
        cached = self._metadata_cache.get(kb_id)
        if cached and (time.time() - cached["ts"]) < self._cache_ttl:
            return cached["data"]
        try:
            async with httpx.AsyncClient(
                base_url=self.ra_service_url, timeout=10
            ) as client:
                resp = await client.get(f"/metadata/{kb_id}")
                if resp.status_code == 200:
                    meta = resp.json().get("metadata", {})
                    self._metadata_cache[kb_id] = {
                        "data": meta,
                        "ts": time.time(),
                    }
                    return meta
        except Exception:
            pass
        return None
