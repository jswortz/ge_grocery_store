"""Integration tests for Discovery Engine search API.

Tests the Discovery Engine SearchService directly (not via ADK or StreamAssist)
to verify data store ingestion and search quality.

Requires:
- Valid GCP credentials
- Provisioned Discovery Engine with data stores
- Run with: pytest -m integration tests/test_discovery_engine.py -v
"""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"


def _load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def config():
    return _load_config()


@pytest.fixture(scope="module")
def search_client():
    try:
        from google.cloud import discoveryengine_v1beta as discoveryengine
        return discoveryengine.SearchServiceClient()
    except ImportError:
        pytest.skip("google-cloud-discoveryengine not installed")


@pytest.fixture(scope="module")
def serving_config(config):
    project_id = config["project"]["id"]
    engine_id = config["project"]["engine_id"]
    return (
        f"projects/{project_id}/locations/global/collections/"
        f"default_collection/engines/{engine_id}/"
        f"servingConfigs/default_config"
    )


@pytest.fixture(scope="module")
def sop_data_store(config):
    project_id = config["project"]["id"]
    return (
        f"projects/{project_id}/locations/global/collections/"
        f"default_collection/dataStores/sop-store"
    )


@pytest.fixture(scope="module")
def brand_data_store(config):
    project_id = config["project"]["id"]
    return (
        f"projects/{project_id}/locations/global/collections/"
        f"default_collection/dataStores/brand-guidelines-store"
    )


class TestSOPDataStore:
    """Verify SOP documents are indexed and searchable."""

    def test_search_closing_procedures(self, search_client, serving_config, sop_data_store):
        from google.cloud import discoveryengine_v1beta as discoveryengine

        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query="closing procedures for frontline associates",
            page_size=5,
            data_store_specs=[
                discoveryengine.SearchRequest.DataStoreSpec(
                    data_store=sop_data_store
                )
            ],
        )
        response = search_client.search(request)
        results = list(response)
        assert len(results) > 0, "Should find closing procedure documents"

    def test_search_opening_procedures(self, search_client, serving_config, sop_data_store):
        from google.cloud import discoveryengine_v1beta as discoveryengine

        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query="opening procedures morning checklist",
            page_size=5,
            data_store_specs=[
                discoveryengine.SearchRequest.DataStoreSpec(
                    data_store=sop_data_store
                )
            ],
        )
        response = search_client.search(request)
        results = list(response)
        assert len(results) > 0, "Should find opening procedure documents"


class TestBrandGuidelinesDataStore:
    """Verify brand guideline documents are indexed and searchable."""

    def test_search_brand_colors(self, search_client, serving_config, brand_data_store):
        from google.cloud import discoveryengine_v1beta as discoveryengine

        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query="brand colors typography",
            page_size=5,
            data_store_specs=[
                discoveryengine.SearchRequest.DataStoreSpec(
                    data_store=brand_data_store
                )
            ],
        )
        response = search_client.search(request)
        results = list(response)
        assert len(results) > 0, "Should find brand guideline documents"

    def test_search_tone_of_voice(self, search_client, serving_config, brand_data_store):
        from google.cloud import discoveryengine_v1beta as discoveryengine

        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query="tone of voice messaging guidelines",
            page_size=5,
            data_store_specs=[
                discoveryengine.SearchRequest.DataStoreSpec(
                    data_store=brand_data_store
                )
            ],
        )
        response = search_client.search(request)
        results = list(response)
        assert len(results) > 0, "Should find tone of voice guidelines"
