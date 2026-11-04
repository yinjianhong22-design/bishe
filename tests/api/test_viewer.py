import copy
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient
import yaml

from docs.api import viewer


class ViewerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(viewer.app)
        cls.document = viewer.load_document(viewer.CONTRACT_PATH)

    def test_document_endpoints_expose_the_same_contract(self):
        json_response = self.client.get("/openapi.json")
        yaml_response = self.client.get("/openapi.yaml")
        docs_response = self.client.get("/docs")
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(yaml_response.status_code, 200)
        self.assertEqual(docs_response.status_code, 200)
        self.assertEqual(json_response.json(), self.document)
        self.assertEqual(yaml.safe_load(yaml_response.text), self.document)
        self.assertIn("Swagger UI", docs_response.text)
        self.assertIn("supportedSubmitMethods", docs_response.text)
        self.assertIn("[]", docs_response.text)

    def test_viewer_has_no_business_routes(self):
        paths = [route.path for route in viewer.app.routes]
        self.assertNotIn("/api/verify", paths)
        self.assertNotIn("/api/attack/campaigns", paths)
        self.assertNotIn("/api/agent/sessions", paths)
        self.assertFalse(any(path.startswith("/api/") for path in paths))

    def test_invalid_documents_fail_loading(self):
        cases = {}
        unsupported = copy.deepcopy(self.document)
        unsupported["openapi"] = "3.0.3"
        cases["unsupported.yaml"] = unsupported
        duplicate = copy.deepcopy(self.document)
        first = next(iter(duplicate["paths"].values()))
        method, operation = next(iter(first.items()))
        duplicate["paths"]["/duplicate"] = {method: operation}
        cases["duplicate.yaml"] = duplicate
        dangling = copy.deepcopy(self.document)
        dangling["paths"]["/api/verify"]["post"]["responses"]["200"]["content"]["application/json"]["schema"] = {"$ref": "#/components/schemas/Missing"}
        cases["dangling.yaml"] = dangling
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename, document in cases.items():
                path = root / filename
                path.write_text(yaml.safe_dump(document, allow_unicode=True), encoding="utf-8")
                with self.subTest(filename=filename), self.assertRaises(ValueError):
                    viewer.load_document(path)
            (root / "bad.yaml").write_text("paths: [", encoding="utf-8")
            with self.assertRaises(ValueError):
                viewer.load_document(root / "bad.yaml")
            with self.assertRaises(ValueError):
                viewer.load_document(root / "missing.yaml")


if __name__ == "__main__":
    unittest.main()
