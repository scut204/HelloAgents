"""Mem0.ai 记忆适配层

提供对 `mem0ai`/`mem0` 客户端的轻量封装，使其符合 HelloAgents
内部的 `BaseMemory` 接口要求，便于与现有记忆管理器统一调度。

设计目标：
- 以最小侵入方式集成第三方记忆服务
- 在未安装 mem0 库时提供清晰的提示
- 尽量兼容 `mem0` 与 `mem0ai` 两种包名及常见客户端接口
"""

from __future__ import annotations

import importlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseMemory, MemoryConfig, MemoryItem


class Mem0Memory(BaseMemory):
    """基于 Mem0.ai 的记忆实现。

    默认会尝试自动加载 ``mem0`` 或 ``mem0ai`` 包下的 ``MemoryClient``/``Memory``
    客户端，也支持外部传入已经初始化好的客户端实例，以便自定义配置。
    """

    def __init__(
        self,
        config: MemoryConfig,
        *,
        client: Any = None,
        user_id: str = "default_user",
        api_key: Optional[str] = None,
        client_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(config, storage_backend=None)
        self.user_id = user_id
        self.client = client or self._init_client(api_key=api_key, options=client_options)

    # BaseMemory 接口实现
    def add(self, memory_item: MemoryItem) -> str:
        payload: Dict[str, Any] = {
            "user_id": memory_item.user_id or self.user_id,
            "metadata": memory_item.metadata or {},
        }

        response = self.client.add(memory_item.content, **payload)
        memory_id = self._extract_memory_id(response) or memory_item.id or self._generate_id()
        return memory_id

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> List[MemoryItem]:
        search_params: Dict[str, Any] = {
            "user_id": user_id or self.user_id,
            "limit": limit,
        }
        filtered_kwargs = {
            key: value for key, value in kwargs.items() if key not in {"min_importance"}
        }
        search_params.update(filtered_kwargs)

        raw_results = self.client.search(query, **search_params)
        normalized: List[MemoryItem] = []

        if not raw_results:
            return normalized

        for item in raw_results:
            normalized.append(self._normalize_record(item, default_user=search_params["user_id"]))

        return normalized[:limit]

    def update(
        self,
        memory_id: str,
        content: str = None,
        importance: float = None,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        update_payload: Dict[str, Any] = {"metadata": metadata or {}}

        if content is not None:
            update_payload["content"] = content
        if importance is not None:
            update_payload["importance"] = importance

        response = self.client.update(memory_id, data=update_payload)
        return bool(response)

    def remove(self, memory_id: str) -> bool:
        response = self.client.delete(memory_id)
        return bool(response) or response is None

    def has_memory(self, memory_id: str) -> bool:
        result = self.client.get(memory_id)
        return bool(result)

    def clear(self):
        if hasattr(self.client, "clear"):
            self.client.clear(user_id=self.user_id)
        elif hasattr(self.client, "delete_all"):
            self.client.delete_all(user_id=self.user_id)

    def get_stats(self) -> Dict[str, Any]:
        all_memories = self.get_all()
        return {
            "count": len(all_memories),
            "memory_type": "mem0",
            "user_id": self.user_id,
        }

    # 扩展工具方法
    def get_all(self) -> List[MemoryItem]:
        records: List[Any] = []
        if hasattr(self.client, "history"):
            records = self.client.history(user_id=self.user_id) or []
        elif hasattr(self.client, "list"):
            records = self.client.list(user_id=self.user_id) or []

        return [self._normalize_record(record, default_user=self.user_id) for record in records]

    # 内部辅助方法
    def _init_client(
        self, *, api_key: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        mem0_spec = importlib.util.find_spec("mem0")
        mem0ai_spec = importlib.util.find_spec("mem0ai") if mem0_spec is None else None

        module_name = None
        if mem0_spec is not None:
            module_name = "mem0"
        elif mem0ai_spec is not None:
            module_name = "mem0ai"

        if module_name is None:
            raise ImportError(
                "Mem0Memory 需要安装 mem0ai（pip install mem0ai）或提供自定义客户端实例"
            )

        module = importlib.import_module(module_name)
        client_cls = getattr(module, "MemoryClient", None) or getattr(module, "Memory", None)

        if client_cls is None:
            raise ImportError(f"在模块 {module_name} 中未找到 MemoryClient/Memory 客户端接口")

        client_init_options = options.copy() if options else {}
        if api_key is not None and "api_key" not in client_init_options:
            client_init_options["api_key"] = api_key

        return client_cls(**client_init_options)

    def _normalize_record(self, record: Any, default_user: str) -> MemoryItem:
        if isinstance(record, dict):
            memory_id = self._extract_memory_id(record) or self._generate_id()
            content = (
                record.get("content")
                or record.get("text")
                or record.get("value")
                or record.get("message")
                or ""
            )
            timestamp_raw = record.get("timestamp") or record.get("created_at")
            timestamp = self._parse_timestamp(timestamp_raw)
            importance = record.get("score") or record.get("importance") or 0.5
            metadata = record.get("metadata") or record.get("meta") or {}
            user = record.get("user_id") or default_user
        else:
            memory_id = self._generate_id()
            content = str(record)
            timestamp = datetime.now()
            importance = 0.5
            metadata = {}
            user = default_user

        return MemoryItem(
            id=str(memory_id),
            content=content,
            memory_type="mem0",
            user_id=user,
            timestamp=timestamp,
            importance=float(importance),
            metadata=metadata,
        )

    def _extract_memory_id(self, data: Any) -> Optional[str]:
        if isinstance(data, dict):
            return data.get("id") or data.get("memory_id") or data.get("uuid")
        return None

    def _parse_timestamp(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return datetime.now()


__all__ = ["Mem0Memory"]
