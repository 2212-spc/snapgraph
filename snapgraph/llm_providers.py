from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict

from .llm import LLMProvider, MockLLM


@dataclass(frozen=True)
class ProviderMetadata:
    configured_provider: str
    provider_used: str
    model_used: str
    api_key_env: str
    has_api_key: bool
    provider_ready: bool
    fallback_used: bool = False
    provider_error: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _resolve_llm(workspace) -> LLMProvider:
    from .config import load_config

    config = load_config(workspace)
    provider_name = config.llm.provider if hasattr(config, "llm") else "mock"

    if provider_name == "mock" or not provider_name:
        return MockLLM()

    if provider_name == "anthropic":
        return _create_anthropic(config.llm)

    if provider_name == "deepseek":
        return _create_deepseek(config.llm)

    if provider_name == "qwen":
        return _create_qwen(config.llm)

    return MockLLM()


def provider_metadata(
    workspace,
    *,
    provider_used: str | None = None,
    fallback_used: bool = False,
    provider_error: str = "",
) -> ProviderMetadata:
    from .config import load_config

    config = load_config(workspace)
    configured_provider = config.llm.provider or "mock"
    api_key_env = config.llm.api_key_env or "SNAPGRAPH_LLM_API_KEY"
    model = config.llm.model or _default_model_for_provider(configured_provider)
    has_api_key = bool(os.environ.get(api_key_env, ""))
    provider_ready = configured_provider == "mock" or has_api_key
    if provider_error:
        provider_ready = False
    return ProviderMetadata(
        configured_provider=configured_provider,
        provider_used=provider_used or configured_provider,
        model_used=model,
        api_key_env=api_key_env,
        has_api_key=has_api_key,
        provider_ready=provider_ready,
        fallback_used=fallback_used,
        provider_error=provider_error,
    )


def resolve_llm_with_metadata(workspace) -> tuple[LLMProvider, ProviderMetadata]:
    llm = _resolve_llm(workspace)
    metadata = provider_metadata(
        workspace,
        provider_used=getattr(llm, "provider_name", None) or _configured_provider(workspace),
    )
    model = getattr(llm, "model", None)
    if model:
        metadata = ProviderMetadata(
            configured_provider=metadata.configured_provider,
            provider_used=metadata.provider_used,
            model_used=model,
            api_key_env=metadata.api_key_env,
            has_api_key=metadata.has_api_key,
            provider_ready=metadata.provider_ready,
            fallback_used=metadata.fallback_used,
            provider_error=metadata.provider_error,
        )
    return llm, metadata


def _configured_provider(workspace) -> str:
    from .config import load_config

    return load_config(workspace).llm.provider or "mock"


def _default_model_for_provider(provider: str) -> str:
    if provider == "deepseek":
        return DeepSeekProvider.DEFAULT_MODEL
    if provider == "qwen":
        return QwenProvider.DEFAULT_MODEL
    if provider == "anthropic":
        return AnthropicProvider.DEFAULT_MODEL
    return "mock"


def _create_anthropic(llm_config) -> LLMProvider:
    api_key = os.environ.get(llm_config.api_key_env or "SNAPGRAPH_LLM_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            f"Anthropic provider requires API key. "
            f"Set environment variable {llm_config.api_key_env or 'SNAPGRAPH_LLM_API_KEY'}."
        )
    return AnthropicProvider(
        model=llm_config.model or AnthropicProvider.DEFAULT_MODEL,
        api_key=api_key,
    )


def _create_deepseek(llm_config) -> LLMProvider:
    api_key = os.environ.get(llm_config.api_key_env or "SNAPGRAPH_LLM_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            f"DeepSeek provider requires API key. "
            f"Set environment variable {llm_config.api_key_env or 'SNAPGRAPH_LLM_API_KEY'}."
        )
    return DeepSeekProvider(
        model=llm_config.model or DeepSeekProvider.DEFAULT_MODEL,
        api_key=api_key,
    )


def _create_qwen(llm_config) -> LLMProvider:
    api_key = os.environ.get(llm_config.api_key_env or "SNAPGRAPH_LLM_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            f"Qwen provider requires API key. "
            f"Set environment variable {llm_config.api_key_env or 'SNAPGRAPH_LLM_API_KEY'}."
        )
    return QwenProvider(
        model=llm_config.model or QwenProvider.DEFAULT_MODEL,
        api_key=api_key,
    )


