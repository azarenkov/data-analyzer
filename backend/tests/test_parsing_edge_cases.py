import io

import pandas as pd


def _upload_csv(client, content: bytes) -> dict:
    response = client.post("/api/datasets", files={"file": ("edge.csv", content, "text/csv")})
    assert response.status_code == 200
    return response.json()


def test_contains_filter_is_literal(client):
    meta = _upload_csv(client, b"name,code\nalpha,A.B\nbeta,AxB\ngamma,C[1]\n")
    response = client.post(
        f"/api/datasets/{meta['id']}/query",
        json={"filters": [{"column": "code", "operator": "contains", "value": "A.B"}]},
    )
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert [r["name"] for r in rows] == ["alpha"]


def test_contains_filter_with_bracket_does_not_crash(client):
    meta = _upload_csv(client, b"name,code\nalpha,A.B\nbeta,AxB\ngamma,C[1]\n")
    response = client.post(
        f"/api/datasets/{meta['id']}/query",
        json={"filters": [{"column": "code", "operator": "contains", "value": "["}]},
    )
    assert response.status_code == 200
    assert [r["name"] for r in response.json()["rows"]] == ["gamma"]


def test_whitespace_duplicate_headers_are_disambiguated(client):
    meta = _upload_csv(client, b" A,A,B\n1,2,3\n4,5,6\n")
    response = client.get(f"/api/datasets/{meta['id']}")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()["columns"]]
    assert len(names) == len(set(names))
    assert set(names) == {"A", "A_2", "B"}


def test_excel_upload_roundtrip(client):
    frame = pd.DataFrame({"city": ["Astana", "Almaty"], "value": [10, 20]})
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    response = client.post(
        "/api/datasets",
        files={"file": ("cities.xlsx", buffer.getvalue())},
    )
    assert response.status_code == 200
    assert response.json()["rowCount"] == 2


def test_xls_engine_installed():
    import xlrd

    assert xlrd.__version__
