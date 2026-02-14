"""BigQuery analytics tool for the ADK agent.

Provides read-only query access to the grocery retail star schema
for answering data-driven questions about sales, products, stores,
and customers.
"""

import logging

logger = logging.getLogger(__name__)


def _load_config():
    from ..agent import _load_config as _agent_load_config
    return _agent_load_config()


def query_grocery_data(question: str) -> dict:
    """Query the grocery retail BigQuery star schema.

    Translates a natural language question into a SQL query against the
    star schema and returns the results. The schema includes:
    - fact_transactions: transaction_id, transaction_ts, store_id, employee_id,
      product_id, quantity, unit_price, total_amount, payment_method, customer_id
    - dim_store: store_id, store_name, city, state, zip_code, square_feet, open_date
    - dim_product: product_id, product_name, category, subcategory, brand,
      unit_price, unit_cost, image_uri, description
    - dim_employee: employee_id, first_name, last_name, role, store_id, hire_date
    - dim_customer: customer_id, first_name, last_name, email, phone,
      loyalty_tier, home_store_id, signup_date, points_balance

    Args:
        question: Natural language question about grocery data
                  (e.g., "What are the top 5 selling products by revenue?")

    Returns:
        Dict with 'status', 'question', 'sql' (if generated), and 'results'.
    """
    config = _load_config()
    project_id = config["bigquery"]["project"]
    dataset = config["bigquery"]["dataset"]
    full_dataset = f"{project_id}.{dataset}"

    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=project_id)

        # Build a context-aware prompt for SQL generation
        schema_context = f"""
You are a SQL expert. Generate a BigQuery SQL query to answer this question.

Dataset: `{full_dataset}`

Tables:
- `{full_dataset}.fact_transactions` (transaction_id INT64, transaction_ts TIMESTAMP,
  store_id INT64, employee_id INT64, product_id INT64, quantity INT64,
  unit_price NUMERIC, total_amount NUMERIC, payment_method STRING, customer_id INT64)
- `{full_dataset}.dim_store` (store_id INT64, store_name STRING, city STRING,
  state STRING, zip_code STRING, square_feet INT64, open_date DATE)
- `{full_dataset}.dim_product` (product_id INT64, product_name STRING,
  category STRING, subcategory STRING, brand STRING, unit_price NUMERIC,
  unit_cost NUMERIC, image_uri STRING, description STRING)
- `{full_dataset}.dim_employee` (employee_id INT64, first_name STRING,
  last_name STRING, role STRING, store_id INT64, hire_date DATE)
- `{full_dataset}.dim_customer` (customer_id INT64, first_name STRING,
  last_name STRING, email STRING, phone STRING, loyalty_tier STRING,
  home_store_id INT64, signup_date DATE, points_balance INT64)

Question: {question}

Return ONLY the SQL query, nothing else. Use fully qualified table names.
Limit results to 20 rows unless the question implies otherwise.
"""
        # For now, use predefined query patterns for common questions
        # In production, this would use Gemini to generate SQL
        sql = _generate_sql(question, full_dataset)

        if sql:
            query_job = client.query(sql)
            rows = list(query_job.result())
            # Convert Decimal/date types to JSON-serializable forms
            results = []
            for row in rows[:20]:
                clean_row = {}
                for k, v in row.items():
                    if hasattr(v, 'as_integer_ratio'):  # Decimal/float
                        clean_row[k] = float(v)
                    elif hasattr(v, 'isoformat'):  # date/datetime
                        clean_row[k] = v.isoformat()
                    else:
                        clean_row[k] = v
                results.append(clean_row)
            return {
                "status": "success",
                "question": question,
                "sql": sql,
                "results": results,
                "row_count": len(results),
            }
        else:
            return {
                "status": "unsupported",
                "question": question,
                "message": (
                    "Could not generate SQL for this question. "
                    "Try asking about: top products, sales by store, "
                    "customer loyalty tiers, or payment methods."
                ),
            }

    except ImportError:
        return {
            "status": "error",
            "message": "BigQuery client library not available.",
        }
    except Exception as e:
        logger.error("BigQuery query failed: %s", e)
        return {
            "status": "error",
            "question": question,
            "message": f"Query failed: {str(e)}",
        }


