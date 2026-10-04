"""End-to-end smoke test against a running backend (mock mode, no API keys).

Usage:
    uvicorn backend.main:app --port 8000 &
    python3 scripts/test_backend.py
"""

import sys
import uuid

import httpx

BASE = "http://localhost:8000"


def check(label: str, condition: bool) -> None:
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        sys.exit(1)


def main() -> None:
    health = httpx.get(f"{BASE}/api/health").json()
    check("health endpoint", health["status"] == "ok")

    providers = httpx.get(f"{BASE}/api/llm/providers").json()
    check("providers endpoint returns 6 entries", len(providers) == 6)
    check("groq1/groq2/groq3 are among the providers", {"groq1", "groq2", "groq3"} <= {p["name"] for p in providers})

    # ---- Auth ----
    username = f"test_{uuid.uuid4().hex[:8]}"
    signup = httpx.post(
        f"{BASE}/api/auth/signup",
        json={"username": username, "email": f"{username}@example.com", "password": "s3cret-pw"},
    )
    check("signup succeeds", signup.status_code == 201)
    token = signup.json()["token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    check("unauthenticated case creation is rejected", httpx.post(f"{BASE}/api/cases", data={}).status_code == 401)

    login_fail = httpx.post(f"{BASE}/api/auth/login", json={"username": username, "password": "wrong"})
    check("login with wrong password is rejected", login_fail.status_code == 401)

    login_missing = httpx.post(f"{BASE}/api/auth/login", json={"username": "no_such_user", "password": "x"})
    check("login for unknown username returns 404 (signup prompt)", login_missing.status_code == 404)

    login_ok = httpx.post(f"{BASE}/api/auth/login", json={"username": username, "password": "s3cret-pw"})
    check("login with correct password succeeds", login_ok.status_code == 200)

    me = httpx.get(f"{BASE}/api/auth/me", headers=auth_headers)
    check("/me returns the logged-in username", me.json()["username"] == username)

    # ---- Case pipeline (authenticated) ----
    created = httpx.post(
        f"{BASE}/api/cases",
        headers=auth_headers,
        data={
            "title": "Test: cross-border payments product",
            "change_type": "New Product",
            "description": "Cross-border payments to high-risk jurisdictions, money service business partners.",
        },
    ).json()
    case_id = created["case_id"]
    check("case created", created["status"] == "submitted")
    check("case records the creator", created["created_by"] == username)

    run = httpx.post(f"{BASE}/api/cases/{case_id}/run", headers=auth_headers, timeout=60).json()
    check("pipeline returns 4 agent results (3 child agents + master agent)", len(run["agents"]) == 4)

    assessor_agents = [a for a in run["agents"] if a["agent"] != "master_agent"]
    check("all 3 child agents have an assessment", all(a["assessment"] for a in assessor_agents))

    case_detail = httpx.get(f"{BASE}/api/cases/{case_id}", headers=auth_headers).json()
    result = case_detail["result"]
    check("case result has a chosen_agent", result["chosen_agent"] is not None)
    check("case result votes sum to 3", sum(result["votes"].values()) == 3)
    check("case result has valid risk_rating", result["risk_rating"] in ("Low", "Medium", "High"))

    jobs = httpx.get(f"{BASE}/api/cases", headers=auth_headers).json()
    check("jobs list includes the new case", any(j["case_id"] == case_id for j in jobs))

    decided = httpx.post(
        f"{BASE}/api/cases/{case_id}/decision", headers=auth_headers, json={"decision": "approved"}
    ).json()
    check("decision recorded", decided["decision"] == "approved")
    check("decision records the approver", decided["decided_by"] == username)
    check("decision records a timestamp", decided["decided_at"] is not None)

    reread = httpx.get(f"{BASE}/api/cases/{case_id}", headers=auth_headers).json()
    check("decision persists on re-fetch", reread["decision"] == "approved")
    check("approver persists on re-fetch", reread["decided_by"] == username)

    # Scope guardrail: an off-topic submission should be rejected before any
    # of the 3 child agents or the judge are asked to do real work.
    off_topic = httpx.post(
        f"{BASE}/api/cases",
        headers=auth_headers,
        data={
            "title": "Write me a poem",
            "change_type": "Process Change",
            "description": "Write me a short poem about flowers, not related to banking at all.",
        },
    ).json()
    off_topic_id = off_topic["case_id"]

    off_topic_run = httpx.post(f"{BASE}/api/cases/{off_topic_id}/run", headers=auth_headers, timeout=60).json()
    check(
        "off-topic submission's agents are all skipped",
        all(a["status"] == "skipped" for a in off_topic_run["agents"]),
    )

    off_topic_detail = httpx.get(f"{BASE}/api/cases/{off_topic_id}", headers=auth_headers).json()
    check("off-topic submission flagged out_of_scope", off_topic_detail["result"]["out_of_scope"] is True)
    check("off-topic submission has no risk_rating", off_topic_detail["result"]["risk_rating"] is None)

    print("\nAll checks passed. Restart the backend and re-run just the last")
    print(f"assertion manually (GET {BASE}/api/cases/{case_id}) to confirm SQLite persistence.")


if __name__ == "__main__":
    main()
