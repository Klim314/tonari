"""Tests for prompt validation (schemas and business logic)."""

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Prompt, PromptVersion


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_prompt():
    """Create a test prompt."""
    with SessionLocal() as db:
        prompt = Prompt(name="Test Prompt", description="A test prompt")
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        return prompt


class TestPromptCreateValidation:
    """Test validation for creating prompts."""

    def test_create_prompt_success(self, client):
        """Should create prompt with valid data."""
        response = client.post(
            "/prompts/", json={"name": "My Prompt", "description": "A helpful prompt"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Prompt"
        assert data["description"] == "A helpful prompt"

    def test_create_prompt_empty_name(self, client):
        """Should reject prompt with empty name."""
        response = client.post("/prompts/", json={"name": "", "description": "A helpful prompt"})
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data
        assert any(e["field"] == "name" for e in data["errors"])

    def test_create_prompt_whitespace_only_name(self, client):
        """Should reject prompt with whitespace-only name."""
        response = client.post("/prompts/", json={"name": "   ", "description": "A helpful prompt"})
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data

    def test_create_prompt_name_too_long(self, client):
        """Should reject prompt with name exceeding max length."""
        response = client.post(
            "/prompts/",
            json={
                "name": "x" * 300,  # Exceeds 255 limit
                "description": "A helpful prompt",
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data
        assert any(e["field"] == "name" for e in data["errors"])

    def test_create_prompt_description_too_long(self, client):
        """Should reject prompt with description exceeding max length."""
        response = client.post(
            "/prompts/",
            json={
                "name": "My Prompt",
                "description": "x" * 2500,  # Exceeds 2000 limit
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data

    def test_create_prompt_trims_whitespace(self, client):
        """Should trim whitespace from name and description."""
        response = client.post(
            "/prompts/", json={"name": "  My Prompt  ", "description": "  A helpful prompt  "}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Prompt"
        assert data["description"] == "A helpful prompt"


class TestPromptUpdateValidation:
    """Test validation for updating prompts."""

    def test_update_prompt_name_success(self, client, test_prompt):
        """Should update prompt name."""
        response = client.patch(f"/prompts/{test_prompt.id}", json={"name": "Updated Name"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_update_prompt_no_fields(self, client, test_prompt):
        """Should reject update with no fields."""
        response = client.patch(
            f"/prompts/{test_prompt.id}", json={"name": None, "description": None}
        )
        assert response.status_code == 422
        data = response.json()
        # Error can be in detail or in errors array
        error_msg = data.get("detail", "") + " ".join(
            e.get("message", "") for e in data.get("errors", [])
        )
        assert "At least one field" in error_msg

    def test_update_prompt_empty_name(self, client, test_prompt):
        """Should reject prompt with empty name."""
        response = client.patch(f"/prompts/{test_prompt.id}", json={"name": ""})
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data

    def test_update_prompt_trims_whitespace(self, client, test_prompt):
        """Should trim whitespace from name."""
        response = client.patch(f"/prompts/{test_prompt.id}", json={"name": "  Updated Name  "})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"


class TestPromptVersionValidation:
    """Test validation for prompt versions."""

    def test_create_version_success(self, client, test_prompt):
        """Should create version with valid data."""
        response = client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={"model": "gpt-4o", "template": "Answer the question: {question}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "gpt-4o"
        assert data["template"] == "Answer the question: {question}"

    def test_create_version_invalid_model(self, client, test_prompt):
        """Should reject version with invalid model."""
        response = client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={"model": "gpt-999-super", "template": "Answer the question: {question}"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data
        error = next(e for e in data["errors"] if e["field"] == "model")
        assert "Invalid model" in error["message"]
        assert "Supported models" in error["message"]

    def test_create_version_empty_model(self, client, test_prompt):
        """Should reject version with empty model."""
        response = client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={"model": "", "template": "Answer the question: {question}"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data

    def test_create_version_empty_template(self, client, test_prompt):
        """Should reject version with empty template."""
        response = client.post(
            f"/prompts/{test_prompt.id}/versions", json={"model": "gpt-4o", "template": ""}
        )
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data

    def test_create_version_invalid_template_syntax(self, client, test_prompt):
        """Should reject version with invalid f-string syntax."""
        response = client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={
                "model": "gpt-4o",
                "template": "Answer this: {unclosed",  # Missing closing brace
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data
        error = next(e for e in data["errors"] if e["field"] == "template")
        assert "syntax" in error["message"].lower()

    def test_create_version_trims_model(self, client, test_prompt):
        """Should trim whitespace from model."""
        response = client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={"model": "  gpt-4o  ", "template": "Answer: {q}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "gpt-4o"

    def test_create_version_duplicate_as_latest(self, client, test_prompt):
        """Should reject version identical to latest version."""
        # Create first version
        resp1 = client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={"model": "gpt-4o", "template": "Answer: {q}"},
        )
        assert resp1.status_code == 200

        # Try to create identical version
        response = client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={"model": "gpt-4o", "template": "Answer: {q}"},
        )
        assert response.status_code == 422
        data = response.json()
        error_msg = data.get("detail", "") + " ".join(
            e.get("message", "") for e in data.get("errors", [])
        )
        assert "must differ from the latest version" in error_msg

    def test_create_version_different_model_allowed(self, client, test_prompt):
        """Should allow version with different model from latest."""
        # Create first version
        client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={"model": "gpt-4o", "template": "Answer: {q}"},
        )

        # Create version with different model
        response = client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={"model": "gpt-4o-mini", "template": "Answer: {q}"},
        )
        assert response.status_code == 200

    def test_create_version_different_template_allowed(self, client, test_prompt):
        """Should allow version with different template from latest."""
        # Create first version
        client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={"model": "gpt-4o", "template": "Answer: {q}"},
        )

        # Create version with different template
        response = client.post(
            f"/prompts/{test_prompt.id}/versions",
            json={"model": "gpt-4o", "template": "Please answer this: {q}"},
        )
        assert response.status_code == 200


class TestValidationErrorFormat:
    """Test error response format."""

    def test_error_response_structure(self, client):
        """Should return structured error response."""
        response = client.post(
            "/prompts/",
            json={
                "name": "",
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "errors" in data
        assert isinstance(data["errors"], list)
        for error in data["errors"]:
            assert "field" in error
            assert "message" in error
            assert "type" in error

    def test_multiple_field_errors(self, client, test_prompt):
        """Should report multiple field errors."""
        response = client.post(
            f"/prompts/{test_prompt.id}/versions", json={"model": "", "template": ""}
        )
        assert response.status_code == 422
        data = response.json()
        assert len(data["errors"]) >= 2
        fields = {e["field"] for e in data["errors"]}
        assert "model" in fields
        assert "template" in fields