def _generate_sql(question: str, dataset: str) -> str:
    """Generate SQL from natural language using pattern matching.

    In a production system, this would use Gemini to generate SQL.
    For the workshop demo, we support common question patterns.
    """
    q = question.lower()

    if "top" in q and "product" in q:
        return f"""
            SELECT p.product_name, p.category, p.brand,
                   SUM(t.total_amount) AS total_revenue,
                   SUM(t.quantity) AS total_units
            FROM `{dataset}.fact_transactions` t
            JOIN `{dataset}.dim_product` p ON t.product_id = p.product_id
            GROUP BY p.product_name, p.category, p.brand
            ORDER BY total_revenue DESC
            LIMIT 10
        """

    if "store" in q and ("sale" in q or "revenue" in q):
        return f"""
            SELECT s.store_name, s.city,
                   SUM(t.total_amount) AS total_revenue,
                   COUNT(*) AS transaction_count,
                   ROUND(AVG(t.total_amount), 2) AS avg_transaction
            FROM `{dataset}.fact_transactions` t
            JOIN `{dataset}.dim_store` s ON t.store_id = s.store_id
            GROUP BY s.store_name, s.city
            ORDER BY total_revenue DESC
        """

    if "loyalty" in q or "tier" in q:
        return f"""
            SELECT c.loyalty_tier,
                   COUNT(DISTINCT c.customer_id) AS customer_count,
                   ROUND(AVG(c.points_balance), 0) AS avg_points,
                   SUM(t.total_amount) AS total_spend
            FROM `{dataset}.dim_customer` c
            LEFT JOIN `{dataset}.fact_transactions` t ON c.customer_id = t.customer_id
            GROUP BY c.loyalty_tier
            ORDER BY total_spend DESC
        """

    if "payment" in q:
        return f"""
            SELECT payment_method,
                   COUNT(*) AS transaction_count,
                   SUM(total_amount) AS total_revenue,
                   ROUND(AVG(total_amount), 2) AS avg_amount
            FROM `{dataset}.fact_transactions`
            GROUP BY payment_method
            ORDER BY transaction_count DESC
        """

    if "category" in q or "categories" in q:
        return f"""
            SELECT p.category,
                   COUNT(*) AS transaction_count,
                   SUM(t.total_amount) AS total_revenue,
                   SUM(t.quantity) AS total_units
            FROM `{dataset}.fact_transactions` t
            JOIN `{dataset}.dim_product` p ON t.product_id = p.product_id
            GROUP BY p.category
            ORDER BY total_revenue DESC
        """

    if "employee" in q or "associate" in q:
        return f"""
            SELECT e.first_name, e.last_name, e.role, s.store_name,
                   COUNT(t.transaction_id) AS transactions_processed,
                   SUM(t.total_amount) AS total_revenue
            FROM `{dataset}.dim_employee` e
            JOIN `{dataset}.dim_store` s ON e.store_id = s.store_id
            LEFT JOIN `{dataset}.fact_transactions` t ON e.employee_id = t.employee_id
            GROUP BY e.first_name, e.last_name, e.role, s.store_name
            ORDER BY total_revenue DESC
            LIMIT 15
        """

    # Default: summary overview
    return f"""
        SELECT
          (SELECT COUNT(*) FROM `{dataset}.fact_transactions`) AS total_transactions,
          (SELECT ROUND(SUM(total_amount), 2) FROM `{dataset}.fact_transactions`) AS total_revenue,
          (SELECT COUNT(DISTINCT product_id) FROM `{dataset}.dim_product`) AS product_count,
          (SELECT COUNT(*) FROM `{dataset}.dim_store`) AS store_count,
          (SELECT COUNT(*) FROM `{dataset}.dim_employee`) AS employee_count,
          (SELECT COUNT(*) FROM `{dataset}.dim_customer`) AS customer_count
    """


def create_bq_tool():
    """Create a FunctionTool for BigQuery analytics."""
    from google.adk.tools import FunctionTool

    return FunctionTool(func=query_grocery_data)
