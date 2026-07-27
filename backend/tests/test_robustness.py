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


def test_mixed_column_stringifies_unsafe_integers(client):
    payload = b'[{"id": 9007199254740993, "tag": "x"}, {"id": "manual", "tag": "y"}]'
    response = client.post(
        "/api/datasets",
        files={"file": ("mixed.json", payload, "application/json")},
    )
    assert response.status_code == 200
    page = client.post(f"/api/datasets/{response.json()['id']}/query", json={})
    values = {row["tag"]: row["id"] for row in page.json()["rows"]}
    assert values["x"] == "9007199254740993"
    assert values["y"] == "manual"


def test_sorting_mixed_type_column(client):
    payload = b'[{"v": 10, "n": "a"}, {"v": "text", "n": "b"}, {"v": 2, "n": "c"}]'
    response = client.post(
        "/api/datasets",
        files={"file": ("mixedsort.json", payload, "application/json")},
    )
    assert response.status_code == 200
    page = client.post(
        f"/api/datasets/{response.json()['id']}/query",
        json={"sort": [{"column": "v", "descending": False}]},
    )
    assert page.status_code == 200
    assert len(page.json()["rows"]) == 3


def test_xlsx_export_keeps_large_integers_exact(client):
    import io

    meta = _upload_csv(client, b"id,name\n9007199254740993,alpha\n5,beta\n")
    response = client.post(
        f"/api/datasets/{meta['id']}/export",
        json={"format": "xlsx"},
    )
    assert response.status_code == 200
    frame = pd.read_excel(io.BytesIO(response.content), dtype={"id": str})
    assert "9007199254740993" in set(frame["id"])


def test_weekly_buckets_start_on_monday(client):
    meta = _upload_csv(
        client,
        b"day,value\n2025-01-06,1\n2025-01-07,2\n2025-01-12,3\n2025-01-13,4\n",
    )
    response = client.get(
        f"/api/datasets/{meta['id']}/time-series",
        params={"dateColumn": "day", "metric": "value", "aggregation": "sum", "frequency": "week"},
    )
    assert response.status_code == 200
    points = {p["period"]: p["value"] for p in response.json()}
    assert points == {"2025-01-06": 6.0, "2025-01-13": 4.0}


def test_correlations_survive_infinite_values():
    frame = pd.DataFrame(
        {
            "a": [1.0, 2.0, 3.0, 4.0, float("inf")],
            "b": [2.0, 4.0, 6.0, 8.0, 10.0],
        }
    )
    table = PandasDataTable(frame)
    pairs = table.correlation_pairs(limit=1)
    assert pairs
    assert abs(pairs[0].value - 1.0) < 1e-9


def test_xlsx_export_rejects_too_many_columns():
    frame = pd.DataFrame([[1] * 16_385], columns=[f"c{i}" for i in range(16_385)])
    table = PandasDataTable(frame)
    with pytest.raises(InvalidQueryError):
        table.export(filters=[], sort=[], fmt=ExportFormat.XLSX)


def test_report_keeps_16_digit_integers_exact(client):
    import io

    meta = _upload_csv(client, b"account,name\n1234567890123456,alpha\n7,beta\n")
    response = client.get(f"/api/datasets/{meta['id']}/report")
    assert response.status_code == 200
    frame = pd.read_excel(
        io.BytesIO(response.content), sheet_name="Данные", dtype={"account": str}
    )
    assert "1234567890123456" in set(frame["account"])


def test_halves_split_uses_time_range_midpoint():
    frame = pd.DataFrame(
        {
            "day": pd.to_datetime(
                ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05",
                 "2025-12-30", "2025-12-31"]
            ),
            "metric": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0, 101.0],
        }
    )
    table = PandasDataTable(frame)
    changes = table.halves_change("day", "metric", by=None)
    assert len(changes) == 1
    assert changes[0].first == 3.0
    assert changes[0].second == 100.5


def test_whitespace_only_header_gets_generated_name(client):
    meta = _upload_csv(client, b" ,b\n1,2\n3,4\n")
    overview = client.get(f"/api/datasets/{meta['id']}").json()
    names = [c["name"] for c in overview["columns"]]
    assert names == ["column", "b"]
    page = client.post(
        f"/api/datasets/{meta['id']}/query",
        json={"filters": [{"column": "column", "operator": "eq", "value": "1"}]},
    )
    assert page.status_code == 200
    assert len(page.json()["rows"]) == 1


def test_na_like_strings_are_preserved(client):
    meta = _upload_csv(client, b"code,value\nNA,1\nN/A,2\nNULL,3\n,4\n")
    overview = client.get(f"/api/datasets/{meta['id']}").json()
    missing = {c["name"]: c["missing"] for c in overview["columns"]}
    assert missing["code"] == 1
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    codes = [row["code"] for row in page["rows"]]
    assert codes == ["NA", "N/A", "NULL", None]


