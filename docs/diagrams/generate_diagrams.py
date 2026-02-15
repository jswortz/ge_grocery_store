"""Generate system architecture diagrams for the ge_grocery_store repository.

Uses graphviz to create three publication-quality diagrams:
1. Overall System Architecture
2. ADK Multi-Agent Architecture
3. Data Flow / Request Processing

Run: python3 docs/diagrams/generate_diagrams.py
"""

import graphviz
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def diagram_1_overall_architecture():
    """Generate the overall system architecture diagram."""
    dot = graphviz.Digraph(
        "system_architecture",
        format="png",
        engine="dot",
        graph_attr={
            "rankdir": "TB",
            "bgcolor": "#f8f9fa",
            "fontname": "Helvetica",
            "fontsize": "14",
            "pad": "0.5",
            "nodesep": "0.6",
            "ranksep": "0.8",
            "label": "System Architecture: Gemini Enterprise Grocery Retail Workshop",
            "labelloc": "t",
            "labeljust": "c",
            "fontsize": "24",
            "fontcolor": "#1a1a2e",
            "dpi": "600",
            "size": "20,15",
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "14",
            "style": "filled",
            "shape": "box",
            "margin": "0.3,0.15",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "11",
            "color": "#555555",
        },
    )

    # --- Gemini Enterprise (Discovery Engine) cluster ---
    with dot.subgraph(name="cluster_discovery") as c:
        c.attr(
            label="Gemini Enterprise (Discovery Engine)",
            style="filled,rounded",
            color="#1565c0",
            fillcolor="#e3f2fd",
            fontcolor="#0d47a1",
            fontsize="16",
            penwidth="2",
        )
        c.node(
            "engine",
            "Discovery Engine App\ngrocery-workshop-engine\n(Global Deployment)",
            fillcolor="#bbdefb",
            color="#1565c0",
            shape="component",
        )
        c.node(
            "sop_store",
            "sop-store\nSOP PDFs (GCS)",
            fillcolor="#c8e6c9",
            color="#2e7d32",
            shape="cylinder",
        )
        c.node(
            "brand_store",
            "brand-guidelines-store\nBrand Guide PDFs (GCS)",
            fillcolor="#c8e6c9",
            color="#2e7d32",
            shape="cylinder",
        )
        c.node(
            "streamassist_api",
            "StreamAssist REST API\nv1alpha streamAssist endpoint\n(Search + Conversational AI)",
            fillcolor="#bbdefb",
            color="#1565c0",
            shape="box3d",
        )
        c.edge("sop_store", "engine", style="dashed", color="#2e7d32")
        c.edge("brand_store", "engine", style="dashed", color="#2e7d32")
        c.edge("engine", "streamassist_api", color="#1565c0")

    # --- GCS Bucket ---
    dot.node(
        "gcs",
        "GCS Bucket\nwortz-project-352116-ge-workshop\nsops/ | brand_guidelines/",
        fillcolor="#fff9c4",
        color="#f57f17",
        shape="folder",
    )
    dot.edge("gcs", "sop_store", label="indexed", style="dashed", color="#f57f17")
    dot.edge("gcs", "brand_store", label="indexed", style="dashed", color="#f57f17")

    # --- StreamAssist Client ---
    dot.node(
        "streamassist_client",
        "StreamAssist Client\nsrc/client/stream_assist.py\n\nOAuth2 | Session Mgmt\nRetry Logic | Response Parsing",
        fillcolor="#e8eaf6",
        color="#283593",
        shape="box",
    )
    dot.edge(
        "streamassist_client",
        "streamassist_api",
        label="REST API\nPOST streamAssist",
        color="#283593",
        penwidth="2",
    )

    # --- ADK Agent on Agent Engine cluster ---
    with dot.subgraph(name="cluster_agent") as c:
        c.attr(
            label="ADK Agent on Vertex AI Agent Engine",
            style="filled,rounded",
            color="#2e7d32",
            fillcolor="#e8f5e9",
            fontcolor="#1b5e20",
            fontsize="16",
            penwidth="2",
        )
        c.node(
            "agent_engine",
            "Vertex AI Agent Engine\nID: 3323818153208709120\nus-central1",
            fillcolor="#a5d6a7",
            color="#2e7d32",
            shape="box3d",
        )
        c.node(
            "root_agent",
            "Root Agent: grocery_assistant\ngemini-2.5-flash\nDiscoveryEngineSearchTool",
            fillcolor="#c8e6c9",
            color="#2e7d32",
        )
        c.node(
            "analytics_agent",
            "analytics_agent\ngemini-2.5-flash\nquery_grocery_data\nFunctionTool",
            fillcolor="#dcedc8",
            color="#558b2f",
        )
        c.node(
            "image_agent",
            "image_agent\ngemini-2.5-flash\ngenerate_product_image\nFunctionTool",
            fillcolor="#dcedc8",
            color="#558b2f",
        )
        c.edge("agent_engine", "root_agent", color="#2e7d32")
        c.edge(
            "root_agent",
            "analytics_agent",
            label="transfer_to_agent",
            color="#558b2f",
            style="bold",
        )
        c.edge(
            "root_agent",
            "image_agent",
            label="transfer_to_agent",
            color="#558b2f",
            style="bold",
        )

    # --- BigQuery Star Schema cluster ---
    with dot.subgraph(name="cluster_bq") as c:
        c.attr(
            label="BigQuery Star Schema",
            style="filled,rounded",
            color="#e65100",
            fillcolor="#fff3e0",
            fontcolor="#bf360c",
            fontsize="16",
            penwidth="2",
        )
        c.node(
            "bq_dataset",
            "Dataset: ge_grocery_demo\nwortz-project-352116",
            fillcolor="#ffe0b2",
            color="#e65100",
            shape="box3d",
        )
        c.node(
            "fact_tx",
            "fact_transactions\n12,000+ rows",
            fillcolor="#ffcc80",
            color="#e65100",
            shape="cylinder",
        )
        c.node(
            "dim_store",
            "dim_store\n3 stores",
            fillcolor="#ffcc80",
            color="#e65100",
            shape="cylinder",
        )
        c.node(
            "dim_product",
            "dim_product\n20 products",
            fillcolor="#ffcc80",
            color="#e65100",
            shape="cylinder",
        )
        c.node(
            "dim_employee",
            "dim_employee\n15 employees",
            fillcolor="#ffcc80",
            color="#e65100",
            shape="cylinder",
        )
        c.node(
            "dim_customer",
            "dim_customer\n40 customers\nGold/Silver/Bronze",
            fillcolor="#ffcc80",
            color="#e65100",
            shape="cylinder",
        )
        c.edge("bq_dataset", "fact_tx", color="#e65100", style="dashed")
        c.edge("fact_tx", "dim_store", color="#e65100", style="dotted")
        c.edge("fact_tx", "dim_product", color="#e65100", style="dotted")
        c.edge("fact_tx", "dim_employee", color="#e65100", style="dotted")
        c.edge("fact_tx", "dim_customer", color="#e65100", style="dotted")

    # --- Vertex AI Imagen ---
    dot.node(
        "imagen",
        "Vertex AI Imagen\nimagen-3.0-generate-002\nus-central1\n\nProduct Photography\nbase64 PNG output",
        fillcolor="#f3e5f5",
        color="#6a1b9a",
        shape="box3d",
    )

    # --- Memory Bank ---
    dot.node(
        "memory_bank",
        "Memory Bank\nPreloadMemoryTool\n(Cross-session memory per user_id)",
        fillcolor="#e8eaf6",
        color="#3f51b5",
        shape="box3d",
    )
    dot.edge(
        "root_agent",
        "memory_bank",
        label="per-user\nmemory",
        color="#3f51b5",
        style="dashed",
        penwidth="1.5",
    )

    # --- Model Armor ---
    dot.node(
        "model_armor",
        "Model Armor\ngrocery-workshop-armor\n\nRAI Harm Filter\nPI & Jailbreak Filter\nSDP (PII) Filter\nMalicious URI Filter",
        fillcolor="#fce4ec",
        color="#c62828",
        shape="octagon",
    )
    dot.edge(
        "streamassist_api",
        "model_armor",
        label="screens\nprompts & responses",
        color="#c62828",
        style="dashed",
        penwidth="1.5",
    )

    # --- A2A Agent (Cloud Run) ---
    dot.node(
        "a2a_agent",
        "A2A Agent\nCloud Run\n\nAgentCard + /a2a endpoint\nInter-agent communication",
        fillcolor="#e0f2f1",
        color="#00695c",
        shape="box3d",
    )
    dot.edge(
        "a2a_agent",
        "root_agent",
        label="A2A protocol",
        color="#00695c",
        penwidth="1.5",
    )

    # --- Simulator ---
    dot.node(
        "simulator",
        "Shopper Simulator\n\nWorld-model simulation\nEndcap merchandising A/B test\nConcurrent shopper agents",
        fillcolor="#fff3e0",
        color="#e65100",
        shape="house",
    )
    dot.edge(
        "simulator",
        "bq_dataset",
        label="reads store/\nproduct data",
        color="#e65100",
        style="dashed",
    )

    # --- Config ---
    dot.node(
        "config",
        "config/settings.yaml\nRetailer: ValueFresh Market\nProject: wortz-project-352116",
        fillcolor="#eceff1",
        color="#455a64",
        shape="note",
    )

    # --- User ---
    dot.node(
        "user",
        "User\n(Associate / Manager / Stakeholder)",
        fillcolor="#fce4ec",
        color="#c62828",
        shape="ellipse",
    )

    # --- Cross-cluster edges ---
    dot.edge(
        "root_agent",
        "engine",
        label="DiscoveryEngine\nSearchTool",
        color="#1565c0",
        penwidth="2",
    )
    dot.edge(
        "analytics_agent",
        "bq_dataset",
        label="google-cloud-bigquery\nSQL queries",
        color="#e65100",
        penwidth="2",
    )
    dot.edge(
        "image_agent",
        "imagen",
        label="vertexai SDK\nImageGenerationModel",
        color="#6a1b9a",
        penwidth="2",
    )
    dot.edge("user", "streamassist_client", color="#c62828", penwidth="2")
    dot.edge(
        "user",
        "agent_engine",
        label="Agent Engine\nstreamQuery API",
        color="#c62828",
        penwidth="2",
    )
    dot.edge(
        "config",
        "root_agent",
        style="dotted",
        label="runtime config",
        color="#455a64",
    )

    output_path = os.path.join(OUTPUT_DIR, "01_system_architecture")
    dot.render(output_path, cleanup=True)
    print(f"Diagram 1 saved to {output_path}.png")


