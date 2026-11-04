"""Read-only Swagger viewer for the independent business API contract."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from openapi_spec_validator import validate
import yaml


CONTRACT_PATH = Path(__file__).with_name("openapi.yaml")
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def load_document(path: Path) -> dict:
    """Load and validate an OpenAPI 3.1 document without creating business routes."""
    try:
        with path.open(encoding="utf-8") as stream:
            document = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Unable to load OpenAPI document: {path}") from exc

    if not isinstance(document, dict) or not document.get("openapi", "").startswith("3.1."):
        raise ValueError("The document must use OpenAPI 3.1")

    operation_ids = [
        operation.get("operationId")
        for path_item in document.get("paths", {}).values()
        for method, operation in path_item.items()
        if method in HTTP_METHODS
    ]
    if any(not identifier for identifier in operation_ids):
        raise ValueError("Every operation must have an operationId")
    if len(operation_ids) != len(set(operation_ids)):
        raise ValueError("operationId values must be unique")

    try:
        validate(document)
    except Exception as exc:
        raise ValueError("Invalid OpenAPI document or unresolved reference") from exc
    return document


DOCUMENT_TEXT = CONTRACT_PATH.read_text(encoding="utf-8")
DOCUMENT = load_document(CONTRACT_PATH)

app = FastAPI(
    title="反诈系统接口文档预览",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    swagger_ui_parameters={"supportedSubmitMethods": []},
)


def contract_openapi() -> dict:
    return DOCUMENT


app.openapi = contract_openapi


@app.get("/openapi.yaml", include_in_schema=False)
def get_openapi_yaml() -> Response:
    return Response(content=DOCUMENT_TEXT, media_type="application/yaml")
