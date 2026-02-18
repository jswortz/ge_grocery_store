"""Tests for eval configuration and scenario files.

Validates that all eval directories contain well-formed JSON files with
the required structure for Agent Engine evaluations. No GCP credentials needed.
"""

import json
from pathlib import Path

import pytest

EVALS_DIR = Path(__file__).resolve().parent.parent / "evals"

# All eval directories that should exist
EXPECTED_EVAL_DIRS = ["grocery_assistant", "mcp_analyst", "simulator", "a2a_agent"]


class TestEvalDirectoryStructure:
    """Verify eval directories exist and contain required files."""

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_eval_directory_exists(self, eval_name):
        eval_dir = EVALS_DIR / eval_name
        assert eval_dir.is_dir(), f"Eval directory {eval_name}/ should exist under evals/"

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_eval_config_exists(self, eval_name):
        config_file = EVALS_DIR / eval_name / "eval_config.json"
        assert config_file.is_file(), f"{eval_name}/eval_config.json should exist"

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_scenarios_file_exists(self, eval_name):
        scenarios_file = EVALS_DIR / eval_name / "scenarios.json"
        assert scenarios_file.is_file(), f"{eval_name}/scenarios.json should exist"


class TestEvalConfigStructure:
    """Verify eval_config.json files have required fields."""

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_config_is_valid_json(self, eval_name):
        config_file = EVALS_DIR / eval_name / "eval_config.json"
        with open(config_file) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_config_has_criteria(self, eval_name):
        config_file = EVALS_DIR / eval_name / "eval_config.json"
        with open(config_file) as f:
            data = json.load(f)
        assert "criteria" in data, "eval_config must have 'criteria' key"
        assert isinstance(data["criteria"], dict)
        assert len(data["criteria"]) > 0, "criteria must have at least one entry"

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_config_criteria_have_thresholds(self, eval_name):
        config_file = EVALS_DIR / eval_name / "eval_config.json"
        with open(config_file) as f:
            data = json.load(f)
        for criterion_name, criterion in data["criteria"].items():
            assert "threshold" in criterion, (
                f"Criterion '{criterion_name}' in {eval_name} must have a 'threshold'"
            )
            assert isinstance(criterion["threshold"], (int, float))

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_config_has_safety_criterion(self, eval_name):
        config_file = EVALS_DIR / eval_name / "eval_config.json"
        with open(config_file) as f:
            data = json.load(f)
        assert "safety_v1" in data["criteria"], (
            f"{eval_name} eval_config must include safety_v1 criterion"
        )

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_config_has_user_simulator(self, eval_name):
        config_file = EVALS_DIR / eval_name / "eval_config.json"
        with open(config_file) as f:
            data = json.load(f)
        assert "user_simulator_config" in data, (
            "eval_config must have 'user_simulator_config'"
        )
        sim_config = data["user_simulator_config"]
        assert "model" in sim_config, "user_simulator_config must specify a model"
        assert "max_allowed_invocations" in sim_config


class TestEvalScenariosStructure:
    """Verify scenarios.json files have required fields."""

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_scenarios_is_valid_json(self, eval_name):
        scenarios_file = EVALS_DIR / eval_name / "scenarios.json"
        with open(scenarios_file) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_scenarios_has_eval_set_id(self, eval_name):
        scenarios_file = EVALS_DIR / eval_name / "scenarios.json"
        with open(scenarios_file) as f:
            data = json.load(f)
        assert "eval_set_id" in data, "scenarios must have 'eval_set_id'"
        assert isinstance(data["eval_set_id"], str)
        assert len(data["eval_set_id"]) > 0

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_scenarios_has_eval_cases(self, eval_name):
        scenarios_file = EVALS_DIR / eval_name / "scenarios.json"
        with open(scenarios_file) as f:
            data = json.load(f)
        assert "eval_cases" in data, "scenarios must have 'eval_cases'"
        assert isinstance(data["eval_cases"], list)
        assert len(data["eval_cases"]) > 0, "eval_cases must not be empty"

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_eval_cases_have_required_fields(self, eval_name):
        scenarios_file = EVALS_DIR / eval_name / "scenarios.json"
        with open(scenarios_file) as f:
            data = json.load(f)
        for i, case in enumerate(data["eval_cases"]):
            assert "eval_id" in case, f"eval_cases[{i}] in {eval_name} must have 'eval_id'"
            assert "conversation_scenario" in case, (
                f"eval_cases[{i}] in {eval_name} must have 'conversation_scenario'"
            )
            scenario = case["conversation_scenario"]
            assert "starting_prompt" in scenario, (
                f"eval_cases[{i}] in {eval_name} must have 'starting_prompt'"
            )
            assert "conversation_plan" in scenario, (
                f"eval_cases[{i}] in {eval_name} must have 'conversation_plan'"
            )

    @pytest.mark.parametrize("eval_name", EXPECTED_EVAL_DIRS)
    def test_eval_ids_are_unique(self, eval_name):
        scenarios_file = EVALS_DIR / eval_name / "scenarios.json"
        with open(scenarios_file) as f:
            data = json.load(f)
        eval_ids = [case["eval_id"] for case in data["eval_cases"]]
        assert len(eval_ids) == len(set(eval_ids)), (
            f"Duplicate eval_ids found in {eval_name}: {eval_ids}"
        )
