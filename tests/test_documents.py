
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_document():
    file_content = b"Sample invoice content"

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                file_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "filename": "invoice.pdf",
        "content_type": "application/pdf",
        "message": "Document received successfully",
    }
