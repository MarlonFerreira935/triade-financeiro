import os
import uuid

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="session")
def api_client():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL ausente no ambiente de testes")
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


@pytest.fixture(scope="session")
def cleanup_registry():
    # Registry for advisor conversations and transactions created in advisor/alerts tests
    return {"transactions": [], "conversations": []}


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_suite(api_client, cleanup_registry):
    yield
    for cid in cleanup_registry["conversations"]:
        api_client.delete(f"{BASE_URL}/api/advisor/conversations/{cid}")
    for txid in cleanup_registry["transactions"]:
        api_client.delete(f"{BASE_URL}/api/transactions/{txid}")


def _assert_ok(resp, expected=(200,)):
    assert resp.status_code in expected, f"{resp.status_code} -> {resp.text[:600]}"


def _stream_chat(api_client, payload, timeout=180):
    resp = api_client.post(
        f"{BASE_URL}/api/advisor/chat",
        json=payload,
        stream=True,
        timeout=timeout,
    )
    _assert_ok(resp)
    events = []
    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            import json

            events.append(json.loads(line[6:]))
    return events


def _stream_chat_with_retry(api_client, payload, timeout=180):
    events = _stream_chat(api_client, payload, timeout=timeout)
    has_delta = any(e.get("type") == "delta" for e in events)
    if not has_delta:
        events = _stream_chat(api_client, payload, timeout=timeout)
    return events


def _create_test_expense(api_client, amount, description_suffix=None):
    payload = {
        "description": f"TEST_ADVISOR_ALERT_{description_suffix or uuid.uuid4().hex[:8]}",
        "amount": amount,
        "date": "2026-07-25",
        "account_id": "50",
        "type": "despesa",
        "note": "teste advisor alerts",
    }
    create = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
    _assert_ok(create, expected=(201,))
    return create.json()


def test_alerts_baseline_july_and_june(api_client):
    # Baseline alerts contract for July/June including historical margin drop behavior
    july = api_client.get(f"{BASE_URL}/api/alerts", params={"month": "2026-07"})
    _assert_ok(july)
    july_data = july.json()
    assert july_data["month"] == "2026-07"
    assert july_data["count"] == 3

    june = api_client.get(f"{BASE_URL}/api/alerts", params={"month": "2026-06"})
    _assert_ok(june)
    june_data = june.json()
    assert june_data["count"] == 3
    margin_drop = [a for a in june_data["alerts"] if a["rule"] == "margin_drop"]
    assert margin_drop, "Esperava alerta de queda de margem em junho"
    assert margin_drop[0]["severity"] == "critico"
    assert "12,8" in margin_drop[0]["metric"]


def test_alert_negative_cash_trigger_and_resolution(api_client, cleanup_registry):
    # Rule-derived negative free cash critical alert must appear and disappear with transaction changes
    before = api_client.get(f"{BASE_URL}/api/dashboard", params={"month": "2026-07"})
    _assert_ok(before)
    base = before.json()["totals"]
    assert base["free_cash"] == 57522.79

    created = _create_test_expense(api_client, amount=70000, description_suffix="NEGATIVE")
    cleanup_registry["transactions"].append(created["id"])

    after_add = api_client.get(f"{BASE_URL}/api/alerts", params={"month": "2026-07"})
    _assert_ok(after_add)
    negative = [a for a in after_add.json()["alerts"] if a["rule"] == "negative_cash"]
    assert negative, "Alerta de caixa livre negativo não foi gerado"
    assert negative[0]["severity"] == "critico"

    update_payload = {
        "description": created["description"],
        "amount": 100,
        "date": "2026-07-25",
        "account_id": "50",
        "type": "despesa",
        "note": "teste advisor alerts reduzido",
    }
    upd = api_client.put(f"{BASE_URL}/api/transactions/{created['id']}", json=update_payload)
    _assert_ok(upd)

    after_fix = api_client.get(f"{BASE_URL}/api/alerts", params={"month": "2026-07"})
    _assert_ok(after_fix)
    no_negative = [a for a in after_fix.json()["alerts"] if a["rule"] == "negative_cash"]
    assert not no_negative

    delete_resp = api_client.delete(f"{BASE_URL}/api/transactions/{created['id']}")
    _assert_ok(delete_resp)
    cleanup_registry["transactions"].remove(created["id"])


def test_alert_acknowledgement_reappears_unread_when_metric_changes(api_client, cleanup_registry):
    # Acknowledged alert should become unread if same rule metric changes later
    created = _create_test_expense(api_client, amount=70000, description_suffix="ACK")
    cleanup_registry["transactions"].append(created["id"])

    feed = api_client.get(f"{BASE_URL}/api/alerts", params={"month": "2026-07"})
    _assert_ok(feed)
    neg = [a for a in feed.json()["alerts"] if a["rule"] == "negative_cash"]
    assert neg
    alert = neg[0]

    ack = api_client.put(
        f"{BASE_URL}/api/alerts/{alert['id']}/acknowledge",
        json={"month": "2026-07", "acknowledged": True},
    )
    _assert_ok(ack)

    feed_after_ack = api_client.get(f"{BASE_URL}/api/alerts", params={"month": "2026-07"})
    _assert_ok(feed_after_ack)
    neg_after_ack = [a for a in feed_after_ack.json()["alerts"] if a["rule"] == "negative_cash"]
    assert neg_after_ack and neg_after_ack[0]["acknowledged"] is True

    upd = api_client.put(
        f"{BASE_URL}/api/transactions/{created['id']}",
        json={
            "description": created["description"],
            "amount": 80000,
            "date": "2026-07-25",
            "account_id": "50",
            "type": "despesa",
            "note": "teste metrica alterada",
        },
    )
    _assert_ok(upd)

    feed_after_change = api_client.get(f"{BASE_URL}/api/alerts", params={"month": "2026-07"})
    _assert_ok(feed_after_change)
    neg_after_change = [a for a in feed_after_change.json()["alerts"] if a["rule"] == "negative_cash"]
    assert neg_after_change
    assert neg_after_change[0]["acknowledged"] is False

    delete_resp = api_client.delete(f"{BASE_URL}/api/transactions/{created['id']}")
    _assert_ok(delete_resp)
    cleanup_registry["transactions"].remove(created["id"])


