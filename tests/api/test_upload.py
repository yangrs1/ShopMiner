"""Tests for image upload API."""
import io
import os
from app.extensions import db
from app.models.analytics import Review


class TestUpload:
    """POST /api/v1/upload"""

    def test_upload_valid_image(self, client, admin_headers):
        """Upload valid PNG image returns 200 with URL."""
        data = dict(file=(io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100), 'test.png'))
        resp = client.post("/api/v1/upload", data=data, content_type='multipart/form-data',
                           headers=admin_headers)
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["code"] == 200
        assert json["data"]["url"].startswith("/static/uploads/")

    def test_upload_invalid_type(self, client, admin_headers):
        """Upload .txt file returns 400."""
        data = dict(file=(io.BytesIO(b'not an image'), 'test.txt'))
        resp = client.post("/api/v1/upload", data=data, content_type='multipart/form-data',
                           headers=admin_headers)
        assert resp.status_code == 400

    def test_upload_no_file(self, client, admin_headers):
        """No file in request returns 400."""
        resp = client.post("/api/v1/upload", headers=admin_headers)
        assert resp.status_code == 400

    def test_upload_unauthorized(self, client):
        """No auth token returns 401."""
        data = dict(file=(io.BytesIO(b'\x89PNG\r\n\x1a\n'), 'test.png'))
        resp = client.post("/api/v1/upload", data=data, content_type='multipart/form-data')
        assert resp.status_code == 401