def diagram_2_agent_architecture():
    """Generate the ADK multi-agent architecture diagram."""
    dot = graphviz.Digraph(
        "agent_architecture",
        format="png",
        engine="dot",
        graph_attr={
            "rankdir": "TB",
            "bgcolor": "#fafafa",
            "fontname": "Helvetica",
            "pad": "0.5",
            "nodesep": "0.7",
            "ranksep": "0.9",
            "label": "ADK Multi-Agent Architecture\nDiscoveryEngineSearchTool + FunctionTool Sub-Agents",
            "labelloc": "t",
            "labeljust": "c",
            "fontsize": "24",
            "fontcolor": "#1a1a2e",
            "dpi": "600",
            "size": "20,15",
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "14",
            "style": "filled",
            "shape": "box",
            "margin": "0.3,0.2",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "12",
            "color": "#555555",
        },
    )

    # User query input
    dot.node(
        "user_query",
        "User Query\n(Natural Language)",
        fillcolor="#fce4ec",
        color="#c62828",
        shape="ellipse",
    )

    # --- Root Agent cluster ---
    with dot.subgraph(name="cluster_root") as c:
        c.attr(
            label="Root Agent",
            style="filled,rounded,bold",
            color="#1565c0",
            fillcolor="#e3f2fd",
            fontcolor="#0d47a1",
            fontsize="16",
            penwidth="2.5",
        )
        c.node(
            "root",
            'grocery_assistant\nModel: gemini-2.5-flash\nType: LlmAgent (root orchestrator)\n\nInstruction: get_main_agent_instruction()\n"AI assistant for grocery retail operations"',
            fillcolor="#bbdefb",
            color="#1565c0",
            shape="box",
            penwidth="2",
        )

    # --- DiscoveryEngineSearchTool cluster ---
    with dot.subgraph(name="cluster_search") as c:
        c.attr(
            label="DiscoveryEngineSearchTool (FunctionTool subclass)",
            style="filled,rounded",
            color="#0277bd",
            fillcolor="#e1f5fe",
            fontcolor="#01579b",
            fontsize="12",
            penwidth="2",
        )
        c.node(
            "search_tool",
            "DiscoveryEngineSearchTool\n\nsearch_engine_id:\nprojects/{project_id}/locations/global/\ncollections/default_collection/\nengines/grocery-workshop-engine",
            fillcolor="#b3e5fc",
            color="#0277bd",
            shape="component",
        )
        c.node(
            "data_store_specs",
            "data_store_specs\n(filters search to GCS stores only)",
            fillcolor="#b3e5fc",
            color="#0277bd",
            shape="box",
        )
        c.node(
            "sop_store",
            "sop-store\n\nClosing procedures\nOpening checklists\nSafety protocols",
            fillcolor="#c8e6c9",
            color="#2e7d32",
            shape="cylinder",
        )
        c.node(
            "brand_store",
            "brand-guidelines-store\n\nColors (#2e7d32, #f9a825)\nTone of voice\nTypography",
            fillcolor="#c8e6c9",
            color="#2e7d32",
            shape="cylinder",
        )
        c.edge("search_tool", "data_store_specs", color="#0277bd")
        c.edge("data_store_specs", "sop_store", color="#2e7d32", style="bold")
        c.edge("data_store_specs", "brand_store", color="#2e7d32", style="bold")

    # --- Analytics Sub-Agent cluster ---
    with dot.subgraph(name="cluster_analytics") as c:
        c.attr(
            label="Analytics Subsystem (Sub-Agent)",
            style="filled,rounded",
            color="#e65100",
            fillcolor="#fff3e0",
            fontcolor="#bf360c",
            fontsize="12",
            penwidth="2",
        )
        c.node(
            "analytics",
            'analytics_agent\nModel: gemini-2.5-flash\nType: LlmAgent (sub-agent)\n\n"Data analytics specialist"\n"Answers data questions by querying\nthe BigQuery star schema"',
            fillcolor="#ffe0b2",
            color="#e65100",
            shape="box",
            penwidth="2",
        )
        c.node(
            "bq_tool",
            "query_grocery_data\n(FunctionTool)\n\nInput: question (str)\nOutput: status, sql, results, row_count",
            fillcolor="#ffcc80",
            color="#e65100",
            shape="component",
        )
        c.node(
            "bq",
            "BigQuery\nge_grocery_demo\n\nfact_transactions | dim_store\ndim_product | dim_employee\ndim_customer",
            fillcolor="#ffab91",
            color="#bf360c",
            shape="cylinder",
        )
        c.edge("analytics", "bq_tool", color="#e65100", penwidth="2")
        c.edge("bq_tool", "bq", label="SQL via\nbigquery.Client", color="#bf360c", penwidth="1.5")

    # --- Image Sub-Agent cluster ---
    with dot.subgraph(name="cluster_image") as c:
        c.attr(
            label="Image Generation Subsystem (Sub-Agent)",
            style="filled,rounded",
            color="#6a1b9a",
            fillcolor="#f3e5f5",
            fontcolor="#4a148c",
            fontsize="12",
            penwidth="2",
        )
        c.node(
            "image",
            'image_agent\nModel: gemini-2.5-flash\nType: LlmAgent (sub-agent)\n\n"Product imagery specialist"\n"Generates product images following\nbrand guidelines"',
            fillcolor="#e1bee7",
            color="#6a1b9a",
            shape="box",
            penwidth="2",
        )
        c.node(
            "img_tool",
            "generate_product_image\n(FunctionTool)\n\nInputs: product_name,\nstyle_description, brand_colors\nOutput: image_base64, mime_type",
            fillcolor="#ce93d8",
            color="#6a1b9a",
            shape="component",
        )
        c.node(
            "imagen",
            "Vertex AI Imagen\nimagen-3.0-generate-002\n\nPNG output, 1:1 aspect\nus-central1",
            fillcolor="#ba68c8",
            color="#4a148c",
            fontcolor="white",
            shape="cylinder",
        )
        c.edge("image", "img_tool", color="#6a1b9a", penwidth="2")
        c.edge(
            "img_tool",
            "imagen",
            label="ImageGenerationModel\n.generate_images()",
            color="#4a148c",
            penwidth="1.5",
        )

    # --- Edges ---
    dot.edge("user_query", "root", color="#c62828", penwidth="2")
    dot.edge("root", "search_tool", label="Direct tool call\n(SOP/Brand queries)", color="#0277bd", penwidth="2")
    dot.edge(
        "root",
        "analytics",
        label="transfer_to_agent\n(Data/Analytics queries)",
        color="#e65100",
        penwidth="2.5",
        style="bold",
    )
    dot.edge(
        "root",
        "image",
        label="transfer_to_agent\n(Image generation queries)",
        color="#6a1b9a",
        penwidth="2.5",
        style="bold",
    )

    # Return edges
    dot.edge("analytics", "root", label="results back", color="#e65100", style="dashed")
    dot.edge("image", "root", label="image back", color="#6a1b9a", style="dashed")

    # --- Memory Bank tool in root agent ---
    dot.node(
        "memory_tool",
        "PreloadMemoryTool\n(loads memories per user_id\nat start of each turn)",
        fillcolor="#e8eaf6",
        color="#3f51b5",
        shape="component",
    )
    dot.edge("root", "memory_tool", label="auto-load\nmemories", color="#3f51b5", style="dashed")

    # --- Model Armor layer ---
    dot.node(
        "model_armor",
        "Model Armor\ngrocery-workshop-armor\n\nScreens prompts & responses\nRAI | PI/Jailbreak | SDP | URI",
        fillcolor="#fce4ec",
        color="#c62828",
        shape="octagon",
    )
    dot.edge(
        "user_query",
        "model_armor",
        label="user prompt\nscreened",
        color="#c62828",
        style="dashed",
    )
    dot.edge(
        "model_armor",
        "root",
        color="#c62828",
        style="dashed",
    )

    # Design note
    dot.node(
        "note",
        "Design Note: DiscoveryEngineSearchTool is used\ninstead of VertexAiSearchTool because the latter's\nbuilt-in Gemini retrieval tool conflicts with\ntransfer_to_agent function tools from sub-agents.",
        fillcolor="#fff9c4",
        color="#f57f17",
        shape="note",
        fontsize="9",
    )

    output_path = os.path.join(OUTPUT_DIR, "02_agent_architecture")
    dot.render(output_path, cleanup=True)
    print(f"Diagram 2 saved to {output_path}.png")


