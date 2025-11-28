# documents/services/confluence_publish.py
import html
import logging
from typing import List

from cases.models import Case, CaseStatus
from documents.models import GeneratedDocument, DocumentStatus
from integrations.confluence_client import ConfluenceClient

logger = logging.getLogger(__name__)


def _build_html_for_case(case: Case, docs: List[GeneratedDocument]) -> str:
    parts: List[str] = []
    parts.append(f"<h1>{html.escape(case.title)}</h1>")
    parts.append("<p>Сгенерированные и одобренные документы Talap AI.</p>")

    for doc in docs:
        parts.append(f"<h2>{html.escape(doc.title)}</h2>")
        # doc.content у нас в Markdown → для простоты заворачиваем в <pre>
        parts.append("<pre>")
        parts.append(html.escape(doc.content or ""))
        parts.append("</pre>")

    return "".join(parts)


def publish_case_to_confluence(case: Case) -> None:
    """
    Создаёт страницу в Confluence, если:
    - указан confluence_space_key,
    - есть хотя бы один документ со статусом APPROVED_BY_BA,
    - страница ещё не создавалась.
    """
    if not case.confluence_space_key:
        logger.info("Case %s has no confluence_space_key, skip publish", case.id)
        return

    if case.confluence_page_id:
        logger.info("Case %s already has confluence_page_id=%s, skip",
                    case.id, case.confluence_page_id)
        return

    docs = list(
        GeneratedDocument.objects.filter(
            case=case,
            status=DocumentStatus.APPROVED_BY_BA,
        ).order_by("doc_type")
    )
    if not docs:
        logger.info("Case %s has no approved documents yet, skip publish", case.id)
        return

    html_body = _build_html_for_case(case, docs)
    client = ConfluenceClient()
    page_id, page_url = client.create_page(
        space_key=case.confluence_space_key,
        title=case.title,
        html_body=html_body,
    )

    case.confluence_page_id = page_id
    case.confluence_page_url = page_url
    case.status = CaseStatus.APPROVED
    case.save(update_fields=["confluence_page_id", "confluence_page_url", "status"])

    logger.info("Case %s published to Confluence page %s", case.id, page_url)
