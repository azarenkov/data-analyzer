import pandas as pd
import pytest

from app.domain.dataset.errors import InvalidQueryError
from app.domain.dataset.values import ExportFormat
from app.infrastructure.dataframe.pandas_table import PandasDataTable


def _upload_csv(client, content: bytes, name: str = "edge.csv") -> dict:
    response = client.post("/api/datasets", files={"file": (name, content, "text/csv")})
    assert response.status_code == 200
    return response.json()


def test_single_column_csv(client):
    meta = _upload_csv(client, b"name\nalpha\nbeta\ngamma\n")
    assert meta["columnCount"] == 1
    assert meta["rowCount"] == 3
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    assert [row["name"] for row in page["rows"]] == ["alpha", "beta", "gamma"]


def test_semicolon_csv(client):
    meta = _upload_csv(client, b"city;value\nAstana;10\nAlmaty;20\n")
    assert meta["columnCount"] == 2
    assert meta["rowCount"] == 2


def test_infinite_values_serialize_as_null(client):
    meta = _upload_csv(client, b"name,ratio\nalpha,inf\nbeta,2.5\ngamma,-inf\n")
    page = client.post(f"/api/datasets/{meta['id']}/query", json={})
    assert page.status_code == 200
    values = {row["name"]: row["ratio"] for row in page.json()["rows"]}
    assert values["alpha"] is None
    assert values["gamma"] is None
    assert values["beta"] == 2.5


def test_boolean_filter(client):
    meta = _upload_csv(client, b"name,active\nalpha,True\nbeta,False\ngamma,True\n")
    for value in (True, "true"):
        page = client.post(
            f"/api/datasets/{meta['id']}/query",
            json={"filters": [{"column": "active", "operator": "eq", "value": value}]},
        )
        assert page.status_code == 200
        assert {row["name"] for row in page.json()["rows"]} == {"alpha", "gamma"}


def test_timezone_aware_dates_export_to_xlsx(client):
    rows = ["ts,value"] + [f"2025-01-{i:02d}T10:00:00Z,{i}" for i in range(1, 6)]
    meta = _upload_csv(client, "\n".join(rows).encode())
    response = client.post(
        f"/api/datasets/{meta['id']}/export",
        json={"format": "xlsx"},
    )
    assert response.status_code == 200
    assert response.content[:2] == b"PK"


def test_xlsx_export_rejects_rows_over_excel_limit():
    table = PandasDataTable(pd.DataFrame({"a": range(1_048_576)}))
    with pytest.raises(InvalidQueryError):
        table.export(filters=[], sort=[], fmt=ExportFormat.XLSX)