def diagram_3_data_flow():
    """Generate the request processing / data flow diagram."""
    dot = graphviz.Digraph(
        "data_flow",
        format="png",
        engine="dot",
        graph_attr={
            "rankdir": "TB",
            "bgcolor": "#f5f5f5",
            "fontname": "Helvetica",
            "pad": "0.5",
            "nodesep": "0.5",
            "ranksep": "0.7",
            "label": "Request Processing Flow\nFrom User Query Through Agent Orchestration to Grounded Response",
            "labelloc": "t",
            "labeljust": "c",
            "fontsize": "24",
            "fontcolor": "#1a1a2e",
            "dpi": "600",
            "size": "20,25",
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "13",
            "style": "filled",
            "shape": "box",
            "margin": "0.25,0.15",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "11",
            "color": "#555555",
        },
    )

    # Step 1: User
    dot.node(
        "user",
        "Step 1: User Sends Query\n\nAssociate / Manager / Stakeholder\n\nExamples:\n\"What are the closing procedures?\"\n\"Show me top selling products\"\n\"Generate image for Nano Banana Pro Bar\"\n\"What are our brand colors?\"",
        fillcolor="#fce4ec",
        color="#c62828",
        shape="box",
        penwidth="2",
    )

    # Step 2: Entry Points
    with dot.subgraph(name="cluster_entry") as c:
        c.attr(
            label="Step 2: Request Entry Points",
            style="filled,rounded",
            color="#455a64",
            fillcolor="#eceff1",
            fontcolor="#263238",
            fontsize="12",
            penwidth="2",
        )
        c.node(
            "path_a",
            "Path A: StreamAssist Client\nsrc/client/stream_assist.py\n\nPOST v1alpha streamAssist\nOAuth2 Bearer Token\nSession Management\nExponential Backoff Retry",
            fillcolor="#bbdefb",
            color="#1565c0",
        )
        c.node(
            "path_b",
            "Path B: Agent Engine REST API\n\nPOST /v1/projects/.../\nreasoningEngines/{id}:streamQuery\n\nVertex AI Agent Engine\nus-central1",
            fillcolor="#c8e6c9",
            color="#2e7d32",
        )

    # Step 3: Root Agent
    dot.node(
        "root_agent",
        "Step 3: Root Agent Orchestration\n\ngrocery_assistant (gemini-2.5-flash)\nAnalyzes intent and decides routing:\n\n  SOP/Brand query -> DiscoveryEngineSearchTool\n  Data/Analytics query -> transfer_to_agent -> analytics_agent\n  Image query -> transfer_to_agent -> image_agent",
        fillcolor="#dcedc8",
        color="#33691e",
        shape="box",
        penwidth="2.5",
    )

    # Step 4: Three paths
    with dot.subgraph(name="cluster_4a") as c:
        c.attr(
            label="Step 4A: Discovery Engine Search",
            style="filled,rounded",
            color="#1565c0",
            fillcolor="#e3f2fd",
            fontcolor="#0d47a1",
            fontsize="11",
            penwidth="2",
        )
        c.node(
            "search_tool",
            "DiscoveryEngineSearchTool\nSearchService REST API",
            fillcolor="#bbdefb",
            color="#1565c0",
        )
        c.node(
            "search_filter",
            "data_store_specs filter:\nsop-store | brand-guidelines-store",
            fillcolor="#90caf9",
            color="#1565c0",
        )
        c.node(
            "search_result",
            "Grounded Results\nCitations + Doc References\nRelevant Excerpts",
            fillcolor="#64b5f6",
            color="#0d47a1",
            fontcolor="white",
        )
        c.edge("search_tool", "search_filter", color="#1565c0")
        c.edge("search_filter", "search_result", label="indexed\nGCS PDFs", color="#1565c0")

    with dot.subgraph(name="cluster_4b") as c:
        c.attr(
            label="Step 4B: BigQuery Analytics",
            style="filled,rounded",
            color="#e65100",
            fillcolor="#fff3e0",
            fontcolor="#bf360c",
            fontsize="11",
            penwidth="2",
        )
        c.node(
            "analytics_agent",
            "analytics_agent\ntransfer_to_agent",
            fillcolor="#ffe0b2",
            color="#e65100",
        )
        c.node(
            "sql_gen",
            "query_grocery_data\nPattern-match -> SQL Generation",
            fillcolor="#ffcc80",
            color="#e65100",
        )
        c.node(
            "bq_exec",
            "BigQuery Execution\nge_grocery_demo\nfact_transactions + dimensions",
            fillcolor="#ffab91",
            color="#bf360c",
            shape="cylinder",
        )
        c.node(
            "bq_result",
            "Structured Results\nstatus, sql, results[], row_count",
            fillcolor="#ff8a65",
            color="#bf360c",
            fontcolor="white",
        )
        c.edge("analytics_agent", "sql_gen", color="#e65100")
        c.edge("sql_gen", "bq_exec", label="SQL", color="#bf360c")
        c.edge("bq_exec", "bq_result", color="#bf360c")

    with dot.subgraph(name="cluster_4c") as c:
        c.attr(
            label="Step 4C: Image Generation",
            style="filled,rounded",
            color="#6a1b9a",
            fillcolor="#f3e5f5",
            fontcolor="#4a148c",
            fontsize="11",
            penwidth="2",
        )
        c.node(
            "image_agent",
            "image_agent\ntransfer_to_agent",
            fillcolor="#e1bee7",
            color="#6a1b9a",
        )
        c.node(
            "prompt_build",
            "Prompt Construction\nproduct_name + style +\nbrand_colors + retailer",
            fillcolor="#ce93d8",
            color="#6a1b9a",
        )
        c.node(
            "imagen",
            "Vertex AI Imagen\nimagen-3.0-generate-002",
            fillcolor="#ba68c8",
            color="#4a148c",
            fontcolor="white",
            shape="cylinder",
        )
        c.node(
            "img_result",
            "Generated Image\nbase64 PNG + metadata",
            fillcolor="#ab47bc",
            color="#4a148c",
            fontcolor="white",
        )
        c.edge("image_agent", "prompt_build", color="#6a1b9a")
        c.edge("prompt_build", "imagen", color="#4a148c")
        c.edge("imagen", "img_result", color="#4a148c")

    # Step 5: Response Assembly
    dot.node(
        "response_assembly",
        "Step 5: Response Assembly\n\nRoot agent formulates final response:\n  SOP: document citations + section refs\n  Brand: tone, colors, guidelines\n  Analytics: specific numbers + data source\n  Images: generated product image",
        fillcolor="#dcedc8",
        color="#33691e",
        shape="box",
        penwidth="2.5",
    )

    # Step 6: Response Delivery
    with dot.subgraph(name="cluster_response") as c:
        c.attr(
            label="Step 6: Response Delivery",
            style="filled,rounded",
            color="#455a64",
            fillcolor="#eceff1",
            fontcolor="#263238",
            fontsize="12",
            penwidth="2",
        )
        c.node(
            "resp_a",
            "Path A: StreamAssist\n\nStreamAssistClient._parse_response()\n-> StreamAssistResponse\n  replies (text + role)\n  thoughts (reasoning)\n  session info",
            fillcolor="#bbdefb",
            color="#1565c0",
        )
        c.node(
            "resp_b",
            "Path B: Agent Engine\n\nJSON lines stream\ncontent.parts[].text\nvia streamQuery API",
            fillcolor="#c8e6c9",
            color="#2e7d32",
        )

    # User receives response
    dot.node(
        "user_out",
        "User Receives\nGrounded Response",
        fillcolor="#fce4ec",
        color="#c62828",
        shape="ellipse",
        penwidth="2",
    )

    # --- Edges connecting the flow ---
    dot.edge("user", "path_a", label="Path A", color="#1565c0", penwidth="2")
    dot.edge("user", "path_b", label="Path B", color="#2e7d32", penwidth="2")
    dot.edge("path_a", "root_agent", color="#1565c0", penwidth="1.5")
    dot.edge("path_b", "root_agent", color="#2e7d32", penwidth="1.5")

    dot.edge(
        "root_agent",
        "search_tool",
        label="SOP/Brand query",
        color="#1565c0",
        penwidth="2",
    )
    dot.edge(
        "root_agent",
        "analytics_agent",
        label="Data query\ntransfer_to_agent",
        color="#e65100",
        penwidth="2",
    )
    dot.edge(
        "root_agent",
        "image_agent",
        label="Image query\ntransfer_to_agent",
        color="#6a1b9a",
        penwidth="2",
    )

    dot.edge("search_result", "response_assembly", color="#1565c0", penwidth="1.5")
    dot.edge("bq_result", "response_assembly", color="#e65100", penwidth="1.5")
    dot.edge("img_result", "response_assembly", color="#6a1b9a", penwidth="1.5")

    dot.edge("response_assembly", "resp_a", label="Path A", color="#1565c0", penwidth="1.5")
    dot.edge("response_assembly", "resp_b", label="Path B", color="#2e7d32", penwidth="1.5")
    dot.edge("resp_a", "user_out", color="#c62828", penwidth="2")
    dot.edge("resp_b", "user_out", color="#c62828", penwidth="2")

    output_path = os.path.join(OUTPUT_DIR, "03_data_flow")
    dot.render(output_path, cleanup=True)
    print(f"Diagram 3 saved to {output_path}.png")


