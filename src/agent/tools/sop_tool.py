"""SOP search tool using Vertex AI Search (Discovery Engine data store).

Provides grounded retrieval of Standard Operating Procedures from
the SOP data store.
"""

from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "settings.yaml"


def _load_datastore_id() -> str:
    """Build the full data store resource path from config."""
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    project_id = config["project"]["id"]
    # Data store ID is fixed by provisioning script
    return (
        f"projects/{project_id}/locations/global/collections/"
        f"default_collection/dataStores/sop-store"
    )


def create_sop_tool():
    """Create a VertexAiSearchTool for SOP retrieval.

    Returns a configured VertexAiSearchTool that searches the SOP data store
    for standard operating procedure documents.
    """
    from google.adk.tools import VertexAiSearchTool

    datastore_id = _load_datastore_id()
    return VertexAiSearchTool(data_store_id=datastore_id)
