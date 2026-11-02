"""Content-free HTTP smoke against the separately verified isolated ERP on8001.

Requires LENY_SMOKE_USERNAME and LENY_SMOKE_PASSWORD for its disposable identity.
Does not read .env or connect to PostgreSQL. Uses no Qwen generation requests.
"""
import json
import os
from pathlib import Path
import re
from uuid import uuid4

import httpx


def main():
    username = os.environ.get("LENY_SMOKE_USERNAME", "")
    password = os.environ.get("LENY_SMOKE_PASSWORD", "")
    if not re.fullmatch(r"leny_smoke_[0-9a-f]{12}", username) or not password:
        raise RuntimeError("An existing disposable smoke identity is required.")
    results = {}
    with httpx.Client(base_url="http://127.0.0.1:8001/api/v1", trust_env=False, timeout=15) as client:
        login = client.post("/auth/login", json={"username": username, "password": password})
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
        conversation = client.post("/leny/conversations")
        conversation.raise_for_status()
        cid = conversation.json()["id"]
        payload = {"conversation_id": cid, "request_id": str(uuid4()), "message": "¿Quién fue el primer presidente de Bolivia?"}
        try:
            invalid = {**payload, "message": "eyJhbGciOiJub25lIn0.synthetic.signature"}
            rejected = client.post("/leny/chat", json=invalid)
            assert rejected.status_code == 422 and invalid["message"] not in rejected.text
            results["secret_422_no_echo"] = True
            assert client.post("/leny/chat", json={**payload, "system": "override"}).status_code == 422
            results["privileged_fields_422"] = True
            first = None
            for index in range(5):
                current = {**payload, "request_id": str(uuid4())}
                response = client.post("/leny/chat", json=current)
                assert response.status_code == 200
                events = [json.loads(line) for line in response.text.splitlines()]
                assert events[-1]["type"] == "done" and events[-1]["outcome"] == "refused"
                if first is None:
                    first = current
            results["five_policy_attempts_admitted"] = True
            duplicate = client.post("/leny/chat", json=first)
            assert duplicate.status_code == 409 and duplicate.json()["detail"]["code"] == "LENY_REQUEST_DUPLICATE"
            results["duplicate_after_quota_not_recharged"] = True
            limited = client.post("/leny/chat", json={**payload, "request_id": str(uuid4())}, headers={"Origin": "http://127.0.0.1:5174"})
            assert limited.status_code == 429 and limited.json()["detail"]["code"] == "LENY_RATE_LIMITED"
            retry = int(limited.headers["Retry-After"])
            assert 1 <= retry <= 60
            assert "retry-after" in limited.headers.get("access-control-expose-headers", "").lower()
            results.update(sixth_attempt_429=True, retry_after_seconds=retry, cors_retry_after_exposed=True)
            detail = client.get("/leny/conversations/" + cid).json()
            assert len(detail["items"]) == 10
            assert all(not item["context_eligible"] for item in detail["items"])
            results["refusals_persisted_excluded_from_context"] = True
            client.headers.pop("Authorization")
            refreshed = client.post("/auth/refresh")
            refreshed.raise_for_status()
            client.headers["Authorization"] = "Bearer " + refreshed.json()["access_token"]
            assert client.get("/leny/conversations/" + cid).status_code == 200
            results["refresh_and_history"] = True
        finally:
            # Only the conversation created by this disposable smoke workflow.
            removed = client.delete("/leny/conversations/" + cid)
            if removed.status_code != 204:
                raise RuntimeError("Own synthetic smoke conversation cleanup requires inspection.")
    report = Path(__file__).resolve().parents[2] / "documentacion/evidencias/leny_011_api_smoke.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"scope": "real HTTP / isolated ERP8001 / synthetic user / no model inference", "results": results}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        import traceback
        location = traceback.extract_tb(error.__traceback__)[-1]
        print("Isolated LENY HTTP smoke failed safely: " + type(error).__name__ + " line=" + str(location.lineno))
        raise SystemExit(1) from None
