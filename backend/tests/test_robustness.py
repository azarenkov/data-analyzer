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


def test_datetime_filter_on_timezone_aware_column(client):
    rows = ["ts,value"] + [f"2025-01-{i:02d}T10:00:00Z,{i}" for i in range(1, 6)]
    meta = _upload_csv(client, "\n".join(rows).encode())
    page = client.post(
        f"/api/datasets/{meta['id']}/query",
        json={"filters": [{"column": "ts", "operator": "gte", "value": "2025-01-03"}]},
    )
    assert page.status_code == 200
    assert {row["value"] for row in page.json()["rows"]} == {3, 4, 5}


def test_summary_with_infinite_values(client):
    meta = _upload_csv(client, b"name,ratio\nalpha,inf\nbeta,2.5\ngamma,-inf\n")
    response = client.get(f"/api/datasets/{meta['id']}/summary")
    assert response.status_code == 200
    ratio = next(s for s in response.json() if s["column"] == "ratio")
    assert ratio["maximum"] == 2.5
    assert ratio["minimum"] == 2.5


def test_top_excludes_non_finite_values(client):
    meta = _upload_csv(client, b"name,ratio\nalpha,inf\nbeta,2.5\ngamma,-inf\ndelta,7.1\n")
    top = client.get(
        f"/api/datasets/{meta['id']}/top",
        params={"metric": "ratio", "limit": 2},
    )
    assert top.status_code == 200
    assert [row["name"] for row in top.json()["rows"]] == ["delta", "beta"]


def test_group_by_skips_infinite_aggregates(client):
    meta = _upload_csv(client, b"grp,ratio\na,inf\na,1.0\nb,2.0\nb,3.0\n")
    response = client.get(
        f"/api/datasets/{meta['id']}/group-by",
        params={"by": "grp", "metric": "ratio", "aggregation": "max"},
    )
    assert response.status_code == 200
    assert [g["label"] for g in response.json()] == ["b"]


def test_upload_size_limit(client, monkeypatch):
    from app.presentation import routes

    monkeypatch.setattr(routes, "MAX_UPLOAD_BYTES", 64)
    response = client.post(
        "/api/datasets",
        files={"file": ("big.csv", b"a,b\n" + b"1,2\n" * 100, "text/csv")},
    )
    assert response.status_code == 413


def test_json_upload_with_nested_values(client):
    payload = b'[{"name": "alpha", "meta": {"tags": ["a", "b"]}}, {"name": "beta", "meta": {"tags": []}}]'
    response = client.post(
        "/api/datasets",
        files={"file": ("nested.json", payload, "application/json")},
    )
    assert response.status_code == 200
    dataset_id = response.json()["id"]
    overview = client.get(f"/api/datasets/{dataset_id}")
    assert overview.status_code == 200
    page = client.post(f"/api/datasets/{dataset_id}/query", json={})
    assert page.status_code == 200
    assert "tags" in page.json()["rows"][0]["meta"]


def test_large_integer_filter_is_exact(client):
    meta = _upload_csv(client, b"id,name\n9007199254740993,alpha\n9007199254740992,beta\n")
    page = client.post(
        f"/api/datasets/{meta['id']}/query",
        json={"filters": [{"column": "id", "operator": "eq", "value": "9007199254740993"}]},
    )
    assert page.status_code == 200
    assert [row["name"] for row in page.json()["rows"]] == ["alpha"]


def test_timestamps_keep_precision_and_offset(client):
    meta = _upload_csv(
        client,
        b"ts,value\n2025-01-01T10:00:00.123Z,1\n2025-01-01T10:00:00.456Z,2\n",
    )
    page = client.post(f"/api/datasets/{meta['id']}/query", json={})
    assert page.status_code == 200
    values = [row["ts"] for row in page.json()["rows"]]
    assert values[0] != values[1]
    assert "+00:00" in values[0]
    assert ".123" in values[0]


def test_summary_ignores_non_finite_observations(client):
    meta = _upload_csv(client, b"name,ratio\nalpha,inf\nbeta,2.5\ngamma,-inf\n")
    response = client.get(f"/api/datasets/{meta['id']}/summary")
    ratio = next(s for s in response.json() if s["column"] == "ratio")
    assert ratio["count"] == 1
    assert ratio["mean"] == 2.5
    assert ratio["maximum"] == 2.5


def test_big_integers_serialize_as_strings(client):
    meta = _upload_csv(client, b"id,name\n9007199254740993,alpha\n5,beta\n")
    page = client.post(f"/api/datasets/{meta['id']}/query", json={})
    rows = {row["name"]: row["id"] for row in page.json()["rows"]}
    assert rows["alpha"] == "9007199254740993"
    assert rows["beta"] == 5


def test_group_sum_skips_all_missing_groups(client):
    meta = _upload_csv(client, b"grp,ratio\na,\na,\nb,2.0\nb,3.0\n")
    response = client.get(
        f"/api/datasets/{meta['id']}/group-by",
        params={"by": "grp", "metric": "ratio", "aggregation": "sum"},
    )
    assert response.status_code == 200
    groups = response.json()
    assert [g["label"] for g in groups] == ["b"]
    assert groups[0]["value"] == 5.0


def test_contains_does_not_match_missing_cells(client):
    meta = _upload_csv(client, b"name,note\nalpha,\nbeta,banana\n")
    hit = client.post(
        f"/api/datasets/{meta['id']}/query",
        json={"filters": [{"column": "note", "operator": "contains", "value": "nan"}]},
    ).json()
    assert [row["name"] for row in hit["rows"]] == ["beta"]
    miss = client.post(
        f"/api/datasets/{meta['id']}/query",
        json={"filters": [{"column": "note", "operator": "contains", "value": "xyz"}]},
    ).json()
    assert miss["rows"] == []


def test_mixed_offset_timestamps_detected_as_datetime(client):
    meta = _upload_csv(
        client,
        b"ts,value\n2025-03-30T01:00:00+01:00,1\n2025-03-30T03:00:00+02:00,2\n2025-03-30T04:00:00+02:00,3\n",
    )
    overview = client.get(f"/api/datasets/{meta['id']}").json()
    kinds = {c["name"]: c["kind"] for c in overview["columns"]}
    assert kinds["ts"] == "datetime"


def test_halves_change_ignores_non_finite_values():
    frame = pd.DataFrame(
        {
            "day": pd.to_datetime([f"2025-01-{i:02d}" for i in range(1, 9)]),
            "metric": [1.0, 2.0, 3.0, float("inf"), 5.0, 6.0, 7.0, 8.0],
        }
    )
    table = PandasDataTable(frame)
    changes = table.halves_change("day", "metric", by=None)
    assert len(changes) == 1
    assert changes[0].change_pct is not None
