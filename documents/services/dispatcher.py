from typing import Any, Dict, Tuple

from documents.models import DocumentType
from .utils import sha256_text

from .artifacts.vision import prompt as vision_prompt
from .artifacts.vision.generator import generate as generate_vision
from .artifacts.vision.renderer import render as render_vision

from .artifacts.scope import prompt as scope_prompt
from .artifacts.scope.generator import generate as generate_scope
from .artifacts.scope.renderer import render as render_scope


def get_artifact_prompt_bundle(doc_type: str) -> Tuple[str, str, str]:
    """
    returns: (prompt_version, system_prompt, user_prompt_template_hash_source)
    """
    if doc_type == DocumentType.VISION:
        return vision_prompt.PROMPT_VERSION, vision_prompt.SYSTEM_PROMPT, "scope"
    if doc_type == DocumentType.SCOPE:
        return scope_prompt.PROMPT_VERSION, scope_prompt.SYSTEM_PROMPT, "vision"
    raise ValueError("Unsupported doc_type")


def compute_prompt_hash(system_prompt: str, user_prompt: str) -> str:
    # хешим фактические строковые промпты (для определения stale)
    return sha256_text(system_prompt + "\n---\n" + user_prompt)


def generate_structured_and_render(doc_type: str, case_context: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str, str]:
    """
    returns: (structured_data, content_md, title, used_model)
    """
    if doc_type == DocumentType.VISION:
        structured, used_model = generate_vision(case_context)
        content = render_vision(structured)
        title = (structured.get("title") or case_context["case"]["title"]).strip() or case_context["case"]["title"]
        return structured, content, title, used_model

    if doc_type == DocumentType.SCOPE:
        structured, used_model = generate_scope(case_context)
        content = render_scope(structured)
        title = f"Scope: {case_context['case']['title']}"
        return structured, content, title, used_model

    raise ValueError("Unsupported doc_type")
