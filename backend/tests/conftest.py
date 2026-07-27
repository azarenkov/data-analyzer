import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.presentation.container import get_container


@pytest.fixture()
def client():
    get_container.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_container.cache_clear()


@pytest.fixture()
def sample_csv() -> bytes:
    rows = ["date,region,asset,value,pnl"]
    regions = ["EU", "US", "ASIA"]
    for day in range(1, 31):
        region = regions[day % 3]
        value = 100 + day * 10
        pnl = day * 2 - 20 if day % 7 else ""
        rows.append(f"2025-01-{day:02d},{region},BTC,{value},{pnl}")
    return "\n".join(rows).encode()


@pytest.fixture()
def dataset_id(client, sample_csv) -> str:
    response = client.post(
        "/api/datasets",
        files={"file": ("sample.csv", sample_csv, "text/csv")},
    )
    assert response.status_code == 200
    return response.json()["id"]
