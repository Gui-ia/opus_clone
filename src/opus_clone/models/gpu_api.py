from pydantic import BaseModel, Field


# ========== File Upload ==========

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str | None = None
    size_bytes: int | None = None


# ========== Transcription ==========

class TranscriptionRequest(BaseModel):
    file_id: str
    language: str = "pt"
    diarize: bool = True
    word_timestamps: bool = True
    vad_filter: bool = True
    min_speakers: int = 1
    max_speakers: int = 5
    webhook_url: str | None = None


class TranscriptionWord(BaseModel):
    word: str
    start: float
    end: float
    score: float | None = None
    speaker: str | None = None


class TranscriptionSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    speaker: str | None = None
    words: list[TranscriptionWord] = []


class TranscriptionResult(BaseModel):
    language: str
    duration: float
    segments: list[TranscriptionSegment]
    speakers: list[str] = []


class TranscriptionWebhook(BaseModel):
    job_id: str
    type: str = "transcription"
    status: str
    language: str | None = None
    duration_s: float | None = None
    result_file_id: str | None = None
    result_url: str | None = None
    speakers_count: int | None = None
    elapsed_seconds: float | None = None
    error: str | None = None


# ========== Video Analysis ==========

class VideoAnalyzeRequest(BaseModel):
    file_id: str
    fps_sample: int = 2
    detect_scenes: bool = True
    detect_faces: bool = True
    detect_active_speaker: bool = True
    webhook_url: str | None = None


class ActiveSpeakerEntry(BaseModel):
    start_ms: int
    end_ms: int
    face_id: str
    confidence: float
    bbox_normalized: list[float] = Field(default_factory=list)


class SceneEntry(BaseModel):
    start: float
    end: float
    dominant_faces: list[str] = []


class FaceEntry(BaseModel):
    face_id: str
    appearances: list[dict] = []


class AnalysisResult(BaseModel):
    duration: float
    scenes: list[SceneEntry] = []
    faces: list[FaceEntry] = []
    active_speaker_timeline: list[ActiveSpeakerEntry] = []
    keyframes: list[dict] = []


class VideoAnalyzeWebhook(BaseModel):
    job_id: str
    status: str
    result_file_id: str | None = None
    summary: dict | None = None
    error: str | None = None


# ========== Render ==========

class RenderRequest(BaseModel):
    source_file_id: str
    edl: dict
    webhook_url: str | None = None


class RenderWebhook(BaseModel):
    job_id: str
    status: str
    result_file_id: str | None = None
    result_url: str | None = None
    duration_s: float | None = None
    file_size_bytes: int | None = None
    dimensions: str | None = None
    elapsed_seconds: float | None = None
    error: str | None = None


# ========== Chat Completions ==========

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "qwen3.5-35b"
    messages: list[ChatMessage]
    max_tokens: int = 4000
    temperature: float = 0.7
    top_p: float = 0.9


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str | None = None


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str | None = None
    choices: list[ChatCompletionChoice] = []
    usage: ChatCompletionUsage | None = None


# ========== Job Status ==========

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float | None = None
    result_url: str | None = None
    error: str | None = None
