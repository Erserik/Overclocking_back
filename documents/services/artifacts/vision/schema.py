KEYS = [
    "summary",
    "in_scope",
    "out_of_scope",
    "business_processes_in_scope",
    "systems_in_scope",
    "assumptions",
    "constraints",
]


def validate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Scope payload must be an object")

    missing = [k for k in KEYS if k not in payload]
    if missing:
        raise ValueError(f"Scope payload missing keys: {', '.join(missing)}")

    if not isinstance(payload.get("summary"), str):
        raise ValueError("Scope.summary must be a string")
    if not payload["summary"].strip():
        payload["summary"] = "Требует уточнения на основании исходных данных"

    list_fields = [k for k in KEYS if k != "summary"]
    for k in list_fields:
        v = payload.get(k)
        if not isinstance(v, list):
            raise ValueError(f"Scope.{k} must be a list of strings")
        payload[k] = [x.strip() for x in v if isinstance(x, str) and x.strip()]

    return payload
