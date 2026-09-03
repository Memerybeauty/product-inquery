"""配置（LLM + system_prompt）"""
import json
import os
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
LLM_CONFIG_PATH = CONFIG_DIR / "agent_llm_config.json"


def load_llm_config() -> dict:
    """加载 LLM 配置"""
    with open(LLM_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prompt(name: str) -> str:
    """加载 system_prompt 片段（base / path_question / path_file / path_other）"""
    path = CONFIG_DIR / "prompts" / f"{name}.md"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


__all__ = ["load_llm_config", "load_prompt", "LLM_CONFIG_PATH", "CONFIG_DIR"]
