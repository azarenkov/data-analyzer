import io

import pandas as pd


def _upload_csv(client, content: bytes, name: str = "edge.csv") -> dict:
    response = client.post("/api/datasets", files={"file": (name, content, "text/csv")})
    assert response.status_code == 200
    return response.json()


def test_mixed_string_column_is_not_coerced_to_dates(client):
    rows = ["day,label"] + [f"2025-01-{i:02d},ok" for i in range(1, 10)] + ["unknown,ok"]
    meta = _upload_csv(client, "\n".join(rows).encode())
    overview = client.get(f"/api/datasets/{meta['id']}").json()
    kinds = {c["name"]: c["kind"] for c in overview["columns"]}
    assert kinds["day"] != "datetime"
    page = client.post(f"/api/datasets/{meta['id']}/query", json={"pageSize": 20}).json()
    assert "unknown" in {row["day"] for row in page["rows"]}


def test_csv_export_escapes_formulas(client):
    meta = _upload_csv(client, b'name,note\nalpha,"=SUM(A1:A9)"\nbeta,plain\n')
    response = client.post(
        f"/api/datasets/{meta['id']}/export",
        json={"format": "csv"},
    )
    text = response.content.decode("utf-8-sig")
    assert "'=SUM(A1:A9)" in text
    assert "\nbeta,plain" in text


def test_xlsx_export_keeps_formula_as_text(client):
    meta = _upload_csv(client, b'name,note\nalpha,"=SUM(A1:A9)"\n')
    response = client.post(
        f"/api/datasets/{meta['id']}/export",
        json={"format": "xlsx"},
    )
    frame = pd.read_excel(io.BytesIO(response.content))
    assert frame.loc[0, "note"] == "=SUM(A1:A9)"


def test_report_contains_all_rows(client):
    rows = ["idx,value"] + [f"{i},{i * 2}" for i in range(10_050)]
    meta = _upload_csv(client, "\n".join(rows).encode(), name="big.csv")
    response = client.get(f"/api/datasets/{meta['id']}/report")
    assert response.status_code == 200
    frame = pd.read_excel(io.BytesIO(response.content), sheet_name="Данные")
    assert len(frame) == 10_050