class AnthropicProvider:
    provider_name = "anthropic"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.environ.get("SNAPGRAPH_LLM_API_KEY", "")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def _call(self, prompt: str, system: str = "") -> str:
        kwargs = dict(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system
        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def summarize(self, text: str) -> str:
        if not text.strip():
            return "空内容。"
        return self._call(
            prompt=(
                "请用 1-2 句话总结下面这份文档。"
                "重点说明它是什么，以及它为什么可能重要。"
                "只返回总结，不要前言。\n\n"
                f"文档：\n{text}"
            ),
            system=_SUMMARIZE_SYSTEM,
        )

    def memory_title(self, text: str, why: str | None = None) -> str:
        """Generate a concise receipt title from capture content and save reason."""
        content = text.strip()[:4000]
        reason = (why or "").strip()[:800]
        if not content and not reason:
            return "新的材料"
        return self._call(
            prompt=(
                "请给这次保存生成一个“保存为”标题。\n"
                "要求：\n"
                "- 根据材料内容和用户写下的保存理由综合概括。\n"
                "- 不要只照抄材料第一句话。\n"
                "- 15-28 个汉字左右，像知识库里的记忆标签。\n"
                "- 只输出标题，不要引号、编号或解释。\n\n"
                f"用户写下的保存理由：\n{reason or '无'}\n\n"
                f"材料内容：\n{content or '无'}"
            ),
            system=(
                "你在为个人认知知识库生成可回看的记忆标题。"
                "标题应凝练、具体、忠于证据，不要夸大或编造。"
            ),
        )

    def key_details(self, text: str) -> list[str]:
        if not text.strip():
            return ["未提取到关键细节。"]
        response = self._call(
            prompt=(
                "请从下面文档中提取 1-3 条关键细节或事实。"
                "每条单独占一行。只返回内容本身，不要编号或项目符号。\n\n"
                f"文档：\n{text}"
            ),
        )
        details = [line.strip().lstrip("-").strip() for line in response.splitlines() if line.strip()]
        return details[:3] if details else ["未提取到关键细节。"]

    def infer_why_saved(self, title: str, text: str) -> str:
        if not text.strip():
            return "AI-inferred: 内容为空，无法推断保存原因。"
        summary = self.summarize(text)
        response = self._call(
            prompt=(
                f"材料标题：'{title}'\n"
                f"材料摘要：{summary}\n\n"
                "基于以上内容，简要推断一个人为什么可能保存这份材料。"
                "它可能关联到什么问题、项目或决策？"
                "要诚实表达不确定性。只返回一句话假设。"
            ),
            system=(
                "你在帮助用户恢复过去的思考过程。"
                "你的推断必须明确标记为 AI-inferred，而不是 user-stated。"
                "不要声称自己确定知道用户当时的动机。"
            ),
        )
        return f"AI-inferred: {response.strip()}"

    def open_loops(self, text: str) -> list[str]:
        if not text.strip():
            return ["之后再决定如何使用这份材料。"]
        response = self._call(
            prompt=(
                "请识别下面文本中提到的 open loop、TODO、未解决问题或下一步行动。"
                "每项单独占一行。"
                "如果没有找到，就返回“之后再决定如何使用这份材料。”\n\n"
                f"文本：\n{text}"
            ),
        )
        loops = [line.strip() for line in response.splitlines() if line.strip()]
        return loops[:3] if loops else ["之后再决定如何使用这份材料。"]

    def future_recall_questions(self, title: str, text: str) -> list[str]:
        response = self._call(
            prompt=(
                f"材料标题：'{title}'\n\n"
                f"文本：\n{text}\n\n"
                "请生成 2-3 个未来回忆时可能会问的问题，帮助理解："
                "这份材料为什么重要、它支持了什么决策、以及它和其他工作如何关联。"
                "每行一个问题，不要编号或项目符号。"
            ),
        )
        questions = [line.strip() for line in response.splitlines() if line.strip()]
        if not questions:
            return [
                f"保存“{title}”时，它为什么重要？",
                f"“{title}”和我当前的项目或问题有什么关系？",
            ]
        return questions[:3]

    def related_project(self, text: str) -> str | None:
        if not text.strip():
            return None
        response = self._call(
            prompt=(
                "请识别这段文本最可能关联的项目或主题领域。"
                "返回一个简短标签（2-5 个词）即可；如果不清楚，就返回“None”。\n\n"
                f"文本：\n{text}"
            ),
        )
        label = response.strip().strip('"')
        if not label or label.lower() == "none":
            return None
        return label

    def describe_image(self, image_path: Path) -> str:
        import anthropic

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        media_type = _mime_type(image_path.suffix)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "请详细描述这张图片里可见的内容。"
                                "包括文字、UI 元素、图表、手写内容或其他明显视觉特征。"
                                "只返回描述本身。"
                            ),
                        },
                    ],
                }
            ],
        )
        return response.content[0].text

    def synthesize_answer(
        self,
        question: str,
        contexts: list[dict],
        graph_paths: list[str],
    ) -> str:
        if not contexts:
            return self._call(
                prompt=(
                    f"问题：{question}\n\n"
                    "知识库中没有找到匹配的材料或图谱路径。"
                ),
                system=_SYNTHESIZE_SYSTEM,
            )

        context_text = _format_contexts_for_prompt(contexts)
        paths_text = "\n".join(graph_paths) if graph_paths else "未找到图谱路径。"
        return self._call(
            prompt=(
                f"问题：{question}\n\n"
                f"从知识库中检索到的上下文：\n{context_text}\n\n"
                f"连接这些上下文的图谱路径：\n{paths_text}\n\n"
                "请按照系统说明里的输出结构生成回答。"
            ),
            system=_SYNTHESIZE_SYSTEM,
        )


