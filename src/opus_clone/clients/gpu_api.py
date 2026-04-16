import json
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from opus_clone.config import get_settings
from opus_clone.logging import get_logger
from opus_clone.models.gpu_api import (
    AnalysisResult,
    ChatCompletionRequest,
    ChatCompletionResponse,
    FileUploadResponse,
    JobStatusResponse,
    RenderRequest,
    TranscriptionRequest,
    TranscriptionResult,
    VideoAnalyzeRequest,
)

logger = get_logger("gpu_api")

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures"


class RetryableError(Exception):
    pass


class GpuApiClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.gpu_api_url
        self.mock = self.settings.gpu_api_mock

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.settings.gpu_api_key}"},
            timeout=httpx.Timeout(self.settings.gpu_api_timeout_s),
        )

    async def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code == 503:
            retry_after = response.headers.get("Retry-After", "30")
            logger.warning("gpu_api_503", retry_after=retry_after)
            raise RetryableError(f"GPU API 503, retry after {retry_after}s")
        if response.status_code >= 500:
            raise RetryableError(f"GPU API {response.status_code}")
        response.raise_for_status()
        return response.json()

    def _load_fixture(self, name: str) -> dict:
        fixture_path = FIXTURES_DIR / name
        if fixture_path.exists():
            return json.loads(fixture_path.read_text(encoding="utf-8"))
        return {}

    # ========== File Upload ==========

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
    )
    async def upload_file(self, file_bytes: bytes, filename: str) -> FileUploadResponse:
        if self.mock:
            return FileUploadResponse(file_id="mock-file-id-001", filename=filename, size_bytes=len(file_bytes))

        async with self._client() as client:
            response = await client.post(
                "/v1/files/upload",
                files={"file": (filename, file_bytes)},
            )
            data = await self._handle_response(response)
            return FileUploadResponse(**data)

    # ========== Transcription ==========

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
    )
    async def transcribe(self, request: TranscriptionRequest) -> str:
        """Dispatches transcription job, returns job_id."""
        if self.mock:
            return "mock-transcription-job-001"

        async with self._client() as client:
            response = await client.post(
                "/v1/audio/transcriptions",
                json=request.model_dump(),
            )
            data = await self._handle_response(response)
            return data.get("job_id", data.get("id", ""))

    async def get_transcription_result(self, result_url: str) -> TranscriptionResult:
        if self.mock:
            fixture = self._load_fixture("sample_transcript.json")
            return TranscriptionResult(**fixture) if fixture else TranscriptionResult(language="pt", duration=180.0, segments=[])

        async with self._client() as client:
            response = await client.get(result_url)
            data = await self._handle_response(response)
            return TranscriptionResult(**data)

    # ========== Video Analysis ==========

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
    )
    async def analyze_video(self, request: VideoAnalyzeRequest) -> str:
        """Dispatches analysis job, returns job_id."""
        if self.mock:
            return "mock-analysis-job-001"

        async with self._client() as client:
            response = await client.post(
                "/v1/video/analyze",
                json=request.model_dump(),
            )
            data = await self._handle_response(response)
            return data.get("job_id", data.get("id", ""))

    async def get_analysis_result(self, result_url: str) -> AnalysisResult:
        if self.mock:
            fixture = self._load_fixture("sample_analyze.json")
            return AnalysisResult(**fixture) if fixture else AnalysisResult(duration=180.0)

        async with self._client() as client:
            response = await client.get(result_url)
            data = await self._handle_response(response)
            return AnalysisResult(**data)

    # ========== Chat Completions ==========

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
    )
    async def chat_completions(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if self.mock:
            return ChatCompletionResponse(
                id="mock-chat-001",
                choices=[{
                    "index": 0,
                    "message": {"role": "assistant", "content": "Mock LLM response"},
                    "finish_reason": "stop",
                }],
            )

        async with self._client() as client:
            response = await client.post(
                "/v1/chat/completions",
                json=request.model_dump(),
            )
            data = await self._handle_response(response)
            return ChatCompletionResponse(**data)

    # ========== Render ==========

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
    )
    async def render_video(self, request: RenderRequest) -> str:
        """Dispatches render job, returns job_id."""
        if self.mock:
            return "mock-render-job-001"

        async with self._client() as client:
            response = await client.post(
                "/v1/video/render",
                json=request.model_dump(),
            )
            data = await self._handle_response(response)
            return data.get("job_id", data.get("id", ""))

    # ========== Image Generation ==========

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
    )
    async def generate_image(self, prompt: str, **kwargs) -> str:
        """Returns output image URL."""
        if self.mock:
            return "http://mock/outputs/thumbnail_001.png"

        async with self._client() as client:
            response = await client.post(
                "/v1/images/generations",
                json={"prompt": prompt, **kwargs},
            )
            data = await self._handle_response(response)
            return data.get("url", data.get("result_url", ""))

    # ========== Job Status (polling) ==========

    async def get_job_status(self, job_type: str, job_id: str) -> JobStatusResponse:
        if self.mock:
            return JobStatusResponse(job_id=job_id, status="completed", result_url=f"http://mock/outputs/{job_id}.json")

        async with self._client() as client:
            response = await client.get(f"/v1/{job_type}/status/{job_id}")
            data = await self._handle_response(response)
            return JobStatusResponse(**data)

    # ========== Download Output ==========

    async def download_output(self, filename: str) -> bytes:
        if self.mock:
            return b"mock-file-content"

        async with self._client() as client:
            response = await client.get(f"/outputs/{filename}")
            response.raise_for_status()
            return response.content
