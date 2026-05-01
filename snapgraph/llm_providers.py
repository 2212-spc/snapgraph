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
            return "Empty source."
        return self._call(
            prompt=(
                "Summarize the following document in 1-2 sentences. "
                "Focus on what it is about and why it might matter. "
                "Return only the summary, no preamble.\n\n"
                f"Document:\n{text}"
            ),
            system=_SUMMARIZE_SYSTEM,
        )

    def key_details(self, text: str) -> list[str]:
        if not text.strip():
            return ["No key details found."]
        response = self._call(
            prompt=(
                "Extract 1-3 key details or facts from the following document. "
                "Each detail should be one line. Return only the details, one per line, no numbers or bullets.\n\n"
                f"Document:\n{text}"
            ),
        )
        details = [line.strip().lstrip("-").strip() for line in response.splitlines() if line.strip()]
        return details[:3] if details else ["No key details found."]

    def infer_why_saved(self, title: str, text: str) -> str:
        if not text.strip():
            return "AI-inferred: empty source, no reason could be inferred."
        summary = self.summarize(text)
        response = self._call(
            prompt=(
                f"Source title: '{title}'\n"
                f"Source summary: {summary}\n\n"
                "Based on the above, briefly infer why someone might have saved this source. "
                "What question, project, or decision might it relate to? "
                "Be honest about uncertainty. Return a single sentence hypothesis."
            ),
            system=(
                "You are helping someone recover their past thinking. "
                "Your inferences must be clearly labeled as AI-inferred, not user-stated. "
                "Never claim certainty about the user's motivations."
            ),
        )
        return f"AI-inferred: {response.strip()}"

    def open_loops(self, text: str) -> list[str]:
        if not text.strip():
            return ["Decide how to use this source later."]
        response = self._call(
            prompt=(
                "Identify any open loops, TODOs, unresolved questions, or next actions mentioned "
                "in the following text. Return each as one line. If none are found, return "
                "'Decide how to use this source later.'\n\n"
                f"Text:\n{text}"
            ),
        )
        loops = [line.strip() for line in response.splitlines() if line.strip()]
        return loops[:3] if loops else ["Decide how to use this source later."]

    def future_recall_questions(self, title: str, text: str) -> list[str]:
        response = self._call(
            prompt=(
                f"Source title: '{title}'\n\n"
                f"Text:\n{text}\n\n"
                "Generate 2-3 questions someone might ask in the future when trying to recall "
                "why this source mattered, what decision it supported, or how it connects "
                "to other work. Return one question per line, no numbers or bullets."
            ),
        )
        questions = [line.strip() for line in response.splitlines() if line.strip()]
        if not questions:
            return [
                f"Why did '{title}' matter when it was saved?",
                f"How does '{title}' connect to my current project or question?",
            ]
        return questions[:3]

    def related_project(self, text: str) -> str | None:
        if not text.strip():
            return None
        response = self._call(
            prompt=(
                "Identify the most likely project or topic area this text relates to. "
                "Return a single short label (2-5 words) or 'None' if unclear.\n\n"
                f"Text:\n{text}"
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
                                "Describe what is visible in this image in detail. "
                                "Include any text, UI elements, diagrams, charts, "
                                "handwriting, or notable visual features. "
                                "Return only the description."
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
                    f"Question: {question}\n\n"
                    "No matching sources or graph paths were found in the knowledge base."
                ),
                system=_SYNTHESIZE_SYSTEM,
            )

        context_text = _format_contexts_for_prompt(contexts)
        paths_text = "\n".join(graph_paths) if graph_paths else "No graph paths found."
        return self._call(
            prompt=(
                f"Question: {question}\n\n"
                f"Retrieved contexts from the knowledge base:\n{context_text}\n\n"
                f"Graph paths connecting contexts:\n{paths_text}\n\n"
                "Synthesize an answer following the output structure described in "
                "the system instructions."
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
            return "Empty source."
        return self._call(
            prompt=(
                "Summarize the following document in 1-2 sentences. "
                "Focus on what it is about and why it might matter. "
                "Return only the summary, no preamble.\n\n"
                f"Document:\n{text}"
            ),
            system=_SUMMARIZE_SYSTEM,
        )

    def key_details(self, text: str) -> list[str]:
        if not text.strip():
            return ["No key details found."]
        response = self._call(
            prompt=(
                "Extract 1-3 key details or facts from the following document. "
                "Each detail should be one line. Return only the details, one per line, no numbers or bullets.\n\n"
                f"Document:\n{text}"
            ),
        )
        details = [line.strip().lstrip("-").strip() for line in response.splitlines() if line.strip()]
        return details[:3] if details else ["No key details found."]

    def infer_why_saved(self, title: str, text: str) -> str:
        if not text.strip():
            return "AI-inferred: empty source, no reason could be inferred."
        summary = self.summarize(text)
        response = self._call(
            prompt=(
                f"Source title: '{title}'\n"
                f"Source summary: {summary}\n\n"
                "Based on the above, briefly infer why someone might have saved this source. "
                "What question, project, or decision might it relate to? "
                "Be honest about uncertainty. Return a single sentence hypothesis."
            ),
            system=(
                "You are helping someone recover their past thinking. "
                "Your inferences must be clearly labeled as AI-inferred, not user-stated. "
                "Never claim certainty about the user's motivations."
            ),
        )
        return f"AI-inferred: {response.strip()}"

    def open_loops(self, text: str) -> list[str]:
        if not text.strip():
            return ["Decide how to use this source later."]
        response = self._call(
            prompt=(
                "Identify any open loops, TODOs, unresolved questions, or next actions mentioned "
                "in the following text. Return each as one line. If none are found, return "
                "'Decide how to use this source later.'\n\n"
                f"Text:\n{text}"
            ),
        )
        loops = [line.strip() for line in response.splitlines() if line.strip()]
        return loops[:3] if loops else ["Decide how to use this source later."]

    def future_recall_questions(self, title: str, text: str) -> list[str]:
        response = self._call(
            prompt=(
                f"Source title: '{title}'\n\n"
                f"Text:\n{text}\n\n"
                "Generate 2-3 questions someone might ask in the future when trying to recall "
                "why this source mattered, what decision it supported, or how it connects "
                "to other work. Return one question per line, no numbers or bullets."
            ),
        )
        questions = [line.strip() for line in response.splitlines() if line.strip()]
        if not questions:
            return [
                f"Why did '{title}' matter when it was saved?",
                f"How does '{title}' connect to my current project or question?",
            ]
        return questions[:3]

    def related_project(self, text: str) -> str | None:
        if not text.strip():
            return None
        response = self._call(
            prompt=(
                "Identify the most likely project or topic area this text relates to. "
                "Return a single short label (2-5 words) or 'None' if unclear.\n\n"
                f"Text:\n{text}"
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
                                "Describe what is visible in this image in detail. "
                                "Include any text, UI elements, diagrams, charts, "
                                "handwriting, or notable visual features. "
                                "Return only the description."
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
                    f"Question: {question}\n\n"
                    "No matching sources or graph paths were found in the knowledge base."
                ),
                system=_SYNTHESIZE_SYSTEM,
            )

        context_text = _format_contexts_for_prompt(contexts)
        paths_text = "\n".join(graph_paths) if graph_paths else "No graph paths found."
        return self._call(
            prompt=(
                f"Question: {question}\n\n"
                f"Retrieved contexts from the knowledge base:\n{context_text}\n\n"
                f"Graph paths connecting contexts:\n{paths_text}\n\n"
                "Synthesize an answer following the output structure described in "
                "the system instructions."
            ),
            system=_SYNTHESIZE_SYSTEM,
        )


_SUMMARIZE_SYSTEM = (
    "You summarize documents for a personal cognitive knowledge base. "
    "Be concise and factual. Do not fabricate details."
)

_SYNTHESIZE_SYSTEM = """You answer questions for a cognitive knowledge base called SnapGraph.
Your answers must follow this structure:

## Direct Answer
A direct answer to the question based on retrieved evidence.

## Recovered Cognitive Context
For each source: what it is, why it was saved, and whether that reason is user-stated or AI-inferred. Distinguish clearly between these two.

## Evidence Sources
Numbered list of sources with their status (user-stated/AI-inferred).

## Graph Paths
How the sources are connected in the knowledge graph (if paths exist).

## Suggested Next Action
Most actionable open loop or next step from the retrieved contexts.

Rules:
- ALWAYS distinguish user-stated from AI-inferred contexts.
- If all contexts are AI-inferred with low confidence, say so clearly.
- NEVER fabricate certainty about the user's intent or memory.
- Cite specific sources as evidence.
- If confidence is low, still provide what information is available but flag the uncertainty."""


def _format_contexts_for_prompt(contexts: list[dict]) -> str:
    parts = []
    for i, context in enumerate(contexts, start=1):
        parts.append(
            f"Source {i}: '{context.get('title', '')}'\n"
            f"  Space: {context.get('space_name') or context.get('graph_space_id') or 'Default'}\n"
            f"  Why saved: {context.get('why_saved', '')}\n"
            f"  Status: {context.get('why_saved_status', '')}\n"
            f"  Related project: {context.get('related_project') or 'None'}\n"
            f"  Source excerpt: {context.get('source_excerpt') or 'None'}\n"
            f"  Open loops: {', '.join(context.get('open_loops', []))}\n"
            f"  Future recall questions: {'; '.join(context.get('future_recall_questions', []))}"
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
