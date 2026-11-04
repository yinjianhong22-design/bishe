import copy
from pathlib import Path
import unittest

import yaml
from openapi_spec_validator import validate
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs" / "api" / "openapi.yaml"

BASE_ROUTES = {
    "/api/auth/login": ["post"],
    "/api/verify": ["post"],
    "/api/verify/batch": ["post",],
    "/api/verify/batch/{batch_id}": ["get"],
    "/api/verify/{trace_id}": ["get"],
    "/api/verify/{trace_id}/explanation": ["post"],
    "/api/admin/traces/{trace_id}": ["get"],
    "/api/knowledge/types": ["get"],
    "/api/knowledge/cases": ["get"],
    "/api/knowledge/cases/{case_id}": ["get"],
    "/api/admin/knowledge/cases": ["get", "post"],
    "/api/admin/knowledge/cases/{case_id}": ["patch"],
    "/api/rules": ["get", "post"],
    "/api/rules/{rule_id}": ["get", "delete"],
    "/api/rules/{rule_id}/draft": ["put"],
    "/api/rules/{rule_id}/versions": ["get", "post"],
    "/api/rule-releases": ["get", "post"],
    "/api/rule-releases/{version}": ["get"],
    "/api/rule-releases/{version}/conflicts": ["get"],
    "/api/rule-releases/{version}/conflicts/{conflict_id}/resolution": ["post"],
    "/api/rule-releases/{version}/activate": ["post"],
    "/api/lists/active": ["get"],
    "/api/lists/draft": ["get", "put"],
    "/api/list-releases": ["post"],
    "/api/list-releases/{version}/activate": ["post"],
    "/api/threshold-config/active": ["get"],
    "/api/threshold-config": ["post"],
    "/api/threshold-config/{version}/activate": ["post"],
    "/api/semantic-config/active": ["get"],
    "/api/semantic-config": ["post"],
    "/api/semantic-config/{version}/activate": ["post"],
    "/api/transform-dictionaries/active": ["get"],
    "/api/transform-dictionaries/draft": ["get", "put"],
    "/api/transform-dictionary-releases": ["post"],
    "/api/transform-dictionary-releases/{version}/activate": ["post"],
    "/api/feedback": ["post"],
    "/api/admin/feedback": ["get"],
    "/api/admin/feedback/{feedback_id}": ["patch"],
    "/api/admin/dashboard": ["get"],
    "/api/admin/audit-logs": ["get"],
}

ATTACK_AGENT_ROUTES = {
    "/api/attack/sample-sets": ["get", "post"],
    "/api/attack/sample-sets/{version}": ["get"],
    "/api/attack/sample-sets/{version}/variants": ["post"],
    "/api/attack/sample-sets/{version}/injections": ["post"],
    "/api/attack/sample-sets/{version}/freeze": ["post"],
    "/api/attack/replays": ["post"],
    "/api/attack/replays/{replay_run_id}": ["get"],
    "/api/attack/replays/{replay_run_id}/blindspots": ["get"],
    "/api/attack/replays/{replay_run_id}/rule-drafts": ["post"],
    "/api/attack/comparisons": ["post"],
    "/api/attack/comparisons/{comparison_id}": ["get"],
    "/api/attack/rule-drafts": ["get"],
    "/api/attack/rule-drafts/{draft_id}/review": ["post"],
    "/api/attack/campaigns": ["post"],
    "/api/attack/campaigns/{campaign_id}": ["get"],
    "/api/agent/sessions": ["post"],
    "/api/agent/sessions/{session_id}": ["get"],
    "/api/agent/sessions/{session_id}/messages": ["post"],
    "/api/agent/sessions/{session_id}/contents/{content_ref}/confirmation": ["post"],
    "/api/agent/runs/{run_id}": ["get"],
}


def load_document():
    with CONTRACT.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def schema_validator(schema):
    candidate = copy.deepcopy(schema)
    candidate["components"] = {"schemas": load_document()["components"]["schemas"]}
    return Draft202012Validator(candidate)


def operation_ids(document):
    return [
        operation["operationId"]
        for path in document["paths"].values()
        for method, operation in path.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]


class OpenApiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = load_document()
        cls.schemas = cls.document["components"]["schemas"]

    def test_document_is_valid_openapi_31(self):
        self.assertEqual(self.document["openapi"], "3.1.0")
        validate(self.document)

    def test_operation_ids_are_unique_and_stable(self):
        ids = operation_ids(self.document)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(identifier and identifier[0].islower() for identifier in ids))

    def test_base_routes_cover_design(self):
        for path, methods in BASE_ROUTES.items():
            with self.subTest(path=path):
                self.assertIn(path, self.document["paths"])
                for method in methods:
                    operation = self.document["paths"][path][method]
                    self.assertTrue({"200", "201", "204"} & operation["responses"].keys())
                    self.assertIn("422", operation["responses"])

    def test_security_schemes_and_trace_access(self):
        security = self.document["components"]["securitySchemes"]
        self.assertEqual(security["traceToken"]["in"], "header")
        self.assertEqual(security["traceToken"]["name"], "X-Trace-Token")
        self.assertEqual(security["batchToken"]["name"], "X-Batch-Token")
        for path in ["/api/verify/{trace_id}", "/api/verify/{trace_id}/explanation"]:
            self.assertIn({"traceToken": []}, self.document["paths"][path]["get" if path.endswith("trace_id}") else "post"]["security"])
        self.assertEqual(self.document["paths"]["/api/feedback"]["post"]["security"], [{"traceToken": []}])
        self.assertEqual(self.document["paths"]["/api/admin/traces/{trace_id}"]["get"]["security"], [{"bearerAuth": []}])
        self.assertEqual(self.document["paths"]["/api/verify"]["post"]["security"], [])

    def test_verification_contract_preserves_engine_boundaries(self):
        request = self.schemas["VerificationRequest"]
        self.assertEqual(request["additionalProperties"], False)
        self.assertEqual(request["required"], ["content_type", "content"])
        self.assertEqual(self.schemas["VerifyMode"]["default"], "fast")
        self.assertNotIn("risk_score", request["properties"])
        self.assertNotIn("operation_key", request["properties"])
        self.assertIn("trace_token", self.schemas["VerificationResult"]["properties"])
        self.assertIn("trace_token", self.schemas["BatchItemResult"]["properties"])
        self.assertIn("batch_token", self.schemas["BatchResult"]["properties"])
        upload = self.document["paths"]["/api/verify/batch"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]["properties"]["file"]
        self.assertEqual(upload["maxLength"], 2097152)
        self.assertIn("413", self.document["paths"]["/api/verify/batch"]["post"]["responses"])
        self.assertIn("504", self.document["paths"]["/api/verify/batch"]["post"]["responses"])

    def test_rules_use_draft_version_release_flow(self):
        draft = self.schemas["RuleDraftUpdate"]
        required = set(draft.get("required", []))
        for part in draft.get("allOf", []):
            if "$ref" in part:
                required.update(self.schemas[part["$ref"].rsplit("/", 1)[-1]].get("required", []))
            required.update(part.get("required", []))
        self.assertIn("revision", required)
        self.assertTrue(draft["additionalProperties"] is False)
        self.assertIn("expected_active_version", self.schemas["ActivationRequest"]["required"])
        self.assertIn("resolution", self.schemas["ConflictResolution"]["required"])
        self.assertNotIn("post", self.document["paths"]["/api/rule-releases/{version}"])

    def test_openapi_31_does_not_use_legacy_nullable(self):
        def walk(value):
            if isinstance(value, dict):
                self.assertNotIn("nullable", value)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(self.document)

    def test_attack_and_agent_routes_cover_design(self):
        for path, methods in ATTACK_AGENT_ROUTES.items():
            with self.subTest(path=path):
                self.assertIn(path, self.document["paths"])
                for method in methods:
                    operation = self.document["paths"][path][method]
                    self.assertIn("422", operation["responses"])
                    if path.startswith("/api/attack/"):
                        self.assertEqual(operation["security"], [{"bearerAuth": []}])
                        self.assertNotIn("202", operation["responses"])

    def test_attack_contract_preserves_experiment_boundaries(self):
        comparison = self.schemas["ComparisonCreate"]
        self.assertIn("experiment_type", comparison["required"])
        self.assertIn("arms", comparison["required"])
        arms = comparison["properties"]["arms"]
        self.assertGreaterEqual(arms["minItems"], 2)
        manifest = self.schemas["ExperimentManifest"]
        for field in ["sample_set_version", "verify_mode", "rule_version", "threshold_version", "semantic_config_version", "defense_flag"]:
            self.assertIn(field, manifest["required"])
        self.assertIn("pair_key", self.schemas["ReplayItem"]["required"])
        self.assertIn("failed_count", self.schemas["ReplayRun"]["required"])
        self.assertIn("accepted", self.schemas["RuleDraft"]["properties"]["status"]["enum"])
        self.assertIn("approved", self.schemas["RuleDraft"]["properties"]["status"]["enum"])
        replay = self.schemas["ReplayCreate"]
        self.assertEqual(replay["properties"]["experiment_type"]["const"], "ad_hoc")

    def test_agent_contract_uses_capability_and_confirmed_content(self):
        message = self.schemas["AgentMessageRequest"]
        self.assertTrue(message["additionalProperties"] is False)
        for forbidden in ["owner_id", "session_id", "campaign_id", "risk_score", "operation_key"]:
            self.assertNotIn(forbidden, message["properties"])
        content = self.schemas["VerificationContent"]
        self.assertIn("content_type", content["required"])
        self.assertIn("content", content["required"])
        confirmation = self.schemas["ContentConfirmation"]
        self.assertIn("confirmed", confirmation["required"])
        session = self.document["paths"]["/api/agent/sessions/{session_id}/messages"]["post"]
        self.assertIn({"agentSessionToken": []}, session["security"])
        self.assertIn({"bearerAuth": []}, session["security"])
        response = self.schemas["AgentMessageResponse"]
        self.assertIn("verification_results", response["required"])
        self.assertIn("degraded", response["required"])

    def test_composed_request_and_response_schemas_accept_valid_instances(self):
        rule = {
            "revision": 1, "fraud_type": "impersonation", "weight": 40,
            "conditions": {"fact": "blacklist"}, "explanation": "命中黑名单", "enabled": True,
        }
        validator = schema_validator(self.schemas["RuleDraftUpdate"])
        validator.check_schema(self.schemas["RuleDraftUpdate"])
        self.assertEqual(list(validator.iter_errors(rule)), [])
        blindspots = self.document["paths"]["/api/attack/replays/{replay_run_id}/blindspots"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        example = {"code": "OK", "data": [], "degraded": [], "trace_id": None}
        errors = list(schema_validator(blindspots).iter_errors(example))
        self.assertEqual(errors, [], "blindspot data array must satisfy its response schema")
        feedback = self.document["paths"]["/api/admin/feedback/{feedback_id}"]["patch"]["requestBody"]["content"]["application/json"]["schema"]
        self.assertEqual(list(schema_validator(feedback).iter_errors({"revision": 1, "status": "resolved"})), [])

    def test_verification_result_includes_config_versions(self):
        result = self.schemas["VerificationResult"]
        self.assertIn("versions", result["required"])
        self.assertIn("versions", result["properties"])
        example = self.document["paths"]["/api/verify"]["post"]["responses"]["200"]["content"]["application/json"]["example"]
        self.assertEqual(list(schema_validator(self.schemas["VerificationResponse"]).iter_errors(example)), [])
        if not example["data"]["hits"]:
            self.assertEqual(example["data"]["total_score"], 0)

    def test_capability_tokens_are_creation_only_and_timeout_is_recoverable(self):
        for schema_name, token_names in {
            "VerificationResult": ["trace_token"],
            "BatchItemResult": ["trace_token"],
            "BatchResult": ["batch_token"],
            "AgentSession": ["session_token"],
        }.items():
            for token_name in token_names:
                self.assertNotIn("writeOnly", self.schemas[schema_name]["properties"][token_name])
        batch_get = self.document["paths"]["/api/verify/batch/{batch_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertNotIn("batch_token", str(batch_get))
        timeout = self.document["paths"]["/api/verify/batch"]["post"]["responses"]["504"]["content"]["application/json"]["schema"]
        self.assertIn("BatchTimeoutError", str(timeout))

    def test_experiment_modes_and_failed_items_are_closed(self):
        replay = self.schemas["ReplayCreate"]
        self.assertEqual(self.schemas["AdHocManifest"]["allOf"][1]["properties"]["experiment_mode"]["const"], "single")
        comparison = self.schemas["ComparisonCreate"]
        self.assertIn("oneOf", comparison)
        self.assertEqual(len(comparison["oneOf"]), 3)
        failed_item = {
            "replay_item_id": "6f0579c4-2ea2-4df0-8977-9d9919ee366f",
            "sample_id": "6f0579c4-2ea2-4df0-8977-9d9919ee366f",
            "trace_id": None, "pair_key": "6f0579c4-2ea2-4df0-8977-9d9919ee366f",
            "detected": False, "attack_success": False, "output_validation_failed": False,
            "status": "failed", "error_code": None,
        }
        self.assertTrue(list(schema_validator(self.schemas["ReplayItem"]).iter_errors(failed_item)))
        arm = self.schemas["ExperimentArm"]
        self.assertIn("anyOf", arm["properties"]["replay_run"])

    def test_state_links_and_request_boundaries(self):
        self.assertIn("allOf", self.schemas["RuleDraft"])
        campaign = self.schemas["CampaignCreate"]
        self.assertNotIn("max_rounds", campaign["properties"])
        self.assertNotIn("max_samples", campaign["properties"])
        self.assertIn("minLength", self.schemas["ActivationRequest"]["properties"]["expected_active_version"])
        body_ref = self.document["paths"]["/api/admin/knowledge/cases"]["post"]["requestBody"]["$ref"]
        body_name = body_ref.rsplit("/", 1)[-1]
        case = self.document["components"]["requestBodies"][body_name]["content"]["application/json"]["schema"]
        case_example = {"fraud_type": "impersonation", "title": "案例", "content": "正文", "advice": "建议", "source_url": "https://example.com/case", "status": "draft", "risk_score": 100}
        self.assertTrue(list(schema_validator(case).iter_errors(case_example)))
        query_names = {p["name"] for p in self.document["paths"]["/api/admin/feedback"]["get"]["parameters"] if "name" in p}
        self.assertTrue({"start", "end"} <= query_names)

    def test_review_regressions_reject_invalid_state_instances(self):
        failed_batch_item = {
            "item_no": 1, "content_type": "sms", "status": "failed",
            "trace_id": None, "trace_token": None, "risk_level": "安全",
            "total_score": 0, "error_code": "MODEL_TIMEOUT",
        }
        self.assertTrue(list(schema_validator(self.schemas["BatchItemResult"]).iter_errors(failed_batch_item)))
        rule = {"fraud_type": "impersonation", "weight": 40, "conditions": {"fact": "blacklist"}, "explanation": "命中黑名单", "enabled": True}
        draft = {
            "draft_id": "6f0579c4-2ea2-4df0-8977-9d9919ee366f",
            "source_replay_run_id": None, "source_sample_id": None,
            "based_on_rule_id": None, "proposed_rule": rule, "status": "approved",
            "accepted_rule_id": None, "published_rule_version_id": None,
        }
        self.assertTrue(list(schema_validator(self.schemas["RuleDraft"]).iter_errors(draft)))
        manifest = {
            "sample_set_version": "samples-v1", "verify_mode": "fast", "experiment_mode": "pure",
            "rule_version": "rules-v1", "threshold_version": "thresholds-v1",
            "semantic_config_version": "semantic-v1", "transform_dict_version": "transforms-v1",
            "list_version": "lists-v1", "retriever_version": None,
            "model_provider": None, "model_name": None, "defense_flag": False,
        }
        arms = [{"arm_role": "pure", "manifest": manifest}, {"arm_role": "pure", "manifest": manifest}]
        for schema_name, request in [
            ("ComparisonCreate", {"experiment_type": "E3", "arms": arms}),
            ("CampaignCreate", {"goal": "验证语义层增益", "experiment_type": "E3", "arms": arms}),
        ]:
            with self.subTest(schema=schema_name):
                self.assertTrue(list(schema_validator(self.schemas[schema_name]).iter_errors(request)))

    def test_trace_declares_required_content_context(self):
        for field in ["content_type", "verify_mode"]:
            self.assertIn(field, self.schemas["JudgmentTrace"]["required"])

    def test_no_generic_success_placeholders_remain(self):
        for name in ["RuleVersion", "RuleRelease", "RuleConflict", "Campaign", "AgentRun", "Dashboard"]:
            self.assertIn(name, self.schemas)
        for path, path_item in self.document["paths"].items():
            for method, operation in path_item.items():
                if method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                for status, response in operation["responses"].items():
                    if status.startswith("2"):
                        self.assertNotEqual(response.get("$ref"), "#/components/responses/DataSuccess", f"{method} {path}")

    def test_invalid_documents_are_rejected(self):
        invalid = copy.deepcopy(self.document)
        path, operation = next(iter(invalid["paths"].items()))
        invalid["paths"]["/duplicate"] = {next(iter(operation)): {"operationId": next(iter(operation.values()))["operationId"], "responses": {}}}
        with self.assertRaises(ValueError):
            ids = operation_ids(invalid)
            if len(ids) != len(set(ids)):
                raise ValueError("duplicate operationId")


if __name__ == "__main__":
    unittest.main()