def test_report_keeps_dates_typed(client):
    import io

    meta = _upload_csv(client, b"day,value\n2025-01-01,1\n2025-01-02,2\n")
    response = client.get(f"/api/datasets/{meta['id']}/report")
    assert response.status_code == 200
    frame = pd.read_excel(io.BytesIO(response.content), sheet_name="Данные")
    assert frame["day"].dtype.kind == "M"


def test_correlation_columns_are_capped():
    frame = pd.DataFrame({f"c{i}": range(10) for i in range(60)})
    table = PandasDataTable(frame)
    pairs = table.correlation_pairs(limit=1000)
    involved = {p.left for p in pairs} | {p.right for p in pairs}
    assert involved <= {f"c{i}" for i in range(40)}


def test_count_analytics_without_numeric_columns(client):
    meta = _upload_csv(client, b"day,city\n2025-01-01,Astana\n2025-01-02,Almaty\n2025-01-08,Astana\n")
    groups = client.get(
        f"/api/datasets/{meta['id']}/group-by",
        params={"by": "city", "aggregation": "count"},
    )
    assert groups.status_code == 200
    assert sum(g["count"] for g in groups.json()) == 3
    series = client.get(
        f"/api/datasets/{meta['id']}/time-series",
        params={"dateColumn": "day", "aggregation": "count", "frequency": "week"},
    )
    assert series.status_code == 200
    assert sum(p["value"] for p in series.json()) == 3.0


def test_nullable_integer_column_keeps_large_ids_exact(client):
    meta = _upload_csv(client, b"id,name\n9007199254740993,alpha\n,beta\n7,gamma\n")
    overview = client.get(f"/api/datasets/{meta['id']}").json()
    kinds = {c["name"]: c["kind"] for c in overview["columns"]}
    assert kinds["id"] == "numeric"
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    values = {row["name"]: row["id"] for row in page["rows"]}
    assert values["alpha"] == "9007199254740993"
    assert values["beta"] is None
    assert values["gamma"] == 7


def test_integers_beyond_int64_stay_text(client):
    meta = _upload_csv(client, b"id,name\n9223372036854775809,alpha\n12,beta\n")
    overview = client.get(f"/api/datasets/{meta['id']}").json()
    kinds = {c["name"]: c["kind"] for c in overview["columns"]}
    assert kinds["id"] != "numeric"
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    values = {row["name"]: row["id"] for row in page["rows"]}
    assert values["alpha"] == "9223372036854775809"


def test_aggregation_without_metric_is_rejected(client):
    meta = _upload_csv(client, b"day,city\n2025-01-01,Astana\n2025-01-02,Almaty\n")
    groups = client.get(
        f"/api/datasets/{meta['id']}/group-by",
        params={"by": "city", "aggregation": "sum"},
    )
    assert groups.status_code == 400
    series = client.get(
        f"/api/datasets/{meta['id']}/time-series",
        params={"dateColumn": "day", "aggregation": "mean", "frequency": "day"},
    )
    assert series.status_code == 400


def test_leading_zero_codes_stay_text(client):
    meta = _upload_csv(client, b"zip,qty\n00123,1\n00456,2\n77000,3\n")
    overview = client.get(f"/api/datasets/{meta['id']}").json()
    kinds = {c["name"]: c["kind"] for c in overview["columns"]}
    assert kinds["zip"] != "numeric"
    assert kinds["qty"] == "numeric"
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    assert [row["zip"] for row in page["rows"]] == ["00123", "00456", "77000"]


def test_oversized_decompressed_workbook_rejected(client, monkeypatch):
    import io

    from app.infrastructure.dataframe import parser

    frame = pd.DataFrame({"a": range(100), "b": range(100)})
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    monkeypatch.setattr(parser, "MAX_DECOMPRESSED_BYTES", 64)
    response = client.post(
        "/api/datasets",
        files={"file": ("bomb.xlsx", buffer.getvalue())},
    )
    assert response.status_code == 400
    assert "expands" in response.json()["detail"]


def test_csv_export_escapes_formula_headers(client):
    meta = _upload_csv(client, b"=cmd,name\n1,alpha\n")
    response = client.post(
        f"/api/datasets/{meta['id']}/export",
        json={"format": "csv"},
    )
    text = response.content.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("'=cmd")


def test_nonscalar_datetime_filter_rejected(client):
    meta = _upload_csv(client, b"day,value\n2025-01-01,1\n2025-01-02,2\n")
    response = client.post(
        f"/api/datasets/{meta['id']}/query",
        json={"filters": [{"column": "day", "operator": "gte", "value": ["2025-01-01", "2025-01-02"]}]},
    )
    assert response.status_code == 400


def test_group_aggregate_keeps_large_integers_exact(client):
    meta = _upload_csv(client, b"grp,amount\na,9007199254740993\nb,5\n")
    response = client.get(
        f"/api/datasets/{meta['id']}/group-by",
        params={"by": "grp", "metric": "amount", "aggregation": "sum"},
    )
    assert response.status_code == 200
    values = {g["label"]: g["value"] for g in response.json()}
    assert values["a"] == "9007199254740993"
    assert values["b"] == 5