def _common_attrs(label, dpi="600"):
    """Shared graph attributes for consistent style across diagrams."""
    return {
        "rankdir": "TB",
        "bgcolor": "#f8f9fa",
        "fontname": "Helvetica",
        "pad": "0.5",
        "nodesep": "0.6",
        "ranksep": "0.8",
        "label": label,
        "labelloc": "t",
        "labeljust": "c",
        "fontsize": "24",
        "fontcolor": "#1a1a2e",
        "dpi": dpi,
        "size": "20,15",
    }


def diagram_4_star_schema():
    """Generate the BigQuery star schema diagram."""
    dot = graphviz.Digraph(
        "star_schema",
        format="png",
        engine="dot",
        graph_attr={
            **_common_attrs("BigQuery Star Schema\nwortz-project-352116.ge_grocery_demo"),
            "ranksep": "1.0",
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "13",
            "style": "filled",
            "shape": "box",
            "margin": "0.3,0.2",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "11",
            "color": "#555555",
        },
    )

    # Fact table
    dot.node(
        "fact",
        "fact_transactions\n12,000+ rows\n\ntransaction_id | transaction_ts\nstore_id | employee_id | product_id\nquantity | unit_price | total_amount\npayment_method | customer_id",
        fillcolor="#ffcc80",
        color="#e65100",
        shape="box3d",
        penwidth="2.5",
    )

    # Dimension tables
    for name, rows, cols, extra in [
        ("dim_store", "3 rows", "store_name | city | state\nzip_code | square_feet | open_date", ""),
        ("dim_product", "20 rows", "product_name | category | brand\nunit_price | unit_cost\nimage_uri | description", ""),
        ("dim_employee", "15 rows", "first_name | last_name | role\nstore_id | hire_date", "\n\nRole Hierarchy:\nStore Mgr > Dept Mgr >\nCashier > Stock Clerk"),
        ("dim_customer", "40 rows", "first_name | last_name | email\nloyalty_tier | home_store_id\npoints_balance | signup_date", "\n\nLoyalty Tiers:\nGold | Silver | Bronze"),
    ]:
        dot.node(
            name,
            f"{name}\n{rows}\n\n{cols}{extra}",
            fillcolor="#ffe0b2",
            color="#e65100",
            shape="cylinder",
            penwidth="1.5",
        )

    # FK edges
    for dim, fk in [
        ("dim_store", "store_id"),
        ("dim_product", "product_id"),
        ("dim_employee", "employee_id"),
        ("dim_customer", "customer_id"),
    ]:
        dot.edge("fact", dim, label=fk, color="#e65100", penwidth="2", style="bold")

    # Cross-dimension edges
    dot.edge("dim_employee", "dim_store", label="store_id (FK)", color="#bf360c", style="dashed")
    dot.edge("dim_customer", "dim_store", label="home_store_id (FK)", color="#bf360c", style="dashed")

    output_path = os.path.join(OUTPUT_DIR, "04_star_schema")
    dot.render(output_path, cleanup=True)
    print(f"Diagram 4 saved to {output_path}.png")


