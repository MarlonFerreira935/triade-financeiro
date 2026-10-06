import io
import os
from collections import Counter
from pathlib import Path

import openpyxl
import pytest
import requests
from PIL import Image, ImageDraw


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


@pytest.fixture(scope="session")
def api_client():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL ausente no ambiente de testes")
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    return s


@pytest.fixture(scope="session")
def created_records():
    # Test cleanup registry for transactions and receipts created by this suite
    return {"transactions": [], "receipts": []}


@pytest.fixture(scope="session", autouse=True)
def cleanup_created_records(api_client, created_records):
    yield
    for tx_id in created_records["transactions"]:
        api_client.delete(f"{BASE_URL}/api/transactions/{tx_id}")
    for rid in created_records["receipts"]:
        api_client.delete(f"{BASE_URL}/api/receipts/{rid}")


@pytest.fixture(scope="session")
def receipt_image_bytes():
    # Receipt OCR integration image fixture with legible text and values
    img = Image.new("RGB", (1200, 900), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    lines = [
        "SUPERMERCADO TRI TESTE",
        "DATA: 17/07/2026",
        "TOTAL: R$ 128,90",
        "CATEGORIA: administrativo",
        "CNPJ: 12.345.678/0001-90",
    ]
    y = 120
    for line in lines:
        draw.text((120, y), line, fill=(0, 0, 0))
        y += 90
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _assert_success(resp, allowed=(200,)):
    assert resp.status_code in allowed, f"{resp.status_code} -> {resp.text[:500]}"


def _year_records_count(api_client, year: int):
    months = [f"{year}-05", f"{year}-06", f"{year}-07"]
    count = 0
    ids = []
    for m in months:
        r = api_client.get(f"{BASE_URL}/api/transactions", params={"month": m})
        _assert_success(r)
        data = r.json()
        count += len(data)
        ids.extend([i["id"] for i in data])
    return count, ids


def test_health_meta_and_july_dashboard_values(api_client):
    # Core health/meta/dashboard integration verification
    health = api_client.get(f"{BASE_URL}/api/")
    _assert_success(health)
    assert health.json().get("status") == "ok"

    meta = api_client.get(f"{BASE_URL}/api/meta")
    _assert_success(meta)
    meta_data = meta.json()
    assert meta_data["whatsapp_connected"] is False
    assert "2026-07" in meta_data["months"]

    july = api_client.get(f"{BASE_URL}/api/dashboard", params={"month": "2026-07"})
    _assert_success(july)
    totals = july.json()["totals"]
    assert totals["revenue"] == 266000
    assert totals["expenses"] == 165070.21
    assert totals["profit"] == 102522.79
    assert totals["free_cash"] == 57522.79
    assert totals["margin"] == 41.27
    assert totals["break_even"] == 39279.1


def test_transaction_crud_and_validations(api_client, created_records):
    # Transaction lifecycle + account type + zero/negative validation
    base_payload = {
        "description": "TEST_API_DESPESA",
        "amount": 149.5,
        "date": "2026-07-18",
        "account_id": "50",
        "type": "despesa",
        "note": "teste regressao",
    }
    create = api_client.post(f"{BASE_URL}/api/transactions", json=base_payload)
    _assert_success(create, allowed=(201,))
    tx = create.json()
    created_records["transactions"].append(tx["id"])
    assert tx["description"] == "TEST_API_DESPESA"
    assert tx["amount"] == 149.5
    assert tx["category"]

    get_list = api_client.get(f"{BASE_URL}/api/transactions", params={"month": "2026-07", "search": "TEST_API_DESPESA"})
    _assert_success(get_list)
    assert any(t["id"] == tx["id"] for t in get_list.json())

    update_payload = {
        "description": "TEST_API_DESPESA_EDITADA",
        "amount": 155.75,
        "date": "2026-07-19",
        "account_id": "50",
        "type": "despesa",
        "note": "editado",
    }
    upd = api_client.put(f"{BASE_URL}/api/transactions/{tx['id']}", json=update_payload)
    _assert_success(upd)
    assert upd.json()["description"] == "TEST_API_DESPESA_EDITADA"

    wrong_account = dict(update_payload)
    wrong_account["type"] = "receita"
    invalid_type = api_client.put(f"{BASE_URL}/api/transactions/{tx['id']}", json=wrong_account)
    assert invalid_type.status_code == 422

    zero_amount = dict(update_payload)
    zero_amount["amount"] = 0
    zero_resp = api_client.post(f"{BASE_URL}/api/transactions", json=zero_amount)
    assert zero_resp.status_code == 422

    negative = dict(update_payload)
    negative["amount"] = -3
    negative_resp = api_client.post(f"{BASE_URL}/api/transactions", json=negative)
    assert negative_resp.status_code == 422

    delete_resp = api_client.delete(f"{BASE_URL}/api/transactions/{tx['id']}")
    _assert_success(delete_resp)
    created_records["transactions"].remove(tx["id"])
    refetch = api_client.get(f"{BASE_URL}/api/transactions", params={"month": "2026-07", "search": "TEST_API_DESPESA_EDITADA"})
    _assert_success(refetch)
    assert all(i["id"] != tx["id"] for i in refetch.json())


def test_spreadsheet_import_idempotence_and_record_count(api_client):
    # Spreadsheet import idempotence and duplicate prevention on original workbook
    before_count, before_ids = _year_records_count(api_client, 2026)

    with open("/app/backend/assets/triade_original.xlsx", "rb") as f:
        files = {"file": ("triade_original.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        first = api_client.post(f"{BASE_URL}/api/spreadsheet/import", data={"year": "2026"}, files=files)
    _assert_success(first)
    imported = first.json()
    assert imported["count"] >= 65

    after_count, after_ids = _year_records_count(api_client, 2026)
    assert after_count == before_count
    dupes = [k for k, v in Counter(after_ids).items() if v > 1]
    assert not dupes

    with open("/app/backend/assets/triade_original.xlsx", "rb") as f:
        files = {"file": ("triade_original.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        second = api_client.post(f"{BASE_URL}/api/spreadsheet/import", data={"year": "2026"}, files=files)
    _assert_success(second)
    second_count, _ = _year_records_count(api_client, 2026)
    assert second_count == after_count
    assert second.json()["count"] == imported["count"]


def test_spreadsheet_reject_corrupted_and_export_reimport_blocked(api_client):
    # Spreadsheet validation: corrupted/incompatible file and exported re-import blocking
    bad = io.BytesIO(b"not an excel file")
    bad_resp = api_client.post(
        f"{BASE_URL}/api/spreadsheet/import",
        data={"year": "2026"},
        files={"file": ("bad.xlsx", bad, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert bad_resp.status_code == 400

    export = api_client.get(f"{BASE_URL}/api/spreadsheet/export", params={"year": "2026"})
    _assert_success(export)

    blocked = api_client.post(
        f"{BASE_URL}/api/spreadsheet/import",
        data={"year": "2026"},
        files={"file": ("exported.xlsx", io.BytesIO(export.content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert blocked.status_code == 400
    assert "Reimportação bloqueada" in blocked.text


def test_export_preserves_original_workbook_structure_formulas_and_styles(api_client):
    # Export verification: all original sheets/names/formulas/styles preserved + system ledger
    original = api_client.get(f"{BASE_URL}/api/spreadsheet/original")
    _assert_success(original)
    exported = api_client.get(f"{BASE_URL}/api/spreadsheet/export", params={"year": "2026"})
    _assert_success(exported)

    wb_orig = openpyxl.load_workbook(io.BytesIO(original.content), data_only=False)
    wb_exp = openpyxl.load_workbook(io.BytesIO(exported.content), data_only=False)

    assert len(wb_orig.sheetnames) == 14
    assert wb_exp.sheetnames[:len(wb_orig.sheetnames)] == wb_orig.sheetnames
    assert "Lançamentos do Sistema" in wb_exp.sheetnames

    for sheet_name in wb_orig.sheetnames:
        s1 = wb_orig[sheet_name]
        s2 = wb_exp[sheet_name]
        assert s1["A1"].style_id == s2["A1"].style_id
        formulas_1 = {}
        formulas_2 = {}
        for row in s1.iter_rows(min_row=1, max_row=s1.max_row, min_col=1, max_col=s1.max_column):
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    formulas_1[c.coordinate] = c.value
        for row in s2.iter_rows(min_row=1, max_row=s2.max_row, min_col=1, max_col=s2.max_column):
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    formulas_2[c.coordinate] = c.value
        for coord, formula in formulas_1.items():
            assert formulas_2.get(coord) == formula

    wb_orig.close()
    wb_exp.close()


def test_receipt_upload_download_ocr_and_posting_flow(api_client, created_records, receipt_image_bytes):
    # Receipt storage/OCR/confirmation workflow + duplicate receipt link prevention
    files = {"file": ("TEST_RECEIPT.png", io.BytesIO(receipt_image_bytes), "image/png")}
    upload = api_client.post(f"{BASE_URL}/api/receipts", data={"month": "2026-07"}, files=files, timeout=180)
    _assert_success(upload, allowed=(201,))
    data = upload.json()
    rid = data["id"]
    created_records["receipts"].append(rid)
    assert data["status"] == "pendente"
    assert data["transaction_id"] is None
    assert data["content_type"] in ["image/jpeg", "image/png", "image/webp"]
    assert "extraction" in data and isinstance(data["extraction"], dict)

    download = api_client.get(f"{BASE_URL}/api/receipts/{rid}/file")
    _assert_success(download)
    assert download.content == receipt_image_bytes

    tx_payload = {
        "description": "TEST_RECEIPT_POSTED",
        "amount": data["extraction"].get("amount") or 128.90,
        "date": data["extraction"].get("date") or "2026-07-17",
        "account_id": data["extraction"].get("account_id") or "50",
        "type": data["extraction"].get("type") or "despesa",
        "note": "vinculado ao comprovante",
        "receipt_id": rid,
    }
    create_tx = api_client.post(f"{BASE_URL}/api/transactions", json=tx_payload)
    _assert_success(create_tx, allowed=(201,))
    tx_id = create_tx.json()["id"]
    created_records["transactions"].append(tx_id)

    list_receipts = api_client.get(f"{BASE_URL}/api/receipts", params={"month": "2026-07"})
    _assert_success(list_receipts)
    linked = [r for r in list_receipts.json() if r["id"] == rid][0]
    assert linked["status"] == "lancado"
    assert linked["transaction_id"] == tx_id

    duplicate = api_client.post(f"{BASE_URL}/api/transactions", json={**tx_payload, "description": "TEST_DUP_LINK"})
    assert duplicate.status_code == 409


def test_receipt_pdf_behavior_and_file_type_size_validation(api_client):
    # Receipt validations: PDF no OCR, extension validation and 10MB limit
    pdf_data = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_pdf = api_client.post(
        f"{BASE_URL}/api/receipts",
        data={"month": "2026-07"},
        files={"file": ("TEST_MANUAL.pdf", io.BytesIO(pdf_data), "application/pdf")},
    )
    _assert_success(upload_pdf, allowed=(201,))
    pdf_record = upload_pdf.json()
    assert "PDF salvo" in (pdf_record.get("warning") or "")
    rid = pdf_record["id"]

    bad_type = api_client.post(
        f"{BASE_URL}/api/receipts",
        data={"month": "2026-07"},
        files={"file": ("bad.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert bad_type.status_code == 400

    big = io.BytesIO(b"A" * (10 * 1024 * 1024 + 10))
    too_large = api_client.post(
        f"{BASE_URL}/api/receipts",
        data={"month": "2026-07"},
        files={"file": ("big.png", big, "image/png")},
    )
    assert too_large.status_code == 413

    api_client.delete(f"{BASE_URL}/api/receipts/{rid}")


def test_dre_rows_and_monthly_vs_comparison_contract(api_client):
    # DRE data contract verification for row mapping and monthly values
    dre = api_client.get(f"{BASE_URL}/api/dre", params={"year": 2026})
    _assert_success(dre)
    data = dre.json()
    assert data["year"] == 2026
    assert len(data["months"]) == 12
    rows = data["rows"]
    assert any(r["row"] == 67 for r in rows)
    assert any(r["account"] for r in rows)
    for row in rows:
        assert len(row["values"]) == 12


def test_ai_diagnostics_stream_and_persistence(api_client):
    # AI diagnostics SSE streaming and persistence check
    stream = api_client.get(
        f"{BASE_URL}/api/diagnostics/stream",
        params={"month": "2026-07"},
        stream=True,
        timeout=180,
    )
    _assert_success(stream)
    chunks = []
    for line in stream.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            chunks.append(line)
    assert any('"done": true' in c for c in chunks)
    assert any('"text":' in c for c in chunks)

    latest = api_client.get(f"{BASE_URL}/api/diagnostics/latest", params={"month": "2026-07"})
    _assert_success(latest)
    assert isinstance(latest.json().get("text", ""), str)
    assert len(latest.json().get("text", "")) > 10


def test_ai_diagnostics_no_data_month_rejected(api_client):
    # AI no-data month behavior must block generation
    empty = api_client.get(f"{BASE_URL}/api/diagnostics/stream", params={"month": "2025-01"})
    assert empty.status_code == 400
