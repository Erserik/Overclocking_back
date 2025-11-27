import logging
import zlib
from typing import Optional

from django.conf import settings

from documents.models import GeneratedDocument, DocumentType

logger = logging.getLogger(__name__)

DEFAULT_PLANTUML_SERVER = "https://www.plantuml.com/plantuml"


# ====== кодирование PlantUML в short URL ======

_PU_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"


def _encode_6bit(b: int) -> str:
    return _PU_ALPHABET[b & 0x3F]


def _append_3bytes(b1: int, b2: int, b3: int) -> str:
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F
    return (
        _encode_6bit(c1 & 0x3F)
        + _encode_6bit(c2 & 0x3F)
        + _encode_6bit(c3 & 0x3F)
        + _encode_6bit(c4 & 0x3F)
    )


def encode_plantuml(text: str) -> str:
    """
    Deflate (wbits=-15) + спец. base64 от PlantUML.
    """
    data = text.encode("utf-8")
    compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed = compressor.compress(data) + compressor.flush()

    res = []
    i = 0
    length = len(compressed)
    while i < length:
        b1 = compressed[i]
        b2 = compressed[i + 1] if i + 1 < length else 0
        b3 = compressed[i + 2] if i + 2 < length else 0
        res.append(_append_3bytes(b1, b2, b3))
        i += 3
    return "".join(res)


def build_plantuml_url(uml_code: str) -> str:
    """
    Строим прямую ссылку на PNG на PlantUML-сервере.
    """
    server = getattr(settings, "PLANTUML_SERVER_URL", DEFAULT_PLANTUML_SERVER)
    encoded = encode_plantuml(uml_code)
    return server.rstrip("/") + "/png/" + encoded


# ====== fallback PlantUML, если GPT ничего не вернул ======


def _build_fallback_plantuml(doc: GeneratedDocument) -> str:
    case = getattr(doc, "case", None)
    title = (getattr(case, "title", None) or doc.title or "New Case").strip()

    return f"""@startuml
title BPMN: {title}

start
:Клиент заполняет кейс в форме;
:AI-агент собирает 8 базовых ответов;
:AI-агент задаёт уточняющие вопросы;
:Генерация документов (Vision, Scope, BPMN);
if (BA одобрил документы?) then (yes)
  :Документы уходят в Confluence / Jira;
else (no)
  :BA запрашивает доработку;
endif
stop

@enduml
"""


# ====== основная функция: сохранить только URL ======


def ensure_bpmn_url_for_document(doc: GeneratedDocument, force: bool = False) -> GeneratedDocument:
    if doc.doc_type != DocumentType.BPMN:
        return doc

    if doc.diagram_url and not force:
        return doc

    structured = doc.structured_data or {}

    # ✅ поддерживаем оба варианта: plantuml ИЛИ plantuml_code
    plantuml_code = (
        structured.get("plantuml")          # то, что сейчас реально приходит
        or structured.get("plantuml_code")  # на будущее, если схему поменяем
        or doc.content
    )

    if not plantuml_code:
        logger.warning(
            "No PlantUML code in structured_data/content for BPMN doc=%s, using fallback",
            doc.id,
        )
        plantuml_code = _build_fallback_plantuml(doc)

    logger.info("PlantUML for BPMN doc %s:\n%s", doc.id, plantuml_code)

    url = build_plantuml_url(plantuml_code)
    doc.diagram_url = url
    doc.save(update_fields=["diagram_url", "updated_at"])
    return doc