"""Test the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from hosted_fastapi.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Hosted FastAPI"}


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_app_metadata():
    """Test the app metadata is correct."""
    assert app.title == "Hosted FastAPI"
    assert app.description == "A FastAPI application for hosting and deployment"
    assert app.version == "0.1.0"