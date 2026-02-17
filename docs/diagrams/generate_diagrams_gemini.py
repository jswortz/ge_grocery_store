"""Generate GCP-branded architecture diagrams using the gcp-diagram skill workflow.

Uses Gemini image generation to create professional architecture diagrams
styled like official Google Cloud Platform documentation.

Model priority: gemini-3-pro-image-preview > gemini-2.5-flash-image

Run: python3 docs/diagrams/generate_diagrams_gemini.py
"""

import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Model priority per gcp-diagram skill: gemini-3-pro-image-preview > gemini-2.5-flash-image
PRIMARY_MODEL = "gemini-3-pro-image-preview"
FALLBACK_MODEL = "gemini-2.5-flash-image"
IMAGE_MODEL = os.environ.get("DIAGRAM_MODEL", PRIMARY_MODEL)

PROJECT_ID = "wortz-project-352116"
LOCATION = "global"


def _generate_diagram(prompt: str, filename: str, model: str = IMAGE_MODEL):
    """Generate a single diagram using Gemini image generation."""
    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    output_path = os.path.join(OUTPUT_DIR, filename)
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            with open(output_path, "wb") as f:
                f.write(part.inline_data.data)
            print(f"  Saved: {output_path} ({len(part.inline_data.data)} bytes)")
            return output_path

    print(f"  WARNING: No image generated for {filename}")
    return None


# ── Diagram prompts (gcp-diagram skill conventions) ─────────────────────
# Each prompt includes required phrases per the skill:
#   - "professional, clean architecture diagram in the style of official Google Cloud Platform documentation"
#   - "GCP brand colors: blue (#4285F4), green (#34A853), yellow (#FBBC05), red (#EA4335)"
#   - "clean white background"
#   - "Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design"
#   - "Google Cloud logo watermark at bottom left"
#
# Color conventions from gcp-brand.md:
#   Compute/Agents: Green (#34A853)
#   Data/Analytics/BigQuery: Orange/Yellow (#F9AB00)
#   AI/ML/Vertex AI: Purple (#A142F4)
#   Storage/GCS: Yellow (#FBBC05)
#   Networking/Serverless: Teal (#12B5CB)
#   Security: Red (#EA4335)
#   Discovery Engine/Search: Blue (#4285F4)
#   Users/Clients: Red ellipse (#EA4335)
#   Config/Infrastructure: Gray (#5F6368)

DIAGRAM_1_SYSTEM_ARCHITECTURE = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.

Title: "Gemini Enterprise — Grocery Retail Workshop Architecture"

The diagram should show these components connected by clean arrows:

TOP ROW (Entry Points):
- "User" (red ellipse #EA4335, person silhouette) connected to two paths:
  1. "Frontend Web UI" (green #34A853 rounded rectangle) → "StreamAssist Client" (blue #4285F4 rounded rectangle)
  2. Direct to "Agent Engine" (green #34A853 rounded rectangle)

MIDDLE ROW (Core Platform):
- "Discovery Engine" (large blue #4285F4 rounded rectangle with light blue #E8F0FE background):
  - Contains: "grocery-workshop-engine" label
  - Connected to "sop-store" and "brand-guidelines-store" (yellow #FBBC05 folder icons)
  - "StreamAssist API" sub-component
  - "Model Armor" (red #EA4335 octagon/shield icon, label: "Content Safety Screening")

- "Vertex AI Agent Engine" (large green #34A853 rounded rectangle with light green #E6F4EA background):
  - Contains: "grocery_assistant" root agent
  - Sub-agents: "analytics_agent", "image_agent"
  - "PreloadMemoryTool" → "Memory Bank" (purple #A142F4 accent)
  - "OpenTelemetry" tracing enabled indicator

BOTTOM ROW (Backend Services):
- "BigQuery" icon with "ge_grocery_demo" label (orange #F9AB00 accent)
  - Tables: fact_transactions, dim_store, dim_product, dim_employee, dim_customer
- "Gemini Image" icon (purple #A142F4 accent)
- "Cloud Run" icon with "A2A Agent" label (teal #12B5CB accent)
- "GCS Bucket" (yellow #FBBC05 folder icon)

SIDE (Config):
- "config/settings.yaml" (gray #5F6368 note icon) feeding into all components

Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design.
All shapes must be rounded rectangles, circles, or ellipses — never hexagons.
Landscape orientation. Google Cloud logo watermark at bottom left.
"""

DIAGRAM_2_AGENT_ARCHITECTURE = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.

Title: "ADK Multi-Agent Architecture"
Subtitle: "DiscoveryEngineSearchTool + FunctionTool Sub-Agents"

Show a hierarchical agent architecture:

TOP: "User Query" (red ellipse #EA4335)

CENTER: "grocery_assistant" (large blue #4285F4 rounded rectangle, labeled "Root Agent / LlmAgent"):
- Model: gemini-3-pro-preview
- Tool: DiscoveryEngineSearchTool (searches sop-store and brand-guidelines-store)
- Tool: PreloadMemoryTool (loads cross-session memories)

LEFT BRANCH: "analytics_agent" (orange #F9AB00 rounded rectangle, labeled "Sub-Agent"):
  - Model: gemini-3-flash-preview
  - Tool: query_grocery_data (FunctionTool)
  - Connects to: BigQuery (orange #F9AB00 cylinder)

RIGHT BRANCH: "image_agent" (purple #A142F4 rounded rectangle, labeled "Sub-Agent"):
  - Model: gemini-3-flash-preview
  - Tool: generate_product_image (FunctionTool)
  - Connects to: Gemini Image (purple #A142F4 cylinder)

SEARCH BRANCH from Root:
- DiscoveryEngineSearchTool connects to:
  - sop-store (blue #4285F4 cylinder)
  - brand-guidelines-store (blue #4285F4 cylinder)
  - Both filtered by data_store_specs

Show transfer_to_agent arrows between root and sub-agents (bold arrows).
Show return arrows (dashed) for results flowing back.
Include a design note box: "DiscoveryEngineSearchTool used instead of VertexAiSearchTool to avoid conflict with transfer_to_agent function tools"

Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design.
All shapes must be rounded rectangles, circles, or ellipses — never hexagons.
Landscape orientation. Google Cloud logo watermark at bottom left.
"""

DIAGRAM_3_DATA_FLOW = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.

Title: "Request Processing Flow"
Subtitle: "From User Query Through Agent Orchestration to Grounded Response"

Show a top-to-bottom flow with numbered steps:

Step 1: "User Sends Query" (red ellipse #EA4335 at top)
- Examples: "What are closing procedures?", "Top selling products?", "Generate image for Nano Banana"

Step 2: "Request Entry Points" (gray #5F6368 rounded rectangle):
- Path A: StreamAssist Client → Discovery Engine StreamAssist API
- Path B: Agent Engine REST API → Vertex AI Agent Engine

Step 3: "Processing / Orchestration" (green #34A853 rounded rectangle):
- grocery_assistant analyzes intent
- Routes to appropriate handler

Step 4 (parallel paths, color-coded):
- Path A: Discovery Engine Search (blue #4285F4): SearchTool → data_store_specs filter → sop-store/brand-store → Grounded Results
- Path B: BigQuery Analytics (orange #F9AB00): analytics_agent → query_grocery_data → SQL execution → Structured Results
- Path C: Image Generation (purple #A142F4): image_agent → prompt construction → Gemini Image → Generated Image

Step 5: "Response Assembly" (green #34A853 rounded rectangle)

Step 6: "User Receives Grounded Response" (red ellipse #EA4335 at bottom)

Clean flowchart style with color-coded paths.
Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design.
All shapes must be rounded rectangles, circles, or ellipses — never hexagons.
Google Cloud logo watermark at bottom left.
"""

DIAGRAM_4_STAR_SCHEMA = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.

Title: "BigQuery Star Schema"
Subtitle: "wortz-project-352116.ge_grocery_demo"

Show a star schema with orange (#F9AB00) accents:

CENTER: "fact_transactions" (large orange #F9AB00 rounded rectangle with bold border):
- 12,000+ rows
- Columns: transaction_id, transaction_ts, store_id, employee_id, product_id, quantity, unit_price, total_amount, payment_method, customer_id

SURROUNDING DIMENSIONS (connected by FK arrows):

Top-left: "dim_store" (deep yellow #F9AB00 rounded rectangle):
- 3 rows
- Columns: store_name, city, state, zip_code, square_feet, open_date

Top-right: "dim_product" (deep yellow #F9AB00 rounded rectangle):
- 20 rows
- Columns: product_name, category, subcategory, brand, unit_price, unit_cost, image_uri, description

Bottom-left: "dim_employee" (deep yellow #F9AB00 rounded rectangle):
- 15 rows
- Columns: first_name, last_name, role, store_id, hire_date
- Note: "Role Hierarchy: Store Mgr > Dept Mgr > Cashier > Stock Clerk"

Bottom-right: "dim_customer" (deep yellow #F9AB00 rounded rectangle):
- 40 rows
- Columns: first_name, last_name, email, loyalty_tier, home_store_id, points_balance
- Note: "Tiers: Gold | Silver | Bronze"

Show FK arrows with column names. Cross-dimension edges: dim_employee.store_id → dim_store, dim_customer.home_store_id → dim_store (dashed).

BigQuery icon at top.
Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design.
All shapes must be rounded rectangles, circles, or ellipses — never hexagons.
Google Cloud logo watermark at bottom left.
"""

DIAGRAM_5_MCP_INTEGRATION = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.

Title: "MCP Integration Architecture"
Subtitle: "genai-toolbox for BigQuery"

Show a LEFT-TO-RIGHT flow:

LEFT: "ADK Agent" (green #34A853 rounded rectangle):
- mcp_grocery_analyst
- gemini-3-pro-preview
- "LLM generates arbitrary SQL"
- Contains: McpToolset with StdioConnectionParams

CENTER: "genai-toolbox" (blue #4285F4 rounded rectangle, labeled "MCP Server / subprocess"):
- Binary: genai-toolbox --prebuilt bigquery --stdio
- Tools: execute_sql, list_table_ids, get_table_info, get_dataset_info, list_dataset_ids, search_catalog, ask_data_insights, forecast, analyze_contribution

RIGHT: "BigQuery API" (orange #F9AB00 cylinder):
- ge_grocery_demo
- 12K+ transactions, 5 tables

Connections:
- Agent to genai-toolbox: "MCP over stdio" (bold blue #4285F4 arrow)
- genai-toolbox to BigQuery: "REST API" (bold orange #F9AB00 arrow)

Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design.
All shapes must be rounded rectangles, circles, or ellipses — never hexagons.
Landscape orientation. Google Cloud logo watermark at bottom left.
"""

DIAGRAM_6_DEPLOYMENT = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.

Title: "Deployment Architecture"
Subtitle: "Agent Engine + Cloud Run + Discovery Engine"

Show:

TOP: "Client" (red ellipse #EA4335) — Frontend UI / REST API / A2A Agent

MIDDLE ROW (deployment targets):
1. "Vertex AI Agent Engine" (green #34A853 rounded rectangle, us-central1):
   - ReasoningEngine ID: 4433744355123003392
   - ADK Agent (grocery_assistant)
   - PreloadMemoryTool → Memory Bank (purple #A142F4 sub-box)
   - DiscoveryEngineSearchTool
   - analytics_agent (BigQuery)
   - image_agent (Gemini Image)
   - OpenTelemetry: Enabled

2. "Cloud Run" (teal #12B5CB rounded rectangle, us-central1):
   - A2A Agent: grocery-a2a-agent
   - /.well-known/agent.json
   - /a2a endpoint
   - Delegates to Agent Engine

3. "Discovery Engine" (blue #4285F4 rounded rectangle, global):
   - grocery-workshop-engine
   - Model Armor (red #EA4335 shield icon)

BOTTOM ROW (backend services):
- BigQuery (orange #F9AB00): ge_grocery_demo
- Gemini Image (purple #A142F4): gemini-3-pro-image-preview
- GCS (yellow #FBBC05): brand guidelines + SOPs

Show connections between all components.
Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design.
All shapes must be rounded rectangles, circles, or ellipses — never hexagons.
Landscape orientation. Google Cloud logo watermark at bottom left.
"""

DIAGRAM_7_MEMORY_MODEL_ARMOR = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.

Title: "Memory Bank & Model Armor"
Subtitle: "Cross-Session Personalization + Content Safety"

Split the diagram into two halves:

LEFT HALF — "Memory Bank" (purple #A142F4 theme):
- "User (Browser)" (red ellipse #EA4335) with localStorage: vf_user_id
- Arrow to "ADK Agent" (green #34A853 rounded rectangle) with user_id
- Agent connects to "PreloadMemoryTool" (purple #A142F4 component box)
- PreloadMemoryTool connects to "VertexAiMemoryBankService" (purple #A142F4 cylinder)
  - Scoped to agent_engine_id
  - GenerateMemories: auto-extract facts from conversation
  - CreateMemory: agent-controlled writes
- Show flow: user_id → load memories → personalized response

RIGHT HALF — "Model Armor" (red #EA4335 theme):
- "Discovery Engine" (blue #4285F4 rounded rectangle) at top
- Connected to "Model Armor Template" (red #EA4335 octagon/shield):
  - Template: grocery-workshop-armor-us
  - Applied to both user prompts and model responses
  - Filters:
    - RAI Harm (hate, violence, sexual, dangerous) — MEDIUM_AND_ABOVE
    - Prompt Injection & Jailbreak — MEDIUM_AND_ABOVE
    - Sensitive Data Protection (PII) — ENABLED
    - Malicious URI Detection — ENABLED
  - Failure Mode: FAIL_OPEN

Show the flow of prompts being screened before reaching the model and
responses being screened before reaching the user.

Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design.
All shapes must be rounded rectangles, circles, or ellipses — never hexagons.
Google Cloud logo watermark at bottom left.
"""


DIAGRAMS = [
    ("01_system_architecture.png", DIAGRAM_1_SYSTEM_ARCHITECTURE, "System Architecture"),
    ("02_agent_architecture.png", DIAGRAM_2_AGENT_ARCHITECTURE, "Agent Architecture"),
    ("03_data_flow.png", DIAGRAM_3_DATA_FLOW, "Data Flow"),
    ("04_star_schema.png", DIAGRAM_4_STAR_SCHEMA, "Star Schema"),
    ("05_mcp_integration.png", DIAGRAM_5_MCP_INTEGRATION, "MCP Integration"),
    ("06_deployment.png", DIAGRAM_6_DEPLOYMENT, "Deployment Architecture"),
    ("07_memory_model_armor.png", DIAGRAM_7_MEMORY_MODEL_ARMOR, "Memory Bank & Model Armor"),
]


def main():
    print(f"Generating GCP-branded diagrams (primary: {PRIMARY_MODEL}, fallback: {FALLBACK_MODEL})")
    print(f"Using model: {IMAGE_MODEL}")
    print(f"Output directory: {OUTPUT_DIR}\n")

    success = 0
    for i, (filename, prompt, label) in enumerate(DIAGRAMS, 1):
        print(f"[{i}/{len(DIAGRAMS)}] Generating {label}...")
        try:
            result = _generate_diagram(prompt, filename)
            if result:
                success += 1
        except Exception as e:
            print(f"  ERROR with {IMAGE_MODEL}: {e}")
            # Try fallback model
            if IMAGE_MODEL != FALLBACK_MODEL:
                print(f"  Trying fallback model: {FALLBACK_MODEL}")
                try:
                    result = _generate_diagram(prompt, filename, model=FALLBACK_MODEL)
                    if result:
                        success += 1
                except Exception as e2:
                    print(f"  Fallback also failed: {e2}")

    print(f"\nGenerated {success}/{len(DIAGRAMS)} diagrams successfully.")


if __name__ == "__main__":
    main()