def diagram_5_mcp_integration():
    """Generate the MCP integration architecture diagram."""
    dot = graphviz.Digraph(
        "mcp_integration",
        format="png",
        engine="dot",
        graph_attr={
            **_common_attrs("MCP Integration Architecture\ngenai-toolbox for BigQuery"),
            "rankdir": "LR",
            "size": "20,8",
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "14",
            "style": "filled",
            "shape": "box",
            "margin": "0.3,0.2",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "12",
            "color": "#555555",
        },
    )

    # ADK Agent
    with dot.subgraph(name="cluster_adk") as c:
        c.attr(
            label="ADK Agent",
            style="filled,rounded",
            color="#2e7d32",
            fillcolor="#e8f5e9",
            fontsize="14",
            penwidth="2",
        )
        c.node(
            "agent",
            "mcp_grocery_analyst\ngemini-2.5-flash\n\nLLM generates\narbitrary SQL",
            fillcolor="#c8e6c9",
            color="#2e7d32",
            penwidth="2",
        )
        c.node(
            "mcp_toolset",
            "McpToolset\n\nStdioConnectionParams\nStdioServerParameters",
            fillcolor="#a5d6a7",
            color="#2e7d32",
            shape="component",
        )
        c.edge("agent", "mcp_toolset", color="#2e7d32", penwidth="2")

    # genai-toolbox
    with dot.subgraph(name="cluster_toolbox") as c:
        c.attr(
            label="genai-toolbox (subprocess)",
            style="filled,rounded",
            color="#1565c0",
            fillcolor="#e3f2fd",
            fontsize="14",
            penwidth="2",
        )
        c.node(
            "toolbox",
            "genai-toolbox binary\n--prebuilt bigquery\n--stdio",
            fillcolor="#bbdefb",
            color="#1565c0",
            shape="box3d",
            penwidth="2",
        )
        c.node(
            "tools",
            "9 BigQuery Tools\n\nexecute_sql | list_table_ids\nget_table_info | get_dataset_info\nlist_dataset_ids | search_catalog\nask_data_insights | forecast\nanalyze_contribution",
            fillcolor="#90caf9",
            color="#1565c0",
        )
        c.edge("toolbox", "tools", color="#1565c0")

    # BigQuery
    dot.node(
        "bq",
        "BigQuery API\n\nge_grocery_demo\n12K+ transactions\n5 tables",
        fillcolor="#ffcc80",
        color="#e65100",
        shape="cylinder",
        penwidth="2",
    )

    # Edges
    dot.edge("mcp_toolset", "toolbox", label="MCP over stdio", color="#1565c0", penwidth="2.5", style="bold")
    dot.edge("tools", "bq", label="REST API", color="#e65100", penwidth="2.5", style="bold")

    output_path = os.path.join(OUTPUT_DIR, "05_mcp_integration")
    dot.render(output_path, cleanup=True)
    print(f"Diagram 5 saved to {output_path}.png")