def test_utf16_csv_upload(client):
    content = "city,value\nАстана,10\nАлматы,20\n".encode("utf-16")
    meta = _upload_csv(client, content)
    assert meta["rowCount"] == 2
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    assert {row["city"] for row in page["rows"]} == {"Астана", "Алматы"}


def test_csv_export_deduplicates_escaped_headers(client):
    meta = _upload_csv(client, b"=amount,'=amount\n1,2\n")
    response = client.post(
        f"/api/datasets/{meta['id']}/export",
        json={"format": "csv"},
    )
    assert response.status_code == 200
    header = response.content.decode("utf-8-sig").splitlines()[0]
    assert "'=amount" in header
    assert "'=amount_2" in header


def test_integer_group_sum_does_not_overflow(client):
    meta = _upload_csv(
        client,
        b"grp,amount\na,5000000000000000000\na,5000000000000000000\nb,1\n",
    )
    response = client.get(
        f"/api/datasets/{meta['id']}/group-by",
        params={"by": "grp", "metric": "amount", "aggregation": "sum"},
    )
    assert response.status_code == 200
    values = {g["label"]: g["value"] for g in response.json()}
    assert values["a"] == "10000000000000000000"
    assert values["b"] == 1


def test_xlsx_export_rejects_overlong_cells(client):
    long_value = "x" * 33_000
    meta = _upload_csv(client, f"name,note\nalpha,{long_value}\n".encode())
    xlsx = client.post(f"/api/datasets/{meta['id']}/export", json={"format": "xlsx"})
    assert xlsx.status_code == 400
    assert "CSV" in xlsx.json()["detail"]
    csv_export = client.post(f"/api/datasets/{meta['id']}/export", json={"format": "csv"})
    assert csv_export.status_code == 200
    report = client.get(f"/api/datasets/{meta['id']}/report")
    assert report.status_code == 400


def test_summary_keeps_large_integer_extrema_exact(client):
    meta = _upload_csv(client, b"id,name\n9007199254740993,alpha\n5,beta\n")
    response = client.get(f"/api/datasets/{meta['id']}/summary")
    assert response.status_code == 200
    summary = next(s for s in response.json() if s["column"] == "id")
    assert summary["maximum"] == "9007199254740993"
    assert summary["minimum"] == 5


def test_xlsx_export_rejects_overlong_header(client):
    header = "h" * 33_000
    meta = _upload_csv(client, f"{header},value\n1,2\n".encode())
    response = client.post(f"/api/datasets/{meta['id']}/export", json={"format": "xlsx"})
    assert response.status_code == 400
    assert "CSV" in response.json()["detail"]


def test_dayfirst_dates_detected(client):
    meta = _upload_csv(client, b"day,value\n13/02/2025,1\n01/02/2025,2\n28/02/2025,3\n")
    overview = client.get(f"/api/datasets/{meta['id']}").json()
    kinds = {c["name"]: c["kind"] for c in overview["columns"]}
    assert kinds["day"] == "datetime"
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    assert [row["day"] for row in page["rows"]] == ["2025-02-13", "2025-02-01", "2025-02-28"]


def test_dotted_dates_parse_dayfirst(client):
    meta = _upload_csv(client, b"day,value\n01.02.2025,1\n02.02.2025,2\n03.02.2025,3\n")
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    assert [row["day"] for row in page["rows"]] == ["2025-02-01", "2025-02-02", "2025-02-03"]


def test_cp1252_csv_decoded_correctly(client):
    content = "name,city\ncafé,Genève\nnoël,Zürich\n".encode("cp1252")
    meta = _upload_csv(client, content)
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    assert {row["name"] for row in page["rows"]} == {"café", "noël"}


def test_cp1251_csv_decoded_correctly(client):
    content = "город,значение\nАстана,10\nАлматы,20\n".encode("cp1251")
    meta = _upload_csv(client, content)
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    assert {row["город"] for row in page["rows"]} == {"Астана", "Алматы"}


def test_dayfirst_evidence_beyond_first_200_rows(client):
    rows = ["day,value"] + [f"01/02/2025,{i}" for i in range(250)] + ["13/02/2025,999"]
    meta = _upload_csv(client, "\n".join(rows).encode())
    page = client.post(
        f"/api/datasets/{meta['id']}/query",
        json={"filters": [{"column": "value", "operator": "eq", "value": "999"}]},
    ).json()
    assert page["rows"][0]["day"] == "2025-02-13"
    first = client.post(f"/api/datasets/{meta['id']}/query", json={"pageSize": 1}).json()
    assert first["rows"][0]["day"] == "2025-02-01"


def test_cp1252_accent_runs_decoded_correctly(client):
    content = "name,value\nééé,1\nüüü,2\n".encode("cp1252")
    meta = _upload_csv(client, content)
    page = client.post(f"/api/datasets/{meta['id']}/query", json={}).json()
    assert {row["name"] for row in page["rows"]} == {"ééé", "üüü"}
