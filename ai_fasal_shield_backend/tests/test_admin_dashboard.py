from fastapi.testclient import TestClient

from app.main import app


def test_admin_dashboard_is_available():
    client = TestClient(app)
    response = client.get("/admin")
    assert response.status_code == 200
    assert "AI Fasal Shield" in response.text
    assert "Farmer Reports" in response.text
    assert "Outbreak Alerts" in response.text
    assert "image is optional" in response.text.lower()
    assert "Mark Valid & Recheck Outbreak" in response.text
    assert "Punjabi (Shahmukhi)" in response.text