def diagram_6_deployment():
    """Generate the deployment architecture diagram."""
    dot = graphviz.Digraph(
        "deployment",
        format="png",
        engine="dot",
        graph_attr={
            **_common_attrs("Deployment Architecture\nAgent Engine + Cloud Run + Discovery Engine"),
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "13",
            "style": "filled",
            "shape": "box",
            "margin": "0.3,0.2",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "11",
            "color": "#555555",
        },
    )

    # Client
    dot.node(
        "client",
        "Client\n(Frontend UI / REST API / A2A Agent)",
        fillcolor="#fce4ec",
        color="#c62828",
        shape="ellipse",
        penwidth="2",
    )

    # Agent Engine
    with dot.subgraph(name="cluster_ae") as c:
        c.attr(
            label="Vertex AI Agent Engine (us-central1)",
            style="filled,rounded",
            color="#2e7d32",
            fillcolor="#e8f5e9",
            fontsize="16",
            penwidth="2",
        )
        c.node(
            "re",
            "ReasoningEngine\nID: 3323818153208709120\n\nADK Agent (grocery_assistant)\n+ PreloadMemoryTool\n+ DiscoveryEngineSearchTool\n+ analytics_agent (BigQuery)\n+ image_agent (Imagen)\n\nOpenTelemetry: Enabled",
            fillcolor="#c8e6c9",
            color="#2e7d32",
            shape="box3d",
            penwidth="2",
        )
        c.node(
            "memory",
            "Memory Bank\n(VertexAiMemoryBankService)\nPer-user cross-session memory",
            fillcolor="#e8eaf6",
            color="#3f51b5",
            shape="box3d",
        )
        c.edge("re", "memory", label="per user_id", color="#3f51b5", style="dashed")

    # Cloud Run
    with dot.subgraph(name="cluster_cr") as c:
        c.attr(
            label="Cloud Run (us-central1)",
            style="filled,rounded",
            color="#00695c",
            fillcolor="#e0f2f1",
            fontsize="16",
            penwidth="2",
        )
        c.node(
            "a2a",
            "A2A Agent\ngrocery-a2a-agent\n\n/.well-known/agent.json\n/a2a endpoint\nuvicorn + Starlette",
            fillcolor="#b2dfdb",
            color="#00695c",
            shape="box3d",
            penwidth="2",
        )

    # Backend services
    dot.node("de", "Discovery Engine\n(global)\ngrocery-workshop-engine", fillcolor="#bbdefb", color="#1565c0", shape="box3d")
    dot.node("ma", "Model Armor\ngrocery-workshop-armor\n(us-central1)", fillcolor="#fce4ec", color="#c62828", shape="octagon")
    dot.node("bq", "BigQuery\nge_grocery_demo", fillcolor="#ffcc80", color="#e65100", shape="cylinder")
    dot.node("imagen", "Vertex AI Imagen\nimagen-3.0-generate-002", fillcolor="#e1bee7", color="#6a1b9a", shape="cylinder")

    # Edges
    dot.edge("client", "re", label="streamQuery API", color="#2e7d32", penwidth="2")
    dot.edge("client", "a2a", label="A2A protocol", color="#00695c", penwidth="2")
    dot.edge("re", "de", label="search", color="#1565c0", penwidth="1.5")
    dot.edge("de", "ma", label="screens I/O", color="#c62828", style="dashed", penwidth="1.5")
    dot.edge("re", "bq", label="SQL", color="#e65100", penwidth="1.5")
    dot.edge("re", "imagen", label="generate", color="#6a1b9a", penwidth="1.5")
    dot.edge("a2a", "re", label="delegates to\nAgent Engine", color="#2e7d32", style="dashed")

    output_path = os.path.join(OUTPUT_DIR, "06_deployment")
    dot.render(output_path, cleanup=True)
    print(f"Diagram 6 saved to {output_path}.png")


