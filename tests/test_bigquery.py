"""Tests for BigQuery star schema and data integrity.

Validates schema structure, data quality, and absence of
hardcoded retailer names.
"""

import pytest

# These tests require live BigQuery access
pytestmark = pytest.mark.integration

PROJECT = "wortz-project-352116"
DATASET = "ge_grocery_demo"
FQ = f"{PROJECT}.{DATASET}"

# Retailer names that must NOT appear in the data
FORBIDDEN_NAMES = ["kroger", "heb", "h-e-b", "h.e.b"]


@pytest.fixture(scope="module")
def bq_client():
    try:
        from google.cloud import bigquery
        return bigquery.Client(project=PROJECT)
    except ImportError:
        pytest.skip("google-cloud-bigquery not installed")


class TestSchemaExists:

    def test_dim_store_exists(self, bq_client):
        result = list(bq_client.query(f"SELECT COUNT(*) AS cnt FROM `{FQ}.dim_store`").result())
        assert result[0].cnt >= 3

    def test_dim_product_exists(self, bq_client):
        result = list(bq_client.query(f"SELECT COUNT(*) AS cnt FROM `{FQ}.dim_product`").result())
        assert result[0].cnt >= 15

    def test_dim_employee_exists(self, bq_client):
        result = list(bq_client.query(f"SELECT COUNT(*) AS cnt FROM `{FQ}.dim_employee`").result())
        assert result[0].cnt >= 12

    def test_dim_customer_exists(self, bq_client):
        result = list(bq_client.query(f"SELECT COUNT(*) AS cnt FROM `{FQ}.dim_customer`").result())
        assert result[0].cnt >= 30

    def test_fact_transactions_exists(self, bq_client):
        result = list(bq_client.query(f"SELECT COUNT(*) AS cnt FROM `{FQ}.fact_transactions`").result())
        assert result[0].cnt >= 10000


class TestDataQuality:

    def test_product_has_multimodal_columns(self, bq_client):
        """Verify dim_product has image_uri and description columns."""
        query = f"""
            SELECT column_name
            FROM `{PROJECT}.{DATASET}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = 'dim_product'
            AND column_name IN ('image_uri', 'description')
        """
        result = list(bq_client.query(query).result())
        column_names = {row.column_name for row in result}
        assert "image_uri" in column_names
        assert "description" in column_names

    def test_employee_role_hierarchy(self, bq_client):
        """Verify employee roles include hierarchy levels."""
        query = f"SELECT DISTINCT role FROM `{FQ}.dim_employee` ORDER BY role"
        result = list(bq_client.query(query).result())
        roles = {row.role for row in result}
        assert "Store Manager" in roles
        assert "Cashier" in roles

    def test_customer_loyalty_tiers(self, bq_client):
        """Verify loyalty tier distribution."""
        query = f"SELECT DISTINCT loyalty_tier FROM `{FQ}.dim_customer`"
        result = list(bq_client.query(query).result())
        tiers = {row.loyalty_tier for row in result}
        assert "Gold" in tiers
        assert "Silver" in tiers
        assert "Bronze" in tiers

    def test_transactions_reference_valid_stores(self, bq_client):
        """All transaction store_ids should exist in dim_store."""
        query = f"""
            SELECT COUNT(*) AS orphan_count
            FROM `{FQ}.fact_transactions` t
            LEFT JOIN `{FQ}.dim_store` s ON t.store_id = s.store_id
            WHERE s.store_id IS NULL
        """
        result = list(bq_client.query(query).result())
        assert result[0].orphan_count == 0

    def test_transactions_reference_valid_products(self, bq_client):
        query = f"""
            SELECT COUNT(*) AS orphan_count
            FROM `{FQ}.fact_transactions` t
            LEFT JOIN `{FQ}.dim_product` p ON t.product_id = p.product_id
            WHERE p.product_id IS NULL
        """
        result = list(bq_client.query(query).result())
        assert result[0].orphan_count == 0


class TestNoHardcodedNames:

    def test_store_names_clean(self, bq_client):
        """No forbidden retailer names in store data."""
        for name in FORBIDDEN_NAMES:
            query = f"""
                SELECT COUNT(*) AS cnt FROM `{FQ}.dim_store`
                WHERE LOWER(store_name) LIKE '%{name}%'
            """
            result = list(bq_client.query(query).result())
            assert result[0].cnt == 0, f"Found forbidden name '{name}' in dim_store"

    def test_product_brands_clean(self, bq_client):
        """No forbidden retailer names in product brands."""
        for name in FORBIDDEN_NAMES:
            query = f"""
                SELECT COUNT(*) AS cnt FROM `{FQ}.dim_product`
                WHERE LOWER(brand) LIKE '%{name}%'
                   OR LOWER(product_name) LIKE '%{name}%'
            """
            result = list(bq_client.query(query).result())
            assert result[0].cnt == 0, f"Found forbidden name '{name}' in dim_product"
