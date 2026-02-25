"""两路检索结果上下文融合器"""

from typing import Dict, List, Optional


class ContextFusion:
    def __init__(
        self,
        ra_context_position: str = "prepend",
        max_ra_context_tokens: int = 4096,
    ):
        self.ra_context_position = ra_context_position
        self.max_ra_context_tokens = max_ra_context_tokens

    def fuse(
        self,
        standard_chunks: List[Dict],
        ra_context: Optional[str],
        ra_entities: Optional[Dict] = None,
    ) -> Dict:
        result = {
            "chunks": standard_chunks,
            "doc_aggs": self._build_doc_aggs(standard_chunks),
            "ra_context": None,
            "retrieval_stats": {
                "standard_count": len(standard_chunks),
                "ra_count": 0,
                "mode_used": "standard",
                "multimodal_activated": False,
            },
        }

        if ra_context:
            truncated = self.truncate_context(ra_context, self.max_ra_context_tokens)
            result["ra_context"] = truncated
            result["retrieval_stats"]["ra_count"] = 1
            result["retrieval_stats"]["multimodal_activated"] = True
            if ra_entities:
                result["retrieval_stats"]["modal_hits"] = ra_entities

        return result

    @staticmethod
    def truncate_context(text: str, max_tokens: int) -> str:
        """粗略按 token 数截断（中文约 2 字符/token）"""
        estimated_tokens = len(text) // 2
        if estimated_tokens <= max_tokens:
            return text
        char_limit = max_tokens * 2
        return text[:char_limit] + "\n...[上下文已截断]"

    @staticmethod
    def _build_doc_aggs(chunks: List[Dict]) -> List[Dict]:
        doc_map: Dict[str, Dict] = {}
        for c in chunks:
            did = c.get("doc_id", "")
            if did not in doc_map:
                doc_map[did] = {
                    "doc_id": did,
                    "doc_name": c.get("docnm_kwd", ""),
                    "count": 0,
                }
            doc_map[did]["count"] += 1
        return list(doc_map.values())
