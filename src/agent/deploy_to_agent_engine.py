"""Deploy the main grocery assistant to Vertex AI Agent Engine.

Self-contained deployment script — builds the agent inline to avoid
cloudpickle module-not-found errors in the Agent Engine runtime.

Usage:
    cd src && python -m agent.deploy_to_agent_engine
"""

import os

import vertexai
from vertexai import agent_engines

PROJECT_ID = os.environ.get("PROJECT_ID", "wortz-project-352116")
PROJECT_NUMBER = os.environ.get("PROJECT_NUMBER", "679926387543")
LOCATION = os.environ.get("AE_LOCATION", "us-central1")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "gs://wortz-project-352116-ge-workshop")

# Hardcoded config for Agent Engine deployment
_RETAILER_NAME = os.environ.get("RETAILER_NAME", "ValueFresh Market")
_ADK_MODEL = os.environ.get("ADK_MODEL", "gemini-3-pro-preview")
_ADK_FAST = os.environ.get("ADK_FAST", "gemini-3-flash-preview")
_BQ_PROJECT = os.environ.get("BQ_PROJECT", "wortz-project-352116")
_BQ_DATASET = os.environ.get("BQ_DATASET", "ge_grocery_demo")
_ENGINE_ID = os.environ.get("ENGINE_ID", "grocery-workshop-engine")
_GCS_BUCKET = os.environ.get("GCS_BUCKET", "wortz-project-352116-ge-workshop")
_IMAGEN_MODEL = os.environ.get("IMAGEN_MODEL", "gemini-3-pro-image-preview")
# Simulator Agent Engine resource ID for A2A delegation
_SIMULATOR_AE_ID = os.environ.get("SIMULATOR_AE_ID", "1774087300184014848")


def find_agent_by_display_name(display_name: str) -> str:
    """Find reasoning engine by display name."""
    agent_filter_query = f'display_name="{display_name}"'
    agent_list = agent_engines.list(filter=agent_filter_query)
    for deployed_agent in agent_list:
        return deployed_agent.resource_name
    return ""


