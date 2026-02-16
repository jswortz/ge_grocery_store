"""Provision an Example Store on Agent Engine for grounded code execution.

Creates an Example Store instance with curated NL->Python examples for
grocery retail analytics. These examples are automatically retrieved via
cosine similarity and injected as few-shot context when the code execution
agent handles similar queries.

Usage:
    python scripts/create_example_store.py

Requires:
    - Valid GCP credentials (gcloud auth application-default login)
    - Agent Engine access
"""

import json
import logging
from pathlib import Path

import vertexai

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = "wortz-project-352116"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://wortz-project-352116-ge-workshop"

EXAMPLES_PATH = Path(__file__).resolve().parent.parent / "data" / "example_store_examples.json"

# BQ dataset for template substitution
BQ_DATASET = "wortz-project-352116.ge_grocery_demo"


def load_examples() -> list[dict]:
    """Load examples from the JSON data file."""
    with open(EXAMPLES_PATH) as f:
        data = json.load(f)
    return data["examples"]


def create_example_store():
    """Create an Example Store and populate it with retail analytics examples."""
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
    examples = load_examples()

    logger.info("Creating Example Store for Code Execution Analytics Agent...")

    try:
        # Create the example store
        example_store = client.agent_engines.example_stores.create(
            display_name="Retail Analytics Code Examples",
            description=(
                "Curated NL-to-Python code examples for grocery retail analytics. "
                "Covers price elasticity, demand forecasting, basket analysis, "
                "cohort retention, store benchmarking, and promotional ROI."
            ),
        )
        logger.info("Example Store created: %s", example_store.name)

    except Exception as e:
        logger.error("Failed to create Example Store: %s", e)
        logger.info("This API may not be available yet. Examples saved to %s", EXAMPLES_PATH)
        return

    # Populate with examples
    created = 0
    for example in examples:
        # Substitute the dataset placeholder in code
        code = example["output"].replace("{dataset}", BQ_DATASET)

        try:
            client.agent_engines.example_stores.create_example(
                example_store_name=example_store.name,
                search_key=example["search_key"],
                output=code,
            )
            logger.info("  Added: %s", example["id"])
            created += 1
        except Exception as e:
            logger.warning("  Failed to add %s: %s", example["id"], e)

    logger.info("Done. Created %d/%d examples in Example Store.", created, len(examples))
    logger.info("Example Store resource: %s", example_store.name)

    return example_store.name


if __name__ == "__main__":
    resource = create_example_store()
    if resource:
        print(f"\nExample Store created: {resource}")
        print("Wire this into the code execution agent's configuration.")
