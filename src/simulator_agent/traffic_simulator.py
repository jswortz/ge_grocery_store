#!/usr/bin/env python3
"""Comprehensive traffic simulator for Gemini Enterprise grocery demo.

Generates synthetic traffic across all deployed endpoints to populate
telemetry, build session diversity, and validate integrations.

Phases:
1. StreamAssist (Discovery Engine) session diversity
2. Agent Engine (ADK) multi-agent traffic
3. MCP Agent (BigQuery analytics) traffic
4. A2A Agent (Cloud Run) traffic
5. BigQuery direct validation

Usage:
    python -m src.simulator_agent.traffic_simulator
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.auth
import requests
import yaml
from google.auth.transport.requests import Request
from google.cloud import bigquery

# Import existing StreamAssist client
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from client.stream_assist import StreamAssistClient, AgentAuthorizationError, RetryableAPIError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


@dataclass
class QueryResult:
    """Result of a single query attempt."""
    phase: str
    query: str
    success: bool
    latency_ms: float
    error: Optional[str] = None
    response_length: int = 0
    session_id: Optional[str] = None


@dataclass
class PhaseStats:
    """Statistics for a simulation phase."""
    phase_name: str
    sessions_created: int = 0
    queries_sent: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    results: List[QueryResult] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.queries_sent if self.queries_sent > 0 else 0.0

    @property
    def success_rate(self) -> float:
        return (self.queries_sent - self.errors) / self.queries_sent if self.queries_sent > 0 else 0.0


@dataclass
class SimulationReport:
    """Complete simulation report."""
    start_time: datetime
    end_time: Optional[datetime] = None
    phases: Dict[str, PhaseStats] = field(default_factory=dict)
    self_healing_actions: List[str] = field(default_factory=list)

    @property
    def total_queries(self) -> int:
        return sum(p.queries_sent for p in self.phases.values())

    @property
    def total_errors(self) -> int:
        return sum(p.errors for p in self.phases.values())

    @property
    def duration_minutes(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return 0.0


class TrafficSimulator:
    """Orchestrates traffic generation across all Gemini Enterprise endpoints."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_PATH
        self.config = self._load_config()
        self.report = SimulationReport(start_time=datetime.now())

        # Initialize clients
        self.stream_assist_client = StreamAssistClient.from_config(self.config_path)
        self.credentials, self.project_id = google.auth.default()
        self.bq_client = bigquery.Client(project=self.config["bigquery"]["project"])

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from settings.yaml."""
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authenticated headers for API calls."""
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return {
            "Authorization": f"Bearer {self.credentials.token}",
            "Content-Type": "application/json",
        }

    def _record_query(self, phase: str, query: str, success: bool, latency_ms: float,
                     error: Optional[str] = None, response_length: int = 0,
                     session_id: Optional[str] = None):
        """Record a query result."""
        result = QueryResult(
            phase=phase,
            query=query,
            success=success,
            latency_ms=latency_ms,
            error=error,
            response_length=response_length,
            session_id=session_id,
        )

        if phase not in self.report.phases:
            self.report.phases[phase] = PhaseStats(phase_name=phase)

        stats = self.report.phases[phase]
        stats.queries_sent += 1
        stats.total_latency_ms += latency_ms
        if not success:
            stats.errors += 1
        stats.results.append(result)

        logger.info(f"[{phase}] Query: {query[:80]}... | Success: {success} | Latency: {latency_ms:.0f}ms")

    def _add_issue(self, phase: str, issue: str):
        """Record an issue found during simulation."""
        if phase not in self.report.phases:
            self.report.phases[phase] = PhaseStats(phase_name=phase)
        self.report.phases[phase].issues.append(issue)
        logger.warning(f"[{phase}] Issue: {issue}")

    def _add_self_healing(self, action: str):
        """Record a self-healing action taken."""
        self.report.self_healing_actions.append(action)
        logger.info(f"[SELF-HEAL] {action}")

    # ========================================================================
    # PHASE 1: StreamAssist Session Diversity
    # ========================================================================

    def phase1_stream_assist_diversity(self):
        """Generate diverse StreamAssist sessions across all query categories."""
        logger.info("="*80)
        logger.info("PHASE 1: StreamAssist Session Diversity")
        logger.info("="*80)

        phase = "Phase 1: StreamAssist"

        # Define query categories with realistic queries
        query_categories = {
            "SOP Queries": [
                "What is the procedure for opening the store?",
                "How do I handle a customer complaint?",
                "What are the food safety guidelines for the deli department?",
                "Describe the cash register closing procedure",
                "What PPE is required for cleaning tasks?",
            ],
            "Brand Guidelines": [
                "What are our brand colors?",
                "How should the logo be displayed on signage?",
                "What font should be used for promotional materials?",
                "What is our brand voice and tone?",
                "What are the spacing requirements for our logo?",
            ],
            "Conversational": [
                "Hello",
                "Good morning",
                "I need help",
                "What can you help me with?",
            ],
            "Follow-up Patterns": [
                ("What is the store opening procedure?", "What time should I arrive?"),
                ("Tell me about customer service policies", "What if a customer wants a refund?"),
                ("What are our brand guidelines?", "Can you show me examples of correct logo usage?"),
            ],
        }

        # Execute single-turn sessions
        for category, queries in query_categories.items():
            if category == "Follow-up Patterns":
                continue  # Handle separately

            logger.info(f"\nCategory: {category}")
            for query in queries:
                try:
                    session_id = self.stream_assist_client.create_session(
                        display_name=f"TrafficSim-{category}-{datetime.now().strftime('%H%M%S')}"
                    )
                    self.report.phases.setdefault(phase, PhaseStats(phase_name=phase)).sessions_created += 1

                    start = time.time()
                    response = self.stream_assist_client.query(query, session_id=session_id)
                    latency = (time.time() - start) * 1000

                    self._record_query(
                        phase=phase,
                        query=query,
                        success=True,
                        latency_ms=latency,
                        response_length=len(response.text),
                        session_id=session_id,
                    )

                    # Check for quality issues
                    if latency > 10000:
                        self._add_issue(phase, f"High latency ({latency:.0f}ms) for query: {query}")

                    if not response.text:
                        self._add_issue(phase, f"Empty response for query: {query}")

                    # Rate limiting
                    time.sleep(0.8)

                except AgentAuthorizationError as e:
                    self._record_query(phase, query, False, 0, error=str(e))
                    self._add_issue(phase, f"Agent authorization required: {e}")
                    break  # Don't continue if auth is broken

                except RetryableAPIError as e:
                    # Already retried by tenacity, this is a hard failure
                    self._record_query(phase, query, False, 0, error=str(e))
                    self._add_issue(phase, f"API error after retries: {e}")

                except Exception as e:
                    self._record_query(phase, query, False, 0, error=str(e))
                    self._add_issue(phase, f"Unexpected error: {e}")

        # Execute multi-turn sessions (follow-up patterns)
        logger.info("\nCategory: Follow-up Patterns (Multi-turn)")
        for initial_query, followup_query in query_categories["Follow-up Patterns"]:
            try:
                session_id = self.stream_assist_client.create_session(
                    display_name=f"TrafficSim-MultiTurn-{datetime.now().strftime('%H%M%S')}"
                )
                self.report.phases[phase].sessions_created += 1

                # First query
                start = time.time()
                response1 = self.stream_assist_client.query(initial_query, session_id=session_id)
                latency1 = (time.time() - start) * 1000
                self._record_query(phase, initial_query, True, latency1,
                                 response_length=len(response1.text), session_id=session_id)

                time.sleep(1.0)  # Pause between turns

                # Follow-up query in same session
                start = time.time()
                response2 = self.stream_assist_client.query(followup_query, session_id=session_id)
                latency2 = (time.time() - start) * 1000
                self._record_query(phase, followup_query, True, latency2,
                                 response_length=len(response2.text), session_id=session_id)

                # Validate context was maintained
                if len(response2.text) < 10:
                    self._add_issue(phase, f"Follow-up response too short, context may be lost: {followup_query}")

                time.sleep(1.0)

            except Exception as e:
                self._record_query(phase, f"{initial_query} -> {followup_query}", False, 0, error=str(e))
                self._add_issue(phase, f"Multi-turn session failed: {e}")

    # ========================================================================
    # PHASE 2: Agent Engine (ADK) Traffic
    # ========================================================================

    def phase2_agent_engine_adk(self):
        """Send queries to the main ADK agent on Agent Engine."""
        logger.info("="*80)
        logger.info("PHASE 2: Agent Engine (ADK) Traffic")
        logger.info("="*80)

        phase = "Phase 2: Agent Engine (ADK)"
        agent_id = self.config["project"]["agent_engine_id"]
        project_id = self.config["project"]["id"]

        # Agent Engine REST API endpoint
        url = (
            f"https://us-central1-aiplatform.googleapis.com/v1beta1/"
            f"projects/{project_id}/locations/us-central1/reasoningEngines/{agent_id}:query"
        )

        # Query categories targeting different sub-agents and tools
        queries = {
            "Analytics (BQ sub-agent)": [
                "What are the top 5 selling products?",
                "Show me sales by store",
                "Which employees had the most transactions last month?",
                "What's the revenue trend over time?",
                "Compare sales across loyalty tiers",
            ],
            "Image Generation": [
                "Generate an image of organic avocados",
                "Create a product image for sourdough bread",
            ],
            "Discovery Search (SOP)": [
                "Find the SOP for inventory management",
                "What is the procedure for handling expired products?",
            ],
            "Discovery Search (Brand)": [
                "What do our brand guidelines say about social media?",
                "What colors should I use for promotional signage?",
            ],
            "Multi-agent routing": [
                "What are our top selling products and can you generate an image of the #1 seller?",
                "Show me sales data for our Houston store and find the SOP for that location",
            ],
        }

        for category, query_list in queries.items():
            logger.info(f"\nCategory: {category}")
            for query in query_list:
                try:
                    headers = self._get_auth_headers()
                    payload = {
                        "input": {
                            "text": query
                        }
                    }

                    start = time.time()
                    response = requests.post(url, headers=headers, json=payload, timeout=60)
                    latency = (time.time() - start) * 1000

                    if response.ok:
                        result = response.json()
                        output = result.get("output", {})
                        response_text = str(output)

                        self._record_query(
                            phase=phase,
                            query=query,
                            success=True,
                            latency_ms=latency,
                            response_length=len(response_text),
                        )

                        # Quality checks
                        if latency > 10000:
                            self._add_issue(phase, f"High latency ({latency:.0f}ms): {query}")

                        if not response_text or len(response_text) < 10:
                            self._add_issue(phase, f"Empty or very short response: {query}")
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                        self._record_query(phase, query, False, latency, error=error_msg)
                        self._add_issue(phase, f"Agent Engine query failed: {error_msg}")

                        # Self-healing: retry once with backoff
                        if response.status_code in [429, 500, 502, 503, 504]:
                            self._add_self_healing(f"Retrying query after {response.status_code} error")
                            time.sleep(5.0)
                            response_retry = requests.post(url, headers=headers, json=payload, timeout=60)
                            if response_retry.ok:
                                self._add_self_healing(f"Retry successful for: {query}")

                    time.sleep(1.5)  # Rate limiting

                except requests.Timeout:
                    self._record_query(phase, query, False, 60000, error="Request timeout")
                    self._add_issue(phase, f"Timeout after 60s: {query}")

                except Exception as e:
                    self._record_query(phase, query, False, 0, error=str(e))
                    self._add_issue(phase, f"Unexpected error: {e}")

    # ========================================================================
    # PHASE 3: MCP Agent Traffic
    # ========================================================================

    def phase3_mcp_agent(self):
        """Send queries to the MCP BigQuery analyst agent."""
        logger.info("="*80)
        logger.info("PHASE 3: MCP Agent (BigQuery Analytics) Traffic")
        logger.info("="*80)

        phase = "Phase 3: MCP Agent"
        agent_id = self.config["project"]["mcp_agent_engine_id"]
        project_id = self.config["project"]["id"]

        url = (
            f"https://us-central1-aiplatform.googleapis.com/v1beta1/"
            f"projects/{project_id}/locations/us-central1/reasoningEngines/{agent_id}:query"
        )

        queries = [
            "List all tables in the dataset",
            "Describe the fact_transactions table",
            "What are total sales by product category?",
            "Show me a forecast for next quarter's revenue",
            "Analyze contribution by store to overall sales",
            "What is the average transaction value by loyalty tier?",
            "Which store has the highest employee-to-transaction ratio?",
            "Show me the top 10 products by revenue",
            "What percentage of sales come from Gold tier customers?",
        ]

        for query in queries:
            try:
                headers = self._get_auth_headers()
                payload = {"input": {"text": query}}

                start = time.time()
                response = requests.post(url, headers=headers, json=payload, timeout=90)
                latency = (time.time() - start) * 1000

                if response.ok:
                    result = response.json()
                    output = str(result.get("output", {}))

                    self._record_query(phase, query, True, latency, response_length=len(output))

                    # Check for SQL generation quality
                    if "SELECT" in output.upper():
                        logger.info(f"  ✓ SQL generated in response")

                    if latency > 15000:
                        self._add_issue(phase, f"High latency ({latency:.0f}ms): {query}")
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    self._record_query(phase, query, False, latency, error=error_msg)
                    self._add_issue(phase, f"MCP agent query failed: {error_msg}")

                time.sleep(2.0)  # MCP queries can be heavier

            except Exception as e:
                self._record_query(phase, query, False, 0, error=str(e))
                self._add_issue(phase, f"Error: {e}")

    # ========================================================================
    # PHASE 4: A2A Agent Traffic
    # ========================================================================

    def phase4_a2a_agent(self):
        """Send traffic to the Cloud Run A2A agent."""
        logger.info("="*80)
        logger.info("PHASE 4: A2A Agent (Cloud Run) Traffic")
        logger.info("="*80)

        phase = "Phase 4: A2A Agent"
        a2a_url = self.config["project"]["a2a_cloud_run_url"]

        # Check AgentCard endpoint
        try:
            card_url = f"{a2a_url}/.well-known/agent.json"
            headers = self._get_auth_headers()

            start = time.time()
            response = requests.get(card_url, headers=headers, timeout=30)
            latency = (time.time() - start) * 1000

            if response.ok:
                agent_card = response.json()
                self._record_query(phase, "GET AgentCard", True, latency,
                                 response_length=len(json.dumps(agent_card)))
                logger.info(f"  ✓ AgentCard retrieved: {agent_card.get('name', 'Unknown')}")
            else:
                self._record_query(phase, "GET AgentCard", False, latency,
                                 error=f"HTTP {response.status_code}")
                self._add_issue(phase, f"AgentCard endpoint failed: {response.status_code}")
        except Exception as e:
            self._record_query(phase, "GET AgentCard", False, 0, error=str(e))
            self._add_issue(phase, f"AgentCard request error: {e}")

        # Send sample task requests
        sample_tasks = [
            {"task": "analyze_sales", "parameters": {"store": "Downtown Market"}},
            {"task": "get_product_info", "parameters": {"product_id": 1}},
        ]

        for i, task in enumerate(sample_tasks, 1):
            try:
                headers = self._get_auth_headers()

                start = time.time()
                response = requests.post(
                    f"{a2a_url}/execute",
                    headers=headers,
                    json=task,
                    timeout=30
                )
                latency = (time.time() - start) * 1000

                query_desc = f"A2A Task {i}: {task['task']}"

                if response.ok:
                    result = response.json()
                    self._record_query(phase, query_desc, True, latency,
                                     response_length=len(json.dumps(result)))
                else:
                    self._record_query(phase, query_desc, False, latency,
                                     error=f"HTTP {response.status_code}")
                    self._add_issue(phase, f"Task execution failed: {response.status_code}")

                time.sleep(1.0)

            except Exception as e:
                self._record_query(phase, query_desc, False, 0, error=str(e))
                self._add_issue(phase, f"Task request error: {e}")

    # ========================================================================
    # PHASE 5: BigQuery Direct Validation
    # ========================================================================

    def phase5_bigquery_validation(self):
        """Validate BigQuery schema and data integrity."""
        logger.info("="*80)
        logger.info("PHASE 5: BigQuery Direct Validation")
        logger.info("="*80)

        phase = "Phase 5: BigQuery Validation"
        dataset_id = f"{self.config['bigquery']['project']}.{self.config['bigquery']['dataset']}"

        validations = [
            ("Row count: fact_transactions", f"SELECT COUNT(*) as cnt FROM `{dataset_id}.fact_transactions`", 12000),
            ("Row count: dim_store", f"SELECT COUNT(*) as cnt FROM `{dataset_id}.dim_store`", 3),
            ("Row count: dim_product", f"SELECT COUNT(*) as cnt FROM `{dataset_id}.dim_product`", 20),
            ("Row count: dim_employee", f"SELECT COUNT(*) as cnt FROM `{dataset_id}.dim_employee`", 15),
            ("Row count: dim_customer", f"SELECT COUNT(*) as cnt FROM `{dataset_id}.dim_customer`", 40),
            ("Referential integrity: store_id",
             f"SELECT COUNT(*) as cnt FROM `{dataset_id}.fact_transactions` t "
             f"LEFT JOIN `{dataset_id}.dim_store` s ON t.store_id = s.store_id WHERE s.store_id IS NULL",
             0),
            ("Referential integrity: product_id",
             f"SELECT COUNT(*) as cnt FROM `{dataset_id}.fact_transactions` t "
             f"LEFT JOIN `{dataset_id}.dim_product` p ON t.product_id = p.product_id WHERE p.product_id IS NULL",
             0),
            ("Null foreign keys check",
             f"SELECT COUNT(*) as cnt FROM `{dataset_id}.fact_transactions` "
             f"WHERE store_id IS NULL OR product_id IS NULL OR employee_id IS NULL",
             0),
        ]

        checks_passed = 0
        checks_total = len(validations)

        for check_name, query, expected_value in validations:
            try:
                start = time.time()
                query_job = self.bq_client.query(query)
                result = list(query_job.result())
                latency = (time.time() - start) * 1000

                actual_value = result[0]["cnt"] if result else None

                # For row counts, allow some variance (within 10%)
                if "Row count" in check_name:
                    tolerance = expected_value * 0.1
                    success = abs(actual_value - expected_value) <= tolerance
                    if not success:
                        self._add_issue(phase,
                            f"{check_name}: Expected ~{expected_value}, got {actual_value}")
                else:
                    success = actual_value == expected_value
                    if not success:
                        self._add_issue(phase,
                            f"{check_name}: Expected {expected_value}, got {actual_value}")

                self._record_query(phase, check_name, success, latency)

                if success:
                    checks_passed += 1
                    logger.info(f"  ✓ {check_name}: {actual_value}")
                else:
                    logger.warning(f"  ✗ {check_name}: Expected {expected_value}, got {actual_value}")

            except Exception as e:
                self._record_query(phase, check_name, False, 0, error=str(e))
                self._add_issue(phase, f"{check_name} failed: {e}")

        logger.info(f"\nValidation Summary: {checks_passed}/{checks_total} checks passed")

        if checks_passed < checks_total:
            self._add_self_healing(
                f"BigQuery validation issues detected. Consider re-running seed data script."
            )

    # ========================================================================
    # Main Execution
    # ========================================================================

    def run(self):
        """Execute all simulation phases and generate report."""
        logger.info("\n" + "="*80)
        logger.info("STARTING COMPREHENSIVE TRAFFIC SIMULATION")
        logger.info(f"Retailer: {self.config['retailer']['name']}")
        logger.info(f"Project: {self.config['project']['id']}")
        logger.info(f"Start Time: {self.report.start_time}")
        logger.info("="*80 + "\n")

        try:
            self.phase1_stream_assist_diversity()
            time.sleep(2)

            self.phase2_agent_engine_adk()
            time.sleep(2)

            self.phase3_mcp_agent()
            time.sleep(2)

            self.phase4_a2a_agent()
            time.sleep(2)

            self.phase5_bigquery_validation()

        except KeyboardInterrupt:
            logger.warning("\n\nSimulation interrupted by user")
        except Exception as e:
            logger.error(f"\n\nSimulation failed with error: {e}", exc_info=True)
        finally:
            self.report.end_time = datetime.now()
            self._print_report()

    def _print_report(self):
        """Print comprehensive simulation report."""
        print("\n" + "="*80)
        print("TRAFFIC SIMULATION REPORT")
        print("="*80)

        print(f"\nSummary:")
        print(f"  Total sessions created: {sum(p.sessions_created for p in self.report.phases.values())}")
        print(f"  Total queries sent: {self.report.total_queries}")
        print(f"  Total errors: {self.report.total_errors}")
        print(f"  Self-healing actions: {len(self.report.self_healing_actions)}")
        print(f"  Duration: {self.report.duration_minutes:.2f} minutes")

        print(f"\nPhase Results:")
        for phase_name, stats in self.report.phases.items():
            print(f"\n  {phase_name}")
            print(f"    Sessions: {stats.sessions_created} | Queries: {stats.queries_sent} | Errors: {stats.errors}")
            print(f"    Avg Latency: {stats.avg_latency_ms:.0f}ms | Success Rate: {stats.success_rate*100:.1f}%")
            if stats.issues:
                print(f"    Issues: {len(stats.issues)}")

        print(f"\nDeficiencies Found:")
        print(f"{'#':<4} {'Severity':<10} {'Component':<30} {'Description':<60}")
        print("-"*110)

        issue_num = 1
        for phase_name, stats in self.report.phases.items():
            for issue in stats.issues:
                severity = "HIGH" if "failed" in issue.lower() or "error" in issue.lower() else "MEDIUM"
                component = phase_name
                description = issue[:60]
                print(f"{issue_num:<4} {severity:<10} {component:<30} {description:<60}")
                issue_num += 1

        if issue_num == 1:
            print("  No deficiencies found - all systems operating normally")

        print(f"\nSelf-Healing Actions Taken:")
        if self.report.self_healing_actions:
            for action in self.report.self_healing_actions:
                print(f"  - {action}")
        else:
            print("  None required")

        print(f"\nRecommendations:")
        recommendations = []

        # Analyze results and generate recommendations
        for phase_name, stats in self.report.phases.items():
            if stats.success_rate < 0.9:
                recommendations.append(
                    f"Investigate {phase_name} - success rate only {stats.success_rate*100:.1f}%"
                )
            if stats.avg_latency_ms > 8000:
                recommendations.append(
                    f"Optimize {phase_name} - average latency {stats.avg_latency_ms:.0f}ms exceeds 8s threshold"
                )

        if not recommendations:
            recommendations.append("All systems performing within expected parameters")

        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

        print(f"\nTelemetry Confirmation:")
        print(f"  Cloud Trace spans: Expected (Agent Engine has OTel enabled)")
        print(f"  Session diversity: {sum(p.sessions_created for p in self.report.phases.values())} unique sessions")
        print(f"  Query pattern coverage: {len(self.report.phases)}/5 phases completed")

        print("\n" + "="*80)
        print(f"Simulation completed at {self.report.end_time}")
        print("="*80 + "\n")


def main():
    """Main entry point."""
    simulator = TrafficSimulator()
    simulator.run()


if __name__ == "__main__":
    main()