def _build_agent():
    """Build the full grocery assistant agent inline for deployment."""
    from google.adk.agents import LlmAgent
    from google.adk.planners import BuiltInPlanner
    from google.adk.tools import FunctionTool
    from google.genai.types import ThinkingConfig

    planner = BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    )

    # --- BigQuery tool (inline) ---
    fq = f"{_BQ_PROJECT}.{_BQ_DATASET}"
    _SQL_PATTERNS = {
        "top_products": f"SELECT p.product_name, SUM(t.quantity) AS total_qty, SUM(t.total_amount) AS total_revenue FROM `{fq}.fact_transactions` t JOIN `{fq}.dim_product` p ON t.product_id = p.product_id GROUP BY p.product_name ORDER BY total_revenue DESC LIMIT {{limit}}",
        "store_revenue": f"SELECT s.store_name, SUM(t.total_amount) AS total_revenue, COUNT(*) AS num_transactions FROM `{fq}.fact_transactions` t JOIN `{fq}.dim_store` s ON t.store_id = s.store_id GROUP BY s.store_name ORDER BY total_revenue DESC",
        "daily_trends": f"SELECT DATE(t.transaction_ts) AS date, SUM(t.total_amount) AS daily_revenue, COUNT(*) AS transactions FROM `{fq}.fact_transactions` t GROUP BY date ORDER BY date DESC LIMIT {{limit}}",
        "employee_performance": f"SELECT e.first_name || ' ' || e.last_name AS employee_name, e.role, SUM(t.total_amount) AS total_sales FROM `{fq}.fact_transactions` t JOIN `{fq}.dim_employee` e ON t.employee_id = e.employee_id GROUP BY employee_name, e.role ORDER BY total_sales DESC LIMIT {{limit}}",
        "category_breakdown": f"SELECT p.category, SUM(t.quantity) AS total_qty, SUM(t.total_amount) AS total_revenue FROM `{fq}.fact_transactions` t JOIN `{fq}.dim_product` p ON t.product_id = p.product_id GROUP BY p.category ORDER BY total_revenue DESC",
        "customer_loyalty": f"SELECT c.loyalty_tier, COUNT(DISTINCT c.customer_id) AS num_customers, SUM(t.total_amount) AS total_revenue FROM `{fq}.fact_transactions` t JOIN `{fq}.dim_customer` c ON t.customer_id = c.customer_id GROUP BY c.loyalty_tier ORDER BY total_revenue DESC",
        "payment_methods": f"SELECT payment_method, COUNT(*) AS num_transactions, SUM(total_amount) AS total_revenue FROM `{fq}.fact_transactions` GROUP BY payment_method ORDER BY total_revenue DESC",
    }

    def query_grocery_data(query_type: str, limit: int = 10) -> dict:
        """Run a BigQuery query against the grocery retail dataset.

        Args:
            query_type: Type of query - one of: top_products, store_revenue,
                daily_trends, employee_performance, category_breakdown,
                customer_loyalty, payment_methods
            limit: Max rows to return (default 10).

        Returns:
            Dict with status, query, and results.
        """
        from google.cloud import bigquery

        sql_template = _SQL_PATTERNS.get(query_type)
        if not sql_template:
            return {
                "status": "error",
                "message": f"Unknown query_type: {query_type}. Available: {list(_SQL_PATTERNS.keys())}",
            }
        sql = sql_template.format(limit=limit)
        try:
            client = bigquery.Client(project=_BQ_PROJECT)
            rows = list(client.query(sql).result())
            results = [dict(row.items()) for row in rows]
            return {"status": "success", "query": sql, "results": results, "row_count": len(results)}
        except Exception as e:
            return {"status": "error", "message": str(e), "query": sql}

    bq_tool = FunctionTool(func=query_grocery_data)

    # --- Image gen tool (inline) ---
    def generate_product_image(
        product_name: str,
        style_description: str = "professional product photography, bright natural lighting, clean background",
        brand_colors: str = "green (#2e7d32) and white, with gold (#f9a825) accents",
    ) -> dict:
        """Generate a product image based on brand guidelines.

        Args:
            product_name: Name of the product.
            style_description: Visual style instructions.
            brand_colors: Brand color palette.

        Returns:
            Dict with status and message.
        """
        import base64
        import hashlib

        prompt = (
            f"Professional product photo of '{product_name}' for {_RETAILER_NAME} grocery store. "
            f"Style: {style_description}. Brand colors: {brand_colors}. "
            f"The product should look appetizing and premium."
        )
        try:
            import vertexai as vai
            from vertexai.generative_models import GenerativeModel

            vai.init(project=PROJECT_ID, location="global")
            model = GenerativeModel(_IMAGEN_MODEL)
            response = model.generate_content(
                prompt, generation_config={"response_modalities": ["IMAGE", "TEXT"]}
            )
            image_bytes = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    break

            if image_bytes:
                from google.cloud import storage

                blob_name = (
                    f"generated_images/{product_name.lower().replace(' ', '_')}_"
                    f"{hashlib.md5(image_bytes[:1024]).hexdigest()[:8]}.png"
                )
                storage_client = storage.Client(project=PROJECT_ID)
                bucket = storage_client.bucket(_GCS_BUCKET)
                blob = bucket.blob(blob_name)
                blob.upload_from_string(image_bytes, content_type="image/png")
                proxy_url = f"/api/images/{blob_name}"
                return {
                    "status": "success",
                    "message": f"Generated product image for '{product_name}'.\n\n![{product_name}]({proxy_url})",
                    "image_uri": f"gs://{_GCS_BUCKET}/{blob_name}",
                    "image_url": proxy_url,
                }
            return {"status": "no_images", "message": "No image generated. Try a different prompt."}
        except Exception as e:
            return {"status": "error", "message": f"Image generation failed: {e}"}

    image_tool = FunctionTool(func=generate_product_image)

    # --- Discovery Engine search as FunctionTool ---
    # NOTE: We use a plain FunctionTool instead of DiscoveryEngineSearchTool
    # because the latter contains gRPC Channel objects that cannot be
    # deep-copied during agent_engines.create() serialization.
    _search_engine_id = (
        f"projects/{PROJECT_ID}/locations/global/collections/"
        f"default_collection/engines/{_ENGINE_ID}"
    )

    def search_documents(query: str, data_store: str = "sop-store") -> dict:
        """Search SOPs and brand guidelines using Discovery Engine.

        Args:
            query: The search query text.
            data_store: Which data store to search. One of: sop-store, brand-guidelines-store.

        Returns:
            Dict with search results including document snippets.
        """
        from google.cloud import discoveryengine_v1beta as discoveryengine

        ds_path = (
            f"projects/{PROJECT_ID}/locations/global/collections/"
            f"default_collection/dataStores/{data_store}"
        )
        serving_config = f"{_search_engine_id}/servingConfigs/default_search"

        try:
            client = discoveryengine.SearchServiceClient()
            request = discoveryengine.SearchRequest(
                serving_config=serving_config,
                query=query,
                page_size=5,
                data_store_specs=[
                    discoveryengine.SearchRequest.DataStoreSpec(
                        data_store=ds_path,
                    )
                ],
            )
            response = client.search(request=request)
            results = []
            for result in response.results:
                doc = result.document
                title = doc.derived_struct_data.get("title", "Untitled")
                snippets = []
                for snippet in doc.derived_struct_data.get("snippets", []):
                    snippet_text = snippet.get("snippet", "")
                    if snippet_text:
                        snippets.append(snippet_text)
                extractive = []
                for seg in doc.derived_struct_data.get("extractive_segments", []):
                    seg_text = seg.get("content", "")
                    if seg_text:
                        extractive.append(seg_text)
                results.append({
                    "title": title,
                    "snippets": snippets,
                    "extractive_segments": extractive,
                })
            return {"status": "success", "results": results, "result_count": len(results)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    search_tool = FunctionTool(func=search_documents)

    # --- Root tools ---
    root_tools = [search_tool]

    # PreloadMemoryTool
    try:
        from google.adk.tools.preload_memory_tool import PreloadMemoryTool
        root_tools.append(PreloadMemoryTool())
    except ImportError:
        pass

    # NOTE: GoogleSearchTool is excluded from Agent Engine deployment
    # because it has a version-incompatible 'model' attribute in the
    # Agent Engine runtime. It works fine in local ADK mode.

    # --- Sub-agents ---
    analytics_agent = LlmAgent(
        name="analytics_agent",
        model=_ADK_FAST,
        planner=planner,
        instruction=(
            f"You are the data analytics specialist for {_RETAILER_NAME}. "
            "Use the query_grocery_data tool to answer questions about sales, "
            "products, stores, customers, and employees. Present results clearly "
            "with specific numbers."
        ),
        description="Answers data questions by querying BigQuery.",
        tools=[bq_tool],
    )

    image_agent = LlmAgent(
        name="image_agent",
        model=_ADK_FAST,
        planner=planner,
        instruction=(
            f"You are the product imagery specialist for {_RETAILER_NAME}. "
            "Use the generate_product_image tool to create product photos. "
            "IMPORTANT: When the tool returns successfully, always include the "
            "markdown image from the 'message' field in your response exactly "
            "as returned (e.g., ![Product Name](/api/images/...)) so the user "
            "can see the generated image inline."
        ),
        description="Generates product images following brand guidelines.",
        tools=[image_tool],
    )

    # --- Root orchestrator ---
    instruction = f"""You are an AI assistant for {_RETAILER_NAME}, a grocery retail company.
You help associates, managers, and stakeholders with:

1. **Standard Operating Procedures** — Retrieve and explain SOPs for frontline associates.
   Use the SOP search tool to find relevant procedures grounded in official documents.

2. **Brand-Compliant Marketing Content** — Generate materials aligned with brand guidelines.
   Always search brand guidelines first to ensure tone, colors, and messaging align.

3. **Product Information & Analytics** — Answer questions about products, sales trends, and
   store performance using BigQuery analytics. Provide data-driven insights.

4. **Product Image Generation** — Create product imagery following brand guidelines.

5. **Memory & Personalization** — Use memory bank to personalize responses across sessions.

6. **Market Intelligence** — Use Google Search for current retail trends and market data.

Guidelines:
- Always ground your responses in data from the tools available to you.
- When citing SOPs, reference the specific document and section.
- For marketing content, apply the brand's tone: warm, friendly, clear, and positive.
- For analytics, include specific numbers and cite the data source.
- Be concise and actionable in your responses.
"""

    agent = LlmAgent(
        name="sop_agent",
        model=_ADK_MODEL,
        planner=planner,
        instruction=instruction,
        description=(
            "AI assistant for grocery retail operations. Searches SOPs and "
            "brand guidelines, and delegates to sub-agents for analytics "
            "and image generation."
        ),
        tools=root_tools,
        sub_agents=[analytics_agent, image_agent],
    )

    return agent


def deploy():
    """Deploy the main grocery assistant to Agent Engine."""
    print("=" * 80)
    print("DEPLOYING GROCERY ASSISTANT TO AGENT ENGINE")
    print("=" * 80)

    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    agent = _build_agent()
    display_name = "Grocery Retail Assistant"

    app = agent_engines.AdkApp(
        agent=agent,
        app_name="sop_agent_app",
        enable_tracing=True,
    )

    existing = find_agent_by_display_name(display_name)

    if existing:
        print(f"Deleting existing deployment: {existing}")
        agent_engines.delete(existing, force=True)
        print("  Deleted.")

    env_vars = {
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
        "GOOGLE_CLOUD_LOCATION": "global",  # Gemini 3 models require global endpoint
    }

    print("Creating new deployment...")
    remote_app = agent_engines.create(
        agent_engine=app,
        display_name=display_name,
        requirements=[
            "google-adk>=1.19.0",
            "google-cloud-bigquery>=3.0.0",
            "google-cloud-aiplatform",
            "google-cloud-discoveryengine",
            "google-cloud-storage",
            "pyyaml>=6.0",
        ],
        env_vars=env_vars,
    )
    print(f"Deployed: {remote_app.resource_name}")
    return remote_app.resource_name


if __name__ == "__main__":
    resource_name = deploy()
    print(f"\nGrocery Assistant deployed: {resource_name}")
