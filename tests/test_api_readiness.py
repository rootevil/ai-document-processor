"""
Tests for frontend-facing API contracts and CORS configuration.

These tests verify that React can communicate with the backend
and that the review endpoints publish typed response contracts.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

FRONTEND_ORIGIN = "http://localhost:5173"


def test_frontend_origin_passes_cors_preflight():
    """The configured React development origin must be permitted."""

    response = client.options(
        "/api/v1/documents/",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200

    assert (
        response.headers.get("access-control-allow-origin")
        == FRONTEND_ORIGIN
    )


def test_unapproved_origin_is_not_allowed():
    """An origin outside the allowlist must not receive CORS permission."""

    response = client.options(
        "/api/v1/documents/",
        headers={
            "Origin": "http://unapproved.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert (
        response.headers.get("access-control-allow-origin")
        is None
    )


def test_review_endpoints_publish_response_models():
    """The review endpoints must expose typed response schemas in OpenAPI."""

    schema = app.openapi()
    paths = schema["paths"]

    base = (
        "/api/v1/documents/{document_id}"
        "/attempts/{attempt_id}"
    )

    expected = {
        ("get", base + "/extraction"): "OriginalAttemptExtractionResponse",
        ("post", base + "/reviews"): "ReviewSubmissionResponse",
        ("get", base + "/reviews"): "ReviewHistoryResponse",
        ("get", base + "/reviews/latest"): "LatestReviewsResponse",
        (
            "get",
            base + "/review-aware-extraction",
        ): "ReviewAwareExtractionResponse",
    }

    for (method, path), expected_model in expected.items():
        operation = paths[path][method]

        response_code = "201" if method == "post" else "200"

        response_schema = (
            operation["responses"][response_code]
            ["content"]["application/json"]["schema"]
        )

        assert response_schema["$ref"].endswith(
            f"/{expected_model}"
        )