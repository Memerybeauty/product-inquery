"""
飞书 bot 适配器（v3 · WebSocket 长连接）
=========================================

用 lark-oapi SDK 启动 WebSocket client，接收 im.message.receive_v1 事件，
调 v3 agent 处理，回复消息。

== 配置 ==

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx   # 飞书后台 → 机器人 → 凭证与基础信息
```

== 启动 ==

```bash
uv run python -m rag_agent_v3.bot.feishu
```

== 行为 ==

- 单聊 / 群聊都接收（text 消息）
- 每条消息独立 thread_id，会话隔离
- agent 完整跑 v3 三路径 + 合规中间件链
- 异常时回退固定话术
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any

# 加载 .env（兼容直接 `python -m rag_agent_v3.bot.feishu` 调用）
try:
    from dotenv import load_dotenv
    _ENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH)
except ImportError:
    pass

from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    GetMessageResourceRequest,
    P2ImMessageReceiveV1,
)
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.ws.client import Client as WSClient
import lark_oapi as lark

logger = logging.getLogger(__name__)

# 飞书配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "cli_a979a524ac7b5cd4")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")


# ---------- 消息解析 ----------

def _extract_text(event: P2ImMessageReceiveV1) -> str:
    """从飞书事件提取纯文本"""
    msg = event.event.message
    if not msg:
        return ""
    msg_type = msg.message_type
    content_raw = msg.content or ""

    if msg_type == "text":
        try:
            return json.loads(content_raw).get("text", "")
        except json.JSONDecodeError:
            return content_raw

    # 其他类型（image / file / post）先简单返回提示
    return f"[{msg_type} 类型暂不支持]"


def _get_message_id(event: P2ImMessageReceiveV1) -> str:
    msg = event.event.message
    return msg.message_id if msg else ""


def _get_sender_id(event: P2ImMessageReceiveV1) -> str:
    sender = event.event.sender
    if sender and sender.sender_id:
        return sender.sender_id.open_id or sender.sender_id.user_id or ""
    return ""


def _get_chat_id(event: P2ImMessageReceiveV1) -> str:
    msg = event.event.message
    return msg.chat_id if msg else ""


def _get_chat_type(event: P2ImMessageReceiveV1) -> str:
    msg = event.event.message
    return msg.chat_type if msg else "p2p"  # p2p | group


# ---------- 消息发送 ----------

def _reply_text(
    http_client: lark.Client,
    message_id: str,
    text: str,
) -> None:
    """回复消息（用 message_id 作为 receive_id，quote 形式）"""
    body = (
        CreateMessageRequestBody.builder()
        .msg_type("text")
        .content(json.dumps({"text": text}, ensure_ascii=False))
        .build()
    )
    # 用 message_id 引用原消息
    req = (
        CreateMessageRequest.builder()
        .message_id(message_id)
        .request_body(body)
        .build()
    )
    resp = http_client.im.v1.message.create(req)
    if not resp.success():
        logger.error("回复失败: code=%s, msg=%s", resp.code, resp.msg)
    else:
        new_id = resp.data.message_id if resp.data else "?"
        logger.info("回复成功: message_id=%s", new_id)


# ---------- Agent 调度 ----------

_agent_instance: Any = None
_agent_lock = threading.Lock()


def _get_agent() -> Any:
    """懒加载 agent（首次调用时 build）"""
    global _agent_instance
    if _agent_instance is not None:
        return _agent_instance
    with _agent_lock:
        if _agent_instance is None:
            from rag_agent_v3 import build_agent
            logger.info("Building v3 agent for feishu bot...")
            _agent_instance = build_agent()
            logger.info("Agent ready")
    return _agent_instance


def _run_agent(agent: Any, user_text: str, sender_id: str) -> str:
    """跑 agent 处理单条消息"""
    from langchain_core.runnables import RunnableConfig

    # thread_id 用 sender 隔离
    thread_id = f"feishu:{sender_id}"
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_text}]},
            config=config,
        )
        messages = result.get("messages", [])
        if not messages:
            return "（无响应）"
        last = messages[-1]
        content = last.content if hasattr(last, "content") else str(last)
        return content if isinstance(content, str) else str(content)
    except Exception as e:
        logger.exception("Agent 调用异常")
        return f"抱歉，服务暂时不可用，请稍后重试。错误：{type(e).__name__}"


# ---------- 事件处理 ----------

def _make_handler(http_client: lark.Client):
    """构造飞书事件 handler"""

    def on_message_receive(data: P2ImMessageReceiveV1) -> None:
        try:
            text = _extract_text(data)
            message_id = _get_message_id(data)
            sender_id = _get_sender_id(data)
            chat_type = _get_chat_type(data)

            logger.info(
                "[feishu] recv · chat=%s · sender=%s · text=%s",
                chat_type, sender_id, text[:80],
            )

            if not text:
                return

            # 跳过机器人自己发的消息
            if sender_id == FEISHU_APP_ID:
                return

            agent = _get_agent()
            response = _run_agent(agent, text, sender_id)
            logger.info("[feishu] reply · text=%s", response[:80])

            # 飞书消息长度限制 4000 字符
            if len(response) > 4000:
                response = response[:3990] + "..."

            _reply_text(http_client, message_id, response)

        except Exception as e:
            logger.exception("处理消息异常")

    return on_message_receive


# ---------- 启动入口 ----------

def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "DEBUG"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # 提升 lark SDK 日志级别
    logging.getLogger("lark_oapi").setLevel(logging.DEBUG)
    logging.getLogger("Lark").setLevel(logging.DEBUG)

    if not FEISHU_APP_SECRET:
        logger.error("FEISHU_APP_SECRET 未设置，请在 .env 配置")
        sys.exit(1)

    logger.info("Starting feishu bot · app_id=%s", FEISHU_APP_ID)

    # 1. HTTP client：用于发消息
    http_client = (
        lark.Client.builder()
        .app_id(FEISHU_APP_ID)
        .app_secret(FEISHU_APP_SECRET)
        .build()
    )
    logger.info("HTTP client ready (for sending messages)")

    # 2. WebSocket client：用于收消息
    from lark_oapi.core.enum import LogLevel as LarkLogLevel

    _lvl = logger.getEffectiveLevel()
    if _lvl <= 10:
        lark_lvl = LarkLogLevel.DEBUG
    elif _lvl <= 20:
        lark_lvl = LarkLogLevel.INFO
    elif _lvl <= 30:
        lark_lvl = LarkLogLevel.WARNING
    else:
        lark_lvl = LarkLogLevel.ERROR

    handler = (
        EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(_make_handler(http_client))
        .build()
    )

    # DEBUG: 打印已注册的事件 processor
    logger.info("Registered processors: %s", list(handler._processorMap.keys()))  # noqa: SLF001

    ws_client = WSClient(
        app_id=FEISHU_APP_ID,
        app_secret=FEISHU_APP_SECRET,
        event_handler=handler,
        log_level=lark_lvl,
    )

    # 优雅退出
    def _shutdown(signum: int, frame: Any) -> None:
        logger.info("Received signal %d, shutting down...", signum)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("Feishu bot running (WebSocket long connection)")
    ws_client.start()


if __name__ == "__main__":
    main()
