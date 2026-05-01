from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


DEFAULT_ALIASES = {
    "截图": ["screenshot", "screenshots", "screenshot ingestion"],
    "入口": ["entry"],
    "核心": ["core"],
    "端侧": ["on-device", "on device", "local"],
    "方法论": ["methodology"],
    "开题": ["thesis", "proposal"],
}


@dataclass(frozen=True)
class RetrievalConfig:
    aliases: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_ALIASES))
    title_weight: float = 3.0
    keyword_weight: float = 1.0
    graph_node_weight: float = 2.0
    graph_edge_weight: float = 1.0
    max_expanded_nodes: int = 40
    max_source_pages: int = 8


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "mock"
    model: str = ""
    api_key_env: str = "SNAPGRAPH_LLM_API_KEY"


@dataclass(frozen=True)
class SnapGraphConfig:
    workspace_version: int = 1
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


def default_config_dict() -> dict:
    return {
        "workspace_version": 1,
        "llm": {
            "provider": "mock",
            "model": "",
            "api_key_env": "SNAPGRAPH_LLM_API_KEY",
        },
        "retrieval": {
            "aliases": DEFAULT_ALIASES,
            "title_weight": 3.0,
            "keyword_weight": 1.0,
            "graph_node_weight": 2.0,
            "graph_edge_weight": 1.0,
            "max_expanded_nodes": 40,
            "max_source_pages": 8,
        },
    }


def render_default_config() -> str:
    return json.dumps(default_config_dict(), ensure_ascii=False, indent=2) + "\n"


def load_config(workspace) -> SnapGraphConfig:
    if not workspace.config_path.exists():
        return SnapGraphConfig()

    raw_text = workspace.config_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return SnapGraphConfig()

    try:
        raw_config = json.loads(raw_text)
    except json.JSONDecodeError:
        return SnapGraphConfig()

    llm_config = raw_config.get("llm", {})
    retrieval_config = raw_config.get("retrieval", {})
    aliases = retrieval_config.get("aliases", DEFAULT_ALIASES)
    return SnapGraphConfig(
        workspace_version=int(raw_config.get("workspace_version", 1)),
        llm=LLMConfig(
            provider=str(llm_config.get("provider", "mock")),
            model=str(llm_config.get("model", "")),
            api_key_env=str(llm_config.get("api_key_env", "SNAPGRAPH_LLM_API_KEY")),
        ),
        retrieval=RetrievalConfig(
            aliases=_normalize_aliases(aliases),
            title_weight=float(retrieval_config.get("title_weight", 3.0)),
            keyword_weight=float(retrieval_config.get("keyword_weight", 1.0)),
            graph_node_weight=float(retrieval_config.get("graph_node_weight", 2.0)),
            graph_edge_weight=float(retrieval_config.get("graph_edge_weight", 1.0)),
            max_expanded_nodes=int(retrieval_config.get("max_expanded_nodes", 40)),
            max_source_pages=int(retrieval_config.get("max_source_pages", 8)),
        ),
    )


def save_config(workspace, config: SnapGraphConfig) -> None:
    config_dict = {
        "workspace_version": config.workspace_version,
        "llm": {
            "provider": config.llm.provider,
            "model": config.llm.model,
            "api_key_env": config.llm.api_key_env,
        },
        "retrieval": {
            "aliases": config.retrieval.aliases,
            "title_weight": config.retrieval.title_weight,
            "keyword_weight": config.retrieval.keyword_weight,
            "graph_node_weight": config.retrieval.graph_node_weight,
            "graph_edge_weight": config.retrieval.graph_edge_weight,
            "max_expanded_nodes": config.retrieval.max_expanded_nodes,
            "max_source_pages": config.retrieval.max_source_pages,
        },
    }
    workspace.config_path.write_text(
        json.dumps(config_dict, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def validate_api_key_env_name(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError("api_key_env cannot be empty")
    if cleaned.startswith(("sk-", "sk_", "sk-proj-", "sk-ant-")):
        raise ValueError("api_key_env must be an environment variable name, not an API key")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", cleaned):
        raise ValueError("api_key_env must be a valid environment variable name")
    return cleaned


def _normalize_aliases(raw_aliases: dict) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for key, value in raw_aliases.items():
        if isinstance(value, list):
            aliases[str(key)] = [str(item) for item in value]
        else:
            aliases[str(key)] = [str(value)]
    return aliases
