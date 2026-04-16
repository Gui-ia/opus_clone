import os

import pytest

# Ensure mock mode
os.environ["GPU_API_MOCK"] = "true"


@pytest.mark.asyncio
async def test_gpu_client_mock_upload():
    from opus_clone.clients.gpu_api import GpuApiClient

    client = GpuApiClient()
    assert client.mock is True

    result = await client.upload_file(b"fake-video-bytes", "test.mp4")
    assert result.file_id == "mock-file-id-001"
    assert result.filename == "test.mp4"


@pytest.mark.asyncio
async def test_gpu_client_mock_transcribe():
    from opus_clone.clients.gpu_api import GpuApiClient
    from opus_clone.models.gpu_api import TranscriptionRequest

    client = GpuApiClient()
    req = TranscriptionRequest(file_id="test-file")
    job_id = await client.transcribe(req)
    assert job_id == "mock-transcription-job-001"


@pytest.mark.asyncio
async def test_gpu_client_mock_analyze():
    from opus_clone.clients.gpu_api import GpuApiClient
    from opus_clone.models.gpu_api import VideoAnalyzeRequest

    client = GpuApiClient()
    req = VideoAnalyzeRequest(file_id="test-file")
    job_id = await client.analyze_video(req)
    assert job_id == "mock-analysis-job-001"


@pytest.mark.asyncio
async def test_gpu_client_mock_chat():
    from opus_clone.clients.gpu_api import GpuApiClient
    from opus_clone.models.gpu_api import ChatCompletionRequest, ChatMessage

    client = GpuApiClient()
    req = ChatCompletionRequest(
        messages=[ChatMessage(role="user", content="Hello")],
    )
    response = await client.chat_completions(req)
    assert len(response.choices) == 1
    assert "Mock" in response.choices[0].message.content


@pytest.mark.asyncio
async def test_gpu_client_mock_render():
    from opus_clone.clients.gpu_api import GpuApiClient
    from opus_clone.models.gpu_api import RenderRequest

    client = GpuApiClient()
    req = RenderRequest(source_file_id="test-file", edl={})
    job_id = await client.render_video(req)
    assert job_id == "mock-render-job-001"


@pytest.mark.asyncio
async def test_gpu_client_mock_job_status():
    from opus_clone.clients.gpu_api import GpuApiClient

    client = GpuApiClient()
    status = await client.get_job_status("audio/transcriptions", "test-job-123")
    assert status.status == "completed"
    assert status.job_id == "test-job-123"


@pytest.mark.asyncio
async def test_gpu_client_mock_download():
    from opus_clone.clients.gpu_api import GpuApiClient

    client = GpuApiClient()
    data = await client.download_output("test.mp4")
    assert data == b"mock-file-content"
