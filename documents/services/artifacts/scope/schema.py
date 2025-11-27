KEYS = [
    "title",
    "problem_statement",
    "business_goals",
    "target_users",
    "expected_outcomes",
    "success_criteria",
    "risks_and_limitations",
]


def validate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Vision payload must be an object")

    missing = [k for k in KEYS if k not in payload]
    if missing:
        raise ValueError(f"Vision payload missing keys: {', '.join(missing)}")

    for k in ["title", "problem_statement"]:
        if not isinstance(payload.get(k), str):
            raise ValueError(f"Vision.{k} must be a string")
        if not payload[k].strip():
            payload[k] = "Требует уточнения на основании исходных данных"

    list_fields = [
        "business_goals", "target_users", "expected_outcomes",
        "success_criteria", "risks_and_limitations"
    ]
    for k in list_fields:
        v = payload.get(k)
        if not isinstance(v, list):
            raise ValueError(f"Vision.{k} must be a list of strings")
        payload[k] = [x.strip() for x in v if isinstance(x, str) and x.strip()]

    return payload