class DeepSeekProvider:
    provider_name = "deepseek"
    DEFAULT_MODEL = "deepseek-chat"

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.environ.get("SNAPGRAPH_LLM_API_KEY", "")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            import httpx

            http_client = httpx.Client(proxy=None)
            self._client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com",
                http_client=http_client,
            )
        return self._client

    def _call(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    def summarize(self, text: str) -> str:
        if not text.strip():
            return "空内容。"
        return self._call(
            prompt=(
                "请用 1-2 句话总结下面这份文档。"
                "重点说明它是什么，以及它为什么可能重要。"
                "只返回总结，不要前言。\n\n"
                f"文档：\n{text}"
            ),
            system=_SUMMARIZE_SYSTEM,
        )

    def memory_title(self, text: str, why: str | None = None) -> str:
        """Generate a concise receipt title from capture content and save reason."""
        content = text.strip()[:4000]
        reason = (why or "").strip()[:800]
        if not content and not reason:
            return "新的材料"
        return self._call(
            prompt=(
                "请给这次保存生成一个“保存为”标题。\n"
                "要求：\n"
                "- 根据材料内容和用户写下的保存理由综合概括。\n"
                "- 不要只照抄材料第一句话。\n"
                "- 15-28 个汉字左右，像知识库里的记忆标签。\n"
                "- 只输出标题，不要引号、编号或解释。\n\n"
                f"用户写下的保存理由：\n{reason or '无'}\n\n"
                f"材料内容：\n{content or '无'}"
            ),
            system=(
                "你在为个人认知知识库生成可回看的记忆标题。"
                "标题应凝练、具体、忠于证据，不要夸大或编造。"
            ),
        )

    def key_details(self, text: str) -> list[str]:
        if not text.strip():
            return ["未提取到关键细节。"]
        response = self._call(
            prompt=(
                "请从下面文档中提取 1-3 条关键细节或事实。"
                "每条单独占一行。只返回内容本身，不要编号或项目符号。\n\n"
                f"文档：\n{text}"
            ),
        )
        details = [line.strip().lstrip("-").strip() for line in response.splitlines() if line.strip()]
        return details[:3] if details else ["未提取到关键细节。"]

    def infer_why_saved(self, title: str, text: str) -> str:
        if not text.strip():
            return "AI-inferred: 内容为空，无法推断保存原因。"
        summary = self.summarize(text)
        response = self._call(
            prompt=(
                f"材料标题：'{title}'\n"
                f"材料摘要：{summary}\n\n"
                "基于以上内容，简要推断一个人为什么可能保存这份材料。"
                "它可能关联到什么问题、项目或决策？"
                "要诚实表达不确定性。只返回一句话假设。"
            ),
            system=(
                "你在帮助用户恢复过去的思考过程。"
                "你的推断必须明确标记为 AI-inferred，而不是 user-stated。"
                "不要声称自己确定知道用户当时的动机。"
            ),
        )
        return f"AI-inferred: {response.strip()}"

    def open_loops(self, text: str) -> list[str]:
        if not text.strip():
            return ["之后再决定如何使用这份材料。"]
        response = self._call(
            prompt=(
                "请识别下面文本中提到的 open loop、TODO、未解决问题或下一步行动。"
                "每项单独占一行。"
                "如果没有找到，就返回“之后再决定如何使用这份材料。”\n\n"
                f"文本：\n{text}"
            ),
        )
        loops = [line.strip() for line in response.splitlines() if line.strip()]
        return loops[:3] if loops else ["之后再决定如何使用这份材料。"]

    def future_recall_questions(self, title: str, text: str) -> list[str]:
        response = self._call(
            prompt=(
                f"材料标题：'{title}'\n\n"
                f"文本：\n{text}\n\n"
                "请生成 2-3 个未来回忆时可能会问的问题，帮助理解："
                "这份材料为什么重要、它支持了什么决策、以及它和其他工作如何关联。"
                "每行一个问题，不要编号或项目符号。"
            ),
        )
        questions = [line.strip() for line in response.splitlines() if line.strip()]
        if not questions:
            return [
                f"保存“{title}”时，它为什么重要？",
                f"“{title}”和我当前的项目或问题有什么关系？",
            ]
        return questions[:3]

    def related_project(self, text: str) -> str | None:
        if not text.strip():
            return None
        response = self._call(
            prompt=(
                "请识别这段文本最可能关联的项目或主题领域。"
                "返回一个简短标签（2-5 个词）即可；如果不清楚，就返回“None”。\n\n"
                f"文本：\n{text}"
            ),
        )
        label = response.strip().strip('"')
        if not label or label.lower() == "none":
            return None
        return label

    def describe_image(self, image_path: Path) -> str:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        media_type = _mime_type(image_path.suffix)
        data_url = f"data:{media_type};base64,{image_data}"
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {
                            "type": "text",
                            "text": (
                                "请详细描述这张图片里可见的内容。"
                                "包括文字、UI 元素、图表、手写内容或其他明显视觉特征。"
                                "只返回描述本身。"
                            ),
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content or ""

    def synthesize_answer(
        self,
        question: str,
        contexts: list[dict],
        graph_paths: list[str],
    ) -> str:
        if not contexts:
            return self._call(
                prompt=(
                    f"问题：{question}\n\n"
                    "知识库中没有找到匹配的材料或图谱路径。"
                ),
                system=_SYNTHESIZE_SYSTEM,
            )

        context_text = _format_contexts_for_prompt(contexts)
        paths_text = "\n".join(graph_paths) if graph_paths else "未找到图谱路径。"
        return self._call(
            prompt=(
                f"问题：{question}\n\n"
                f"从知识库中检索到的上下文：\n{context_text}\n\n"
                f"连接这些上下文的图谱路径：\n{paths_text}\n\n"
                "请按照系统说明里的输出结构生成回答。"
            ),
            system=_SYNTHESIZE_SYSTEM,
        )

    def stream_recall_reply(
        self,
        question: str,
        contexts: list[dict],
        graph_paths: list[str],
    ):
        context_text = _format_contexts_for_prompt(contexts)
        paths_text = "\n".join(graph_paths[:4]) if graph_paths else "未找到图谱路径。"
        messages = [
            {"role": "system", "content": _RECALL_REPLY_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"用户问题：{question}\n\n"
                    f"可用上下文：\n{context_text}\n\n"
                    f"图谱连接：\n{paths_text}\n\n"
                    "请只写给用户看的 AI 回复正文。"
                ),
            },
        ]
        stream = self.client.chat.completions.create(
            model=self.model,
            max_tokens=700,
            messages=messages,
            stream=True,
        )
        for event in stream:
            chunk = event.choices[0].delta.content or ""
            if chunk:
                yield chunk


class QwenProvider(DeepSeekProvider):
    provider_name = "qwen"
    DEFAULT_MODEL = "qwen3-vl-plus"
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            import httpx

            http_client = httpx.Client(proxy=None)
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=os.environ.get("SNAPGRAPH_QWEN_BASE_URL", self.DEFAULT_BASE_URL),
                http_client=http_client,
            )
        return self._client