def diagram_7_config_system():
    """Generate the configuration system diagram."""
    dot = graphviz.Digraph(
        "config_system",
        format="png",
        engine="dot",
        graph_attr={
            **_common_attrs("Configuration System\nconfig/settings.yaml + Environment Variable Overrides"),
            "size": "18,12",
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "13",
            "style": "filled",
            "shape": "box",
            "margin": "0.3,0.2",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "11",
            "color": "#555555",
        },
    )

    # Config file
    dot.node(
        "yaml",
        "config/settings.yaml\n\nretailer.name\nproject.id | project.engine_id\nbigquery.project | bigquery.dataset\nmemory.enabled | memory.location\nmodel_armor.enabled | model_armor.template_id",
        fillcolor="#eceff1",
        color="#455a64",
        shape="note",
        penwidth="2",
    )

    # Env vars
    dot.node(
        "env",
        "Environment Variables\n(Agent Engine deployment)\n\nRETAILER_NAME\nPROJECT_ID | ENGINE_ID\nBQ_PROJECT | BQ_DATASET\nADK_MODEL",
        fillcolor="#fff9c4",
        color="#f57f17",
        shape="parallelogram",
        penwidth="2",
    )

    # _load_config()
    dot.node(
        "loader",
        "_load_config()\n\n1. Read settings.yaml\n2. Apply env var overrides\n3. Return merged config dict",
        fillcolor="#dcedc8",
        color="#33691e",
        shape="box3d",
        penwidth="2.5",
    )

    # Consumers
    consumers = [
        ("bq_tool", "bq_tool.py\nBigQuery SQL", "#ffe0b2", "#e65100"),
        ("image_gen", "image_gen_tool.py\nImagen prompts", "#e1bee7", "#6a1b9a"),
        ("system_prompts", "system_prompts.py\nRetailer name\nin instructions", "#bbdefb", "#1565c0"),
        ("stream_assist", "stream_assist.py\nAPI endpoints\nProject config", "#e8eaf6", "#283593"),
        ("mcp_agent", "mcp_agent/agent.py\nBQ project\nSchema context", "#c8e6c9", "#2e7d32"),
        ("a2a_agent", "a2a_agent/agent.py\nAll config\nfor A2A serving", "#b2dfdb", "#00695c"),
    ]
    for name, label, fill, border in consumers:
        dot.node(name, label, fillcolor=fill, color=border, shape="component")

    # Edges
    dot.edge("yaml", "loader", label="file read", color="#455a64", penwidth="2")
    dot.edge("env", "loader", label="overrides", color="#f57f17", penwidth="2", style="dashed")
    for name, _, _, _ in consumers:
        dot.edge("loader", name, color="#33691e", penwidth="1.5")

    output_path = os.path.join(OUTPUT_DIR, "07_config_system")
    dot.render(output_path, cleanup=True)
    print(f"Diagram 7 saved to {output_path}.png")


