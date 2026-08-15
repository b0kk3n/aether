"""Guards against a regression class: a model field defined as a plain
Python @property (rather than Pydantic's @computed_field) works fine in
service-layer/unit tests but silently vanishes from actual API JSON
responses. Product.effective_status shipped this way in 0.1.0/0.1.1 and
broke status-flip feedback, checklist/main-list consistency, and produced
literal "undefined" text in the grocery view's needs-attention pills -
none of which the plain unit tests caught, since they call the service
layer directly in Python where @property still works. These tests go
through the actual FastAPI TestClient/JSON layer instead.
"""

import pytest
from fastapi.testclient import TestClient

from pantry.core.database import init_db
from pantry.core.models import ProductCreate, ProductStatus
from pantry.core.services.product_service import ProductService


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHER_PANTRY_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    from pantry.api.app import create_app

    return TestClient(create_app())


class TestProductComputedFieldsSerialize:
    def test_effective_status_present_in_list_response(self, client):
        ProductService.create(ProductCreate(name="Milk"))
        response = client.get("/api/products")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert "effective_status" in body[0]
        assert body[0]["effective_status"] == "in_stock"

    def test_effective_status_present_in_single_get(self, client):
        product = ProductService.create(ProductCreate(name="Milk"))
        response = client.get(f"/api/products/{product.id}")
        assert response.status_code == 200
        assert response.json()["effective_status"] == "in_stock"

    def test_effective_status_present_and_correct_in_needing_attention(self, client):
        product = ProductService.create(ProductCreate(name="Milk"))
        ProductService.set_status(product.id, ProductStatus.OUT)

        response = client.get("/api/products/needing-attention")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["effective_status"] == "out"

    def test_other_computed_fields_also_serialize(self, client):
        ProductService.create(ProductCreate(name="Yogurt", interval_days=3))
        response = client.get("/api/products")
        body = response.json()[0]
        # None of these are plain Pydantic fields on ProductBase/Product -
        # they only exist via @computed_field, so their presence in the
        # JSON is exactly what a bare @property would fail to produce.
        assert "next_due" in body
        assert "days_since_checked" in body
        assert "effective_interval_days" in body
        assert body["next_due"] is not None

    def test_status_patch_response_includes_effective_status(self, client):
        product = ProductService.create(ProductCreate(name="Milk"))
        response = client.patch(
            f"/api/products/{product.id}/status", json={"status": "low"}
        )
        assert response.status_code == 200
        assert response.json()["effective_status"] == "low"