def test_advisor_chat_stream_events_persistence_and_content_guardrails(api_client, cleanup_registry):
    # Streaming advisor chat events and persistence with grounded July values and bank-balance disclaimer
    july = api_client.get(f"{BASE_URL}/api/dashboard", params={"month": "2026-07"})
    _assert_ok(july)
    totals = july.json()["totals"]
    assert totals["revenue"] == 266000
    assert totals["profit"] == 102522.79
    assert totals["margin"] == 41.27
    assert totals["free_cash"] == 57522.79

    message = "Qual foi meu lucro líquido e minha margem em julho de 2026? Também diga meu saldo bancário."
    events = _stream_chat_with_retry(api_client, {"month": "2026-07", "message": message})

    assert any(e.get("type") == "meta" for e in events)
    assert any(e.get("type") == "delta" for e in events)
    assert any(e.get("type") == "done" for e in events)

    meta = next(e for e in events if e.get("type") == "meta")
    cid = meta["conversation_id"]
    cleanup_registry["conversations"].append(cid)

    deltas = [e.get("text", "") for e in events if e.get("type") == "delta"]
    answer = "".join(deltas)
    assert "102.522,79" in answer
    assert ("41,27" in answer) or ("41,3" in answer)
    assert "saldo banc" in answer.lower()
    assert any(token in answer.lower() for token in ["não", "nao", "não informa", "não é saldo"])

    conv = api_client.get(f"{BASE_URL}/api/advisor/conversations/{cid}")
    _assert_ok(conv)
    data = conv.json()
    assert data["id"] == cid
    assert len(data["messages"]) >= 2
    assert any(m["role"] == "assistant" and m["status"] in ["complete", "failed"] for m in data["messages"])


def test_advisor_chat_multiturn_memory_and_month_mismatch_rejected(api_client, cleanup_registry):
    # Multi-turn same-conversation memory + period mismatch protection
    first = _stream_chat_with_retry(
        api_client,
        {"month": "2026-07", "message": "Faça um resumo rápido da saúde financeira de julho."},
    )
    first_meta = next(e for e in first if e.get("type") == "meta")
    cid = first_meta["conversation_id"]
    cleanup_registry["conversations"].append(cid)

    second = _stream_chat_with_retry(
        api_client,
        {
            "month": "2026-07",
            "conversation_id": cid,
            "message": "Com base no que você acabou de dizer, qual ação eu priorizo primeiro?",
        },
    )
    assert any(e.get("type") == "done" for e in second)
    second_answer = "".join([e.get("text", "") for e in second if e.get("type") == "delta"])
    assert len(second_answer.strip()) > 20

    conversation_data = api_client.get(f"{BASE_URL}/api/advisor/conversations/{cid}")
    _assert_ok(conversation_data)
    messages = conversation_data.json()["messages"]
    assert len(messages) >= 4

    mismatch = api_client.post(
        f"{BASE_URL}/api/advisor/chat",
        json={
            "month": "2026-06",
            "conversation_id": cid,
            "message": "Teste de período diferente",
        },
    )
    assert mismatch.status_code == 409


def test_advisor_chat_validation_and_no_data_month_behavior(api_client):
    # Input validation and honest no-data month response behavior
    blank = api_client.post(
        f"{BASE_URL}/api/advisor/chat",
        json={"month": "2026-07", "message": "   "},
    )
    assert blank.status_code == 422

    invalid_month = api_client.post(
        f"{BASE_URL}/api/advisor/chat",
        json={"month": "2026-13", "message": "teste"},
    )
    assert invalid_month.status_code == 422

    no_data_events = _stream_chat_with_retry(
        api_client,
        {"month": "2025-01", "message": "Como está minha saúde financeira nesse mês?"},
    )
    meta = next((e for e in no_data_events if e.get("type") == "meta"), {})
    assert meta.get("record_count") == 0
    no_data_answer = "".join([e.get("text", "") for e in no_data_events if e.get("type") == "delta"])
    assert no_data_answer.strip(), "Resposta vazia para mês sem dados"
    lowered = no_data_answer.lower()
    assert any(
        fragment in lowered
        for fragment in [
            "sem dados",
            "não há dados",
            "nao ha dados",
            "não encontrei",
            "não tenho dados",
            "selecione",
            "lançamento",
            "período",
        ]
    )
    assert "saúde financeira excelente" not in lowered
    assert "julho de 2026" not in lowered