_SUMMARIZE_SYSTEM = (
    "你在为一个个人认知知识库总结文档。"
    "请保持简洁、客观，不要编造细节。"
)

_SYNTHESIZE_SYSTEM = """你在为一个名为 SnapGraph 的认知知识库回答问题。
你的回答必须使用中文，并严格遵循下面结构：

## 找回的原话
优先列出 user-stated 原话；没有用户原话时，明确说明只能看到 AI-inferred 线索。

## 相关材料
列出直接相关材料，并标明 user-stated / AI-inferred。

## 连接路径
说明这些材料在知识图谱中如何连接；如果没有路径，也要明确写出来。

## AI 探索回应
基于材料、保存理由和连接路径，给出一段真正接住用户问题的探索性回答。
这一段可以做有用的泛化、类比和判断推进，但必须清楚依赖哪些证据，不能伪装成用户当时的原话。
如果证据不足，要明确说明不确定性，并把回应写成探索假设。
这一段是用户最先看到的 AI 回复，必须像人一样直接回答用户问的“为什么 / 怎么办 / 这说明什么”。
不要列材料数量、source_id、文件名清单或检索诊断；这些只能放在其他 section。
用 2-4 个短段落回答，每段不超过 3 句。
先给判断，再说明依据边界；不要只说“找到了几条线索”。

## 涌现洞见
只基于检索证据说明这些材料串起来之后，当前最值得注意的新判断是什么。

## 下一步
从检索出的上下文中给出最可执行的 open loop 或下一步行动。

规则：
- 必须始终区分 user-stated 和 AI-inferred 上下文。
- 如果所有上下文都是低置信度的 AI-inferred，要明确说明。
- 不要假装确定知道用户当时的意图或记忆。
- 要引用具体材料作为证据。
- 如果置信度低，仍可提供已有信息，但必须明确标出不确定性。
- 不要使用 emoji、横线分隔符或“这是个好问题”一类寒暄。
- 优先恢复当时留下的原话，再解释它和当前问题的关系。
- AI 探索回应要像一个认真读过用户图谱的思考伙伴，不要只复述材料列表。
- 不要把英文 source id、文件路径、材料编号写进 AI 探索回应，除非用户明确询问这些。"""


