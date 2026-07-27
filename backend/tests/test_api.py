def test_upload_returns_metadata(client, sample_csv):
    response = client.post(
        "/api/datasets",
        files={"file": ("sample.csv", sample_csv, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "sample.csv"
    assert body["rowCount"] == 30
    assert body["columnCount"] == 5


def test_upload_rejects_unknown_extension(client):
    response = client.post(
        "/api/datasets",
        files={"file": ("sample.pdf", b"broken", "application/pdf")},
    )
    assert response.status_code == 400


def test_overview_detects_column_kinds(client, dataset_id):
    response = client.get(f"/api/datasets/{dataset_id}")
    assert response.status_code == 200
    body = response.json()
    kinds = {c["name"]: c["kind"] for c in body["columns"]}
    assert kinds["date"] == "datetime"
    assert kinds["region"] == "categorical"
    assert kinds["value"] == "numeric"
    missing = {c["name"]: c["missing"] for c in body["columns"]}
    assert missing["pnl"] > 0
    assert len(body["preview"]) == 10


def test_query_filters_sorts_and_paginates(client, dataset_id):
    response = client.post(
        f"/api/datasets/{dataset_id}/query",
        json={
            "filters": [{"column": "region", "operator": "eq", "value": "EU"}],
            "sort": [{"column": "value", "descending": True}],
            "page": 1,
            "pageSize": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 10
    assert len(body["rows"]) == 5
    values = [row["value"] for row in body["rows"]]
    assert values == sorted(values, reverse=True)
    assert all(row["region"] == "EU" for row in body["rows"])


def test_query_numeric_range_filter(client, dataset_id):
    response = client.post(
        f"/api/datasets/{dataset_id}/query",
        json={"filters": [{"column": "value", "operator": "gte", "value": 350}]},
    )
    assert response.status_code == 200
    assert all(row["value"] >= 350 for row in response.json()["rows"])


def test_query_unknown_column_fails(client, dataset_id):
    response = client.post(
        f"/api/datasets/{dataset_id}/query",
        json={"filters": [{"column": "nope", "operator": "eq", "value": 1}]},
    )
    assert response.status_code == 400


def test_summary_covers_numeric_columns(client, dataset_id):
    response = client.get(f"/api/datasets/{dataset_id}/summary")
    assert response.status_code == 200
    columns = {s["column"] for s in response.json()}
    assert columns == {"value", "pnl"}


def test_top_values(client, dataset_id):
    response = client.get(
        f"/api/datasets/{dataset_id}/top",
        params={"metric": "value", "limit": 3},
    )
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert [r["value"] for r in rows] == [400, 390, 380]


def test_group_by_sum(client, dataset_id):
    response = client.get(
        f"/api/datasets/{dataset_id}/group-by",
        params={"by": "region", "metric": "value", "aggregation": "sum"},
    )
    assert response.status_code == 200
    body = response.json()
    assert {g["label"] for g in body} == {"EU", "US", "ASIA"}
    assert sum(g["count"] for g in body) == 30


def test_time_series_by_week(client, dataset_id):
    response = client.get(
        f"/api/datasets/{dataset_id}/time-series",
        params={"dateColumn": "date", "metric": "value", "aggregation": "sum", "frequency": "week"},
    )
    assert response.status_code == 200
    points = response.json()
    assert len(points) >= 4
    assert all(p["value"] > 0 for p in points)


def test_insights_returned(client, dataset_id):
    response = client.get(f"/api/datasets/{dataset_id}/insights")
    assert response.status_code == 200
    insights = response.json()
    assert insights
    assert all({"kind", "title", "detail"} <= set(i) for i in insights)


def test_export_filtered_csv(client, dataset_id):
    response = client.post(
        f"/api/datasets/{dataset_id}/export",
        json={
            "filters": [{"column": "region", "operator": "eq", "value": "US"}],
            "format": "csv",
        },
    )
    assert response.status_code == 200
    text = response.content.decode("utf-8-sig")
    lines = [line for line in text.strip().splitlines() if line]
    assert len(lines) == 11


def test_export_report_xlsx(client, dataset_id):
    response = client.get(f"/api/datasets/{dataset_id}/report")
    assert response.status_code == 200
    assert response.content[:2] == b"PK"


def test_delete_dataset(client, dataset_id):
    assert client.delete(f"/api/datasets/{dataset_id}").status_code == 204
    assert client.get(f"/api/datasets/{dataset_id}").status_code == 404


def test_unknown_dataset_returns_404(client):
    assert client.get("/api/datasets/missing").status_code == 404
