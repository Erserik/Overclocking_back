"""
Простой тест запроса на PlantUML-сервер.

1) Берёт пример PlantUML-кода (activity-диаграмма под наш BPMN-флоу).
2) Кодирует его так же, как делает PlantUML (deflate + спец. base64).
3) Шлёт GET на PLANTUML_SERVER_URL/png/<код>.
4) Сохраняет картинку в plantuml_test.png рядом с файлом.
"""

import os
import zlib
import requests


# ===== 1. Настройки =====

# Можно переопределить через переменную окружения PLANTUML_SERVER_URL
PLANTUML_SERVER_URL = os.getenv(
    "PLANTUML_SERVER_URL",
    "http://www.plantuml.com/plantuml",  # или твой локальный сервер
)

OUTPUT_FILE = "plantuml_test.png"


# ===== 2. Пример PlantUML-кода =====

EXAMPLE_PLANTUML = r"""
@startuml
title BPMN v2: Talap AI — внутренний AI-ассистент Forte Bank

|Клиент|
start
:Заполняет кейс в веб-форме;
:Отправляет ответы;

|AI-агент|
:Принимает кейс;
:Проверяет полноту 8 базовых ответов;

if (Все ответы есть?) then (yes)
  :Строит уточняющие вопросы;
else (no)
  :Просит клиента дозаполнить форму;
  |Клиент|
  :Дополняет недостающие поля;
  |AI-агент|
endif

:Генерирует Vision и Scope;
:Строит BPMN-диаграмму процесса;

|Бизнес-аналитик (BA)|
:Просматривает материалы;

if (BA доволен?) then (yes)
  :Отправляет в Confluence / Jira;
  stop
else (no)
  :Оставляет комментарии и запросы на доработку;
  |AI-агент|
  :Формирует новый раунд уточнений для клиента;
  |Клиент|
  :Отвечает на новые вопросы;
  |AI-агент|
  :Перегенерирует документы;
  |Бизнес-аналитик (BA)|
  :Повторная проверка;
  stop
endif

@enduml

""".strip()


# ===== 3. Кодирование PlantUML =====

def _encode6bit(b: int) -> str:
    if b < 10:
        return chr(48 + b)
    b -= 10
    if b < 26:
        return chr(65 + b)
    b -= 26
    if b < 26:
        return chr(97 + b)
    b -= 26
    if b == 0:
        return "-"
    if b == 1:
        return "_"
    return "?"


def _append3bytes(b1: int, b2: int, b3: int) -> str:
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F

    r = ""
    r += _encode6bit(c1 & 0x3F)
    r += _encode6bit(c2 & 0x3F)
    r += _encode6bit(c3 & 0x3F)
    r += _encode6bit(c4 & 0x3F)
    return r


def encode_plantuml(text: str) -> str:
    """
    Deflate (wbits=-15) + спец. base64 от PlantUML.
    """
    data = text.encode("utf-8")
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    compressed = compressor.compress(data) + compressor.flush()

    res = []
    i = 0
    length = len(compressed)
    while i < length:
        b1 = compressed[i]
        b2 = compressed[i + 1] if i + 1 < length else 0
        b3 = compressed[i + 2] if i + 2 < length else 0
        res.append(_append3bytes(b1, b2, b3))
        i += 3

    return "".join(res)


def build_plantuml_url(code: str) -> str:
    encoded = encode_plantuml(code)
    return PLANTUML_SERVER_URL.rstrip("/") + "/png/" + encoded


# ===== 4. Основной тест =====

def main():
    print("PlantUML server:", PLANTUML_SERVER_URL)
    print("Пример PlantUML-кода:\n", EXAMPLE_PLANTUML, "\n")

    url = build_plantuml_url(EXAMPLE_PLANTUML)
    print("GET", url)

    resp = requests.get(url, timeout=30)

    print("HTTP status:", resp.status_code)
    content_type = resp.headers.get("Content-Type", "")
    print("Content-Type:", content_type)

    if resp.status_code == 200 and content_type.startswith("image/"):
        with open(OUTPUT_FILE, "wb") as f:
            f.write(resp.content)
        print(f"✅ Картинка сохранена в: {OUTPUT_FILE}")
    else:
        print("❌ Что-то пошло не так, ответ сервера:")
        try:
            print(resp.text[:1000])
        except Exception:
            print("<binary body>")


if __name__ == "__main__":
    main()
