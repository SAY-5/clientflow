from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def sample_rule_set():
    return {
        "name": "orders",
        "input_schema": {
            "fields": [
                {"name": "amount", "type": "number"},
                {"name": "country", "type": "string"},
            ]
        },
        "rules": [
            {
                "id": "big",
                "condition": {
                    "kind": "comparison",
                    "field": "amount",
                    "op": "gte",
                    "value": 1000,
                },
                "actions": [{"type": "flag", "target": "review", "value": True}],
            }
        ],
    }


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_evaluate_endpoint_fires_rule():
    body = {"rule_set": sample_rule_set(), "payload": {"amount": 1200, "country": "US"}}
    res = client.post("/evaluate", json=body)
    assert res.status_code == 200
    assert res.json()["fired"] == ["big"]


def test_evaluate_rejects_unknown_field():
    rs = sample_rule_set()
    rs["rules"][0]["condition"]["field"] = "nope"
    res = client.post("/evaluate", json={"rule_set": rs, "payload": {}})
    assert res.status_code == 422
    assert "unknown field" in res.json()["detail"]
