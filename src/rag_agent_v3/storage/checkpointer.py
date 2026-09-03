"""
Checkpointer（v3）
==================

本地开发默认 in-memory（重启丢状态），通过环境变量切换：
- CHECKPOINTER_BACKEND=memory（默认）
- CHECKPOINTER_BACKEND=sqlite（持久化到本地）
- CHECKPOINTER_BACKEND=postgres（生产）
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

BACKEND = os.getenv("CHECKPOINTER_BACKEND", "memory").lower()


def get_checkpointer() -> Any:
    """获取 checkpointer。"""
    if BACKEND == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        logger.info("Checkpointer: in-memory (data lost on restart)")
        return MemorySaver()

    if BACKEND == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver
        path = os.getenv("SQLITE_PATH", "./data/checkpoints.db")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        logger.info("Checkpointer: SQLite at %s", path)
        return SqliteSaver.from_conn_string(path)

    if BACKEND == "postgres":
        # 生产接入
        raise NotImplementedError("Postgres checkpointer 待生产接入")

    raise ValueError(f"Unknown checkpointer backend: {BACKEND}")


__all__ = ["get_checkpointer", "BACKEND"]