def diagram_8_memory_model_armor():
    """Generate the Memory Bank + Model Armor diagram."""
    dot = graphviz.Digraph(
        "memory_model_armor",
        format="png",
        engine="dot",
        graph_attr={
            **_common_attrs("Memory Bank & Model Armor\nCross-Session Personalization + Content Safety"),
            "size": "20,12",
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "13",
            "style": "filled",
            "shape": "box",
            "margin": "0.3,0.2",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "11",
            "color": "#555555",
        },
    )

    # User
    dot.node(
        "user",
        "User (Browser)\n\nlocalStorage: vf_user_id\ncrypto.randomUUID()",
        fillcolor="#fce4ec",
        color="#c62828",
        shape="ellipse",
        penwidth="2",
    )

    # Memory Bank
    with dot.subgraph(name="cluster_memory") as c:
        c.attr(
            label="Memory Bank (Agent Engine)",
            style="filled,rounded",
            color="#3f51b5",
            fillcolor="#e8eaf6",
            fontsize="14",
            penwidth="2",
        )
        c.node(
            "preload",
            "PreloadMemoryTool\n\nAuto-loads memories\nat start of each turn\nbased on user_id",
            fillcolor="#c5cae9",
            color="#3f51b5",
            shape="component",
        )
        c.node(
            "mem_service",
            "VertexAiMemoryBankService\n(scoped to agent_engine_id)\n\nGenerateMemories: auto-extract facts\nCreateMemory: agent-controlled writes",
            fillcolor="#9fa8da",
            color="#283593",
            shape="box3d",
        )
        c.edge("preload", "mem_service", color="#3f51b5", penwidth="2")

    # Model Armor
    with dot.subgraph(name="cluster_armor") as c:
        c.attr(
            label="Model Armor (Discovery Engine)",
            style="filled,rounded",
            color="#c62828",
            fillcolor="#fce4ec",
            fontsize="14",
            penwidth="2",
        )
        c.node(
            "template",
            "Template: grocery-workshop-armor\n\nApplied to both:\n- User prompt (input)\n- Model response (output)",
            fillcolor="#ef9a9a",
            color="#c62828",
            shape="component",
        )
        c.node(
            "filters",
            "Filters (MEDIUM_AND_ABOVE):\n\nRAI Harm (hate, violence, sexual)\nPrompt Injection & Jailbreak\nSensitive Data Protection (PII)\nMalicious URI Detection",
            fillcolor="#ffcdd2",
            color="#c62828",
        )
        c.node(
            "fail_mode",
            "Failure Mode: FAIL_OPEN\n(pass through if unavailable)",
            fillcolor="#ffebee",
            color="#c62828",
            shape="note",
        )
        c.edge("template", "filters", color="#c62828")
        c.edge("template", "fail_mode", style="dotted", color="#c62828")

    # ADK Agent
    dot.node(
        "agent",
        "ADK Agent\ngrocery_assistant\n\nPersonalized responses\nusing recalled memories",
        fillcolor="#c8e6c9",
        color="#2e7d32",
        shape="box3d",
        penwidth="2",
    )

    # Discovery Engine
    dot.node(
        "de",
        "Discovery Engine\ngrocery-workshop-engine\n\nStreamAssist | SearchService",
        fillcolor="#bbdefb",
        color="#1565c0",
        shape="box3d",
    )

    # Edges
    dot.edge("user", "agent", label="user_id +\nmessage", color="#c62828", penwidth="2")
    dot.edge("agent", "preload", label="load memories\nfor user_id", color="#3f51b5", penwidth="2")
    dot.edge("user", "de", label="StreamAssist\nquery", color="#1565c0", penwidth="2")
    dot.edge("de", "template", label="screens\nI/O", color="#c62828", penwidth="2", style="dashed")

    output_path = os.path.join(OUTPUT_DIR, "08_memory_model_armor")
    dot.render(output_path, cleanup=True)
    print(f"Diagram 8 saved to {output_path}.png")


if __name__ == "__main__":
    print(f"Generating diagrams in {OUTPUT_DIR}/\n")
    diagram_1_overall_architecture()
    diagram_2_agent_architecture()
    diagram_3_data_flow()
    diagram_4_star_schema()
    diagram_5_mcp_integration()
    diagram_6_deployment()
    diagram_7_config_system()
    diagram_8_memory_model_armor()
    print(f"\nAll diagrams generated successfully.")