_RECALL_REPLY_SYSTEM = """你是 SnapGraph 的 AI 回复层。用户不是要看检索报告，而是要你接住问题。

请只输出给用户看的正文，不要写 markdown 标题，不要列 source id、材料编号、文件路径或检索诊断。

回答原则：
- 先直接回答用户的问题，不寒暄。
- 用 2-4 个短段落，每段不超过 3 句。
- 可以做泛化、类比、判断推进，但必须基于给定上下文。
- 区分用户原话和你的推断；不要把推断伪装成过去的记忆。
- 如果证据不足，就明确说“不确定”，但仍给出一个可验证的探索假设。
- 语气像认真读过用户图谱的思考伙伴，不像客服、报告或搜索摘要。"""


def _format_contexts_for_prompt(contexts: list[dict]) -> str:
    parts = []
    for i, context in enumerate(contexts, start=1):
        parts.append(
            f"材料 {i}: '{context.get('title', '')}'\n"
            f"  空间: {context.get('space_name') or context.get('graph_space_id') or '默认空间'}\n"
            f"  保存原因: {context.get('why_saved', '')}\n"
            f"  状态: {context.get('why_saved_status', '')}\n"
            f"  相关项目: {context.get('related_project') or 'None'}\n"
            f"  材料摘录: {context.get('source_excerpt') or 'None'}\n"
            f"  Open loops: {', '.join(context.get('open_loops', []))}\n"
            f"  未来回忆问题: {'; '.join(context.get('future_recall_questions', []))}"
        )
    return "\n\n".join(parts)


def _mime_type(suffix: str) -> str:
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return mapping.get(suffix.lower(), "image/png")
