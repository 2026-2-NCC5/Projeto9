"""Testes da segunda via de boleto interativa (dados FICTICIOS)."""
import io
import sqlite3
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.main import app

client = TestClient(app)
BASE = "/api/v1/boletos"


def _login(email: str, password: str = "demo1234") -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="module")
def ana():
    return _login("estudante@demo.fecap.br")


@pytest.fixture(scope="module")
def carlos():
    return _login("estudante2@demo.fecap.br")


def _pending(headers):
    res = client.get(f"{BASE}/pending", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def test_pending_lists_only_own_unpaid_boletos(ana):
    data = _pending(ana)
    assert data["count"] == len(data["boletos"]) >= 1
    assert all(b["status"] in ("pendente", "vencido") for b in data["boletos"])
    assert data["total_cents"] == sum(b["amount_cents"] for b in data["boletos"])
    assert "SEM VALIDADE FINANCEIRA OU BANCÁRIA" in data["disclaimer"]


def test_single_selection_summary(ana):
    first = _pending(ana)["boletos"][0]
    res = client.post(f"{BASE}/summary", json={"boleto_ids": [first["id"]]}, headers=ana)
    assert res.status_code == 200
    assert res.json()["count"] == 1
    assert res.json()["total_cents"] == first["amount_cents"]


def test_multiple_selection_total_is_correct(ana):
    items = _pending(ana)["boletos"]
    assert len(items) >= 2
    ids = [b["id"] for b in items[:2]]
    res = client.post(f"{BASE}/summary", json={"boleto_ids": ids}, headers=ana)
    assert res.status_code == 200
    assert res.json()["total_cents"] == sum(b["amount_cents"] for b in items[:2])
    # ids duplicados nao somam duas vezes
    res = client.post(f"{BASE}/summary", json={"boleto_ids": [ids[0], ids[0]]}, headers=ana)
    assert res.json()["count"] == 1


def test_download_pdf_matches_selected_boleto(ana):
    item = _pending(ana)["boletos"][0]
    res = client.get(f"{BASE}/{item['id']}/pdf", headers=ana)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/pdf")
    assert item["document_id"] in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")
    text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(res.content)).pages)
    flat = " ".join(text.split())
    assert "AMBIENTE DE DEMONSTRA" in flat
    assert "SEM VALIDADE FINANCEIRA OU BANC" in flat
    assert item["competence_label"] in flat
    assert item["due_date"] in flat
    assert item["amount_label"] in flat
    assert item["document_id"] in flat
    assert "QR" not in flat.replace("QR Code e", "")  # sem QR Code de pagamento


def test_issue_returns_individual_documents(ana):
    ids = [b["id"] for b in _pending(ana)["boletos"][:2]]
    res = client.post(f"{BASE}/issue", json={"boleto_ids": ids}, headers=ana)
    assert res.status_code == 200
    body = res.json()
    assert len(body["documents"]) == len(ids)
    assert all(d["download_url"].endswith("/pdf") for d in body["documents"])


def test_other_student_cannot_access_boletos(ana, carlos):
    carlos_ids = {b["id"] for b in _pending(carlos)["boletos"]}
    ana_ids = {b["id"] for b in _pending(ana)["boletos"]}
    assert carlos_ids and not (carlos_ids & ana_ids)
    foreign = next(iter(carlos_ids))
    assert client.get(f"{BASE}/{foreign}/pdf", headers=ana).status_code == 404
    assert client.post(f"{BASE}/summary", json={"boleto_ids": [foreign]}, headers=ana).status_code == 404
    assert client.post(f"{BASE}/issue", json={"boleto_ids": [foreign]}, headers=ana).status_code == 404
    assert (
        client.post(f"{BASE}/{foreign}/simulate-payment", json={"confirm": True}, headers=ana).status_code
        == 404
    )


def test_requests_without_authentication_are_rejected():
    assert client.get(f"{BASE}/pending").status_code == 401
    assert client.get(f"{BASE}/abc/pdf").status_code == 401
    assert client.post(f"{BASE}/issue", json={"boleto_ids": ["x"]}).status_code == 401
    bad = {"Authorization": "Bearer token-invalido"}
    assert client.get(f"{BASE}/pending", headers=bad).status_code == 401


def test_student_without_boletos_gets_empty_list():
    db_path = settings.database_url.replace("sqlite:///", "")
    uid, sid = str(uuid.uuid4()), str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "INSERT INTO users (id,email,hashed_password,role,is_active,is_demo,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (uid, f"tmp-{uid[:8]}@teste.invalid", hash_password("x"), "student", 1, 0, now, now),
        )
        con.execute(
            "INSERT INTO students (id,user_id,name,ra,course,period,email,is_demo,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, uid, "Temp Ficticio", f"TMP{uid[:6]}", "Curso Demo", "1", f"s-{uid[:8]}@teste.invalid", 0, now, now),
        )
        con.commit()
        token = create_access_token({"sub": uid, "type": "access"})
        res = client.get(f"{BASE}/pending", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["count"] == 0
        assert res.json()["boletos"] == []
    finally:
        con.execute("DELETE FROM audit_logs WHERE user_id=?", (uid,))
        con.execute("DELETE FROM students WHERE id=?", (sid,))
        con.execute("DELETE FROM users WHERE id=?", (uid,))
        con.commit()
        con.close()


def test_status_preserved_after_issue_download_and_simulation(ana):
    before = {b["id"]: b["status"] for b in _pending(ana)["boletos"]}
    ids = list(before)
    client.post(f"{BASE}/issue", json={"boleto_ids": ids}, headers=ana)
    for i in ids:
        assert client.get(f"{BASE}/{i}/pdf", headers=ana).status_code == 200
    # simulacao exige confirmacao explicita
    assert client.post(f"{BASE}/{ids[0]}/simulate-payment", json={}, headers=ana).status_code == 400
    sim = client.post(f"{BASE}/{ids[0]}/simulate-payment", json={"confirm": True}, headers=ana)
    assert sim.status_code == 200 and sim.json()["simulated"] is True
    after = {b["id"]: b["status"] for b in _pending(ana)["boletos"]}
    assert after == before


def test_seed_is_idempotent(ana):
    assert _pending(ana)["count"] == _pending(ana)["count"]
    first = {b["document_id"] for b in _pending(ana)["boletos"]}
    second = {b["document_id"] for b in _pending(ana)["boletos"]}
    assert first == second
