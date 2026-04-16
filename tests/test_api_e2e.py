"""End-to-end API tests using FastAPI TestClient.

These tests use mock mode for GPU and scraper but test the full API flow:
- Channel CRUD
- Webhook reception
- Video/Clip query endpoints
- PubSubHubbub verification
"""
import json
import os
import socket

import pytest
from fastapi.testclient import TestClient


def _pg_available():
    """Check if Postgres is reachable at localhost:5632."""
    try:
        s = socket.create_connection(("localhost", 5632), timeout=1)
        s.close()
        return True
    except OSError:
        return False


requires_infra = pytest.mark.skipif(
    not _pg_available(),
    reason="Postgres/Redis/MinIO not available (run on VPS with docker compose up)",
)

# Force mock mode
os.environ["GPU_API_MOCK"] = "true"
os.environ["SCRAPER_AGENT_MOCK"] = "true"
os.environ["APP_ENV"] = "development"
os.environ["APP_BASE_URL"] = "http://localhost:8080"
os.environ.setdefault("DATABASE_URL", "postgres://opus:test@localhost:5632/opus_clone")
os.environ.setdefault("REDIS_URL", "redis://:test@localhost:6479")
os.environ.setdefault("REDIS_PASSWORD", "test")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9600")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
os.environ.setdefault("WEBHOOK_SHARED_SECRET", "")

from opus_clone.api.main import app

client = TestClient(app)


# ========== Health ==========

class TestHealth:
    def test_health_endpoint_returns_200(self):
        """Health endpoint is accessible."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


# ========== Channels ==========

class TestChannels:
    @requires_infra
    def test_create_channel(self):
        """Create a YouTube channel."""
        response = client.post("/api/channels", json={
            "platform": "youtube",
            "external_id": "UCtest123",
            "username": "testchannel",
            "display_name": "Test Channel",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "youtube"
        assert data["external_id"] == "UCtest123"
        assert data["username"] == "testchannel"
        assert data["is_active"] is True

    @requires_infra
    def test_list_channels(self):
        response = client.get("/api/channels")
        assert response.status_code == 200

    def test_create_channel_validation(self):
        """Invalid platform is rejected."""
        response = client.post("/api/channels", json={
            "platform": "twitch",
            "external_id": "xxx",
            "username": "test",
        })
        assert response.status_code == 422  # Validation error


# ========== PubSubHubbub ==========

class TestPubSubHubbub:
    def test_pubsub_verify_challenge(self):
        """YouTube PubSubHubbub hub verification returns challenge."""
        response = client.get(
            "/v1/webhooks/youtube-pubsub",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test_challenge_12345",
                "hub.topic": "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UCtest",
            },
        )
        assert response.status_code == 200
        assert response.text == "test_challenge_12345"

    def test_pubsub_verify_wrong_mode(self):
        response = client.get(
            "/v1/webhooks/youtube-pubsub",
            params={"hub.mode": "unsubscribe", "hub.challenge": "xxx"},
        )
        assert response.status_code == 404

    @requires_infra
    def test_pubsub_notification(self):
        """YouTube PubSubHubbub notification is accepted."""
        atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
  <entry>
    <yt:videoId>dQw4w9WgXcQ</yt:videoId>
    <yt:channelId>UCtest123</yt:channelId>
    <title>Test Video Title</title>
    <published>2026-04-16T12:00:00Z</published>
  </entry>
</feed>"""
        response = client.post(
            "/v1/webhooks/youtube-pubsub",
            content=atom_xml.encode(),
            headers={"Content-Type": "application/atom+xml"},
        )
        assert response.status_code == 200


# ========== GPU Webhooks ==========

class TestGpuWebhooks:
    @requires_infra
    def test_asr_webhook(self):
        """ASR webhook is accepted."""
        payload = {
            "job_id": "tr_test123",
            "type": "transcription",
            "status": "completed",
            "language": "pt",
            "duration_s": 180.5,
            "result_file_id": "file_xyz",
        }
        response = client.post(
            "/v1/webhooks/asr",
            json=payload,
        )
        assert response.status_code == 200

    @requires_infra
    def test_analyze_webhook(self):
        """Analyze webhook is accepted."""
        payload = {
            "job_id": "va_test456",
            "status": "completed",
            "result_file_id": "file_abc",
        }
        response = client.post(
            "/v1/webhooks/analyze",
            json=payload,
        )
        assert response.status_code == 200

    @requires_infra
    def test_render_webhook(self):
        """Render webhook is accepted."""
        payload = {
            "job_id": "rn_test789",
            "status": "completed",
            "result_file_id": "file_clip",
            "result_url": "http://gpu/outputs/rn_test789.mp4",
            "duration_s": 45.0,
        }
        response = client.post(
            "/v1/webhooks/render",
            json=payload,
        )
        assert response.status_code == 200


# ========== Videos ==========

class TestVideos:
    @requires_infra
    def test_list_videos(self):
        response = client.get("/api/videos")
        assert response.status_code == 200

    @requires_infra
    def test_get_video_not_found(self):
        response = client.get("/api/videos/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


# ========== Clips ==========

class TestClips:
    @requires_infra
    def test_list_clips(self):
        response = client.get("/api/clips")
        assert response.status_code == 200

    @requires_infra
    def test_get_clip_not_found(self):
        response = client.get("/api/clips/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


# ========== Metrics ==========

class TestMetrics:
    def test_metrics_endpoint(self):
        """Prometheus metrics endpoint is accessible."""
        response = client.get("/metrics")
        assert response.status_code == 200
