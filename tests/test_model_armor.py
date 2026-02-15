"""Tests for Model Armor integration.

Unit tests validate config and provisioning script correctness.
Integration tests validate the live Model Armor template and
Discovery Engine assistant configuration.
"""

import json
import os
import subprocess
import unittest
from pathlib import Path

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


def _load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


class TestModelArmorConfig(unittest.TestCase):
    """Unit tests: config and provisioning script correctness."""

    def test_config_has_model_armor_section(self):
        config = _load_config()
        assert "model_armor" in config
        assert config["model_armor"]["enabled"] is True

    def test_config_has_template_id(self):
        config = _load_config()
        assert "template_id" in config["model_armor"]
        assert config["model_armor"]["template_id"] == "grocery-workshop-armor-us"

    def test_config_failure_mode_is_fail_open(self):
        config = _load_config()
        assert config["model_armor"]["failure_mode"] == "FAIL_OPEN"

    def test_provisioning_script_exists(self):
        path = PROJECT_ROOT / "infra" / "provision_model_armor.sh"
        assert path.exists(), "provision_model_armor.sh missing"

    def test_provisioning_script_executable(self):
        path = PROJECT_ROOT / "infra" / "provision_model_armor.sh"
        assert os.access(path, os.X_OK), "provision_model_armor.sh not executable"

    def test_provisioning_script_uses_correct_api_schema(self):
        """Verify script uses raiFilters array (not raiFilterType)."""
        path = PROJECT_ROOT / "infra" / "provision_model_armor.sh"
        content = path.read_text()
        # Correct schema uses raiFilters array with filterType
        assert "raiFilters" in content
        assert '"filterType"' in content
        assert '"confidenceLevel"' in content
        # Should NOT use old incorrect field names
        assert "raiFilterType" not in content

    def test_provisioning_script_covers_all_rai_filters(self):
        path = PROJECT_ROOT / "infra" / "provision_model_armor.sh"
        content = path.read_text()
        for filter_type in ["HATE_SPEECH", "SEXUALLY_EXPLICIT", "HARASSMENT", "DANGEROUS"]:
            assert filter_type in content, f"Missing RAI filter: {filter_type}"

    def test_provisioning_script_enables_pi_jailbreak(self):
        path = PROJECT_ROOT / "infra" / "provision_model_armor.sh"
        content = path.read_text()
        assert "piAndJailbreakFilterSettings" in content
        assert '"filterEnforcement": "ENABLED"' in content

    def test_provisioning_script_enables_sdp(self):
        path = PROJECT_ROOT / "infra" / "provision_model_armor.sh"
        content = path.read_text()
        assert "sdpSettings" in content

    def test_provisioning_script_enables_malicious_uri(self):
        path = PROJECT_ROOT / "infra" / "provision_model_armor.sh"
        content = path.read_text()
        assert "maliciousUriFilterSettings" in content


@pytest.mark.integration
class TestModelArmorLive(unittest.TestCase):
    """Integration tests: validate live Model Armor resources.

    These tests require:
    - gcloud auth application-default login
    - Model Armor API enabled
    - Template created via provision_model_armor.sh
    """

    @classmethod
    def setUpClass(cls):
        cls.config = _load_config()
        cls.project_id = cls.config["project"]["id"]
        cls.template_id = cls.config["model_armor"]["template_id"]
        cls.engine_id = cls.config["project"]["engine_id"]
        cls.location = "us-central1"

        # Get access token
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            pytest.skip("No gcloud auth available")
        cls.access_token = result.stdout.strip()

    def _get_template(self):
        """Fetch the Model Armor template via REST API."""
        import urllib.request
        url = (
            f"https://modelarmor.googleapis.com/v1/projects/{self.project_id}"
            f"/locations/{self.location}/templates/{self.template_id}"
        )
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.access_token}",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

    def _get_assistant(self):
        """Fetch the Discovery Engine assistant config."""
        import urllib.request
        url = (
            f"https://discoveryengine.googleapis.com/v1/projects/{self.project_id}"
            f"/locations/global/collections/default_collection"
            f"/engines/{self.engine_id}/assistants/default_assistant"
        )
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.access_token}",
            "X-Goog-User-Project": self.project_id,
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

    def test_model_armor_api_enabled(self):
        """Verify the Model Armor API is enabled on the project."""
        result = subprocess.run(
            ["gcloud", "services", "list", "--enabled",
             f"--project={self.project_id}",
             "--filter=name:modelarmor",
             "--format=value(name)"],
            capture_output=True, text=True, timeout=15,
        )
        assert "modelarmor" in result.stdout, (
            "Model Armor API not enabled. Run: "
            f"gcloud services enable modelarmor.googleapis.com --project={self.project_id}"
        )

    def test_model_armor_template_exists(self):
        """Verify the Model Armor template exists."""
        template = self._get_template()
        if "error" in template:
            pytest.skip(
                f"Template not accessible: {template['error']}. "
                "Run: bash infra/provision_model_armor.sh"
            )
        assert "filterConfig" in template

    def test_model_armor_template_has_rai_filters(self):
        """Verify template has all 4 RAI filter types."""
        template = self._get_template()
        if "error" in template:
            pytest.skip("Template not accessible")

        rai_settings = template.get("filterConfig", {}).get("raiSettings", {})
        rai_filters = rai_settings.get("raiFilters", [])
        filter_types = {f.get("filterType") for f in rai_filters}
        for expected in ["HATE_SPEECH", "SEXUALLY_EXPLICIT", "HARASSMENT", "DANGEROUS"]:
            assert expected in filter_types, f"Missing RAI filter: {expected}"

    def test_model_armor_template_has_pi_jailbreak(self):
        """Verify template has prompt injection/jailbreak filter."""
        template = self._get_template()
        if "error" in template:
            pytest.skip("Template not accessible")

        pi_settings = template.get("filterConfig", {}).get(
            "piAndJailbreakFilterSettings", {}
        )
        assert pi_settings.get("filterEnforcement") == "ENABLED"

    def test_discovery_engine_assistant_has_model_armor(self):
        """Verify Model Armor is enabled on the Discovery Engine assistant."""
        assistant = self._get_assistant()
        if "error" in assistant:
            pytest.skip("Assistant not accessible")

        customer_policy = assistant.get("customerPolicy", {})
        model_armor_config = customer_policy.get("modelArmorConfig", {})

        if not model_armor_config:
            self.fail(
                "Model Armor not configured on Discovery Engine assistant. "
                "Run: bash infra/provision_model_armor.sh"
            )

        assert "userPromptTemplate" in model_armor_config
        assert "responseTemplate" in model_armor_config
        assert model_armor_config.get("failureMode") == "FAIL_OPEN"


if __name__ == "__main__":
    unittest.main()
