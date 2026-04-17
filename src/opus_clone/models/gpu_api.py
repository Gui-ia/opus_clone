from pydantic import BaseModel, Field


# ========== File Upload ==========

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str | None = None
    content_type: str | None = None
    size: int | None = None
    url: str | None = None
    created_at: float | None = None


# ========== Transcription ==========

class TranscriptionRequest(BaseModel):
    file_id: str
    language: str = "pt"
    diarize: bool = True
    word_timestamps: bool = True
    vad_filter: bool = True
    min_speakers: int = 1
    max_speakers: int = 5
    beam_size: int = 5
    condition_on_previous_text: bool = False
    initial_prompt: str | None = None
    webhook_url: str | None = None


class TranscriptionWord(BaseModel):
    word: str
    start: float | None = None
    end: float | None = None
    score: float | None = None
    speaker: str | None = None


class TranscriptionSegment(BaseModel):
    id: int | None = None
    start: float
    end: float
    text: str
    speaker: str | None = None
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    words: list[TranscriptionWord] = []


class TranscriptionResult(BaseModel):
    language: str = "pt"
    language_probability: float | None = None
    duration: float = 0.0
    segments: list[TranscriptionSegment] = []
    speakers: list[str] = []


# ========== Video Analysis ==========

class VideoAnalyzeRequest(BaseModel):
    file_id: str
    detect_scenes: bool = True
    detect_faces: bool = True
    detect_active_speaker: bool = False
    scene_threshold: float = 27.0
    face_det_score: float = 0.5
    frames_per_scene: int = 3
    webhook_url: str | None = None


class SceneEntry(BaseModel):
    scene_idx: int
    start_s: float
    end_s: float
    duration_s: float = 0.0


class FaceDetection(BaseModel):
    scene_idx: int
    time_s: float
    bbox: list[float] = Field(default_factory=list)
    det_score: float = 0.0
    identity_id: int = 0


class IdentityEntry(BaseModel):
    identity_id: int
    detections: int = 0
    scenes: list[int] = Field(default_factory=list)


class ActiveSpeakerEntry(BaseModel):
    scene_idx: int
    time_s: float
    identity_id: int
    bbox: list[float] = Field(default_factory=list)
    score: float = 0.0


class AnalysisResult(BaseModel):
    job_id: str | None = None
    duration_s: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    scenes: list[SceneEntry] = []
    scenes_count: int = 0
    faces: list[FaceDetection] = []
    identities: list[IdentityEntry] = []
    identities_count: int = 0
    active_speaker: list[ActiveSpeakerEntry] = []
    elapsed_seconds: float = 0.0
    analyzed_at: float | None = None


# ========== Render ==========

class RenderRequest(BaseModel):
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
    content: str | None = None
    tool_calls: list | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "qwen3.5-35b"
    messages: list[ChatMessage]
    max_tokens: int = 4000
    temperature: float = 0.7
    top_p: float = 0.9
    system_prompt: str | None = None
    stream: bool = False
    tools: list | None = None
    tool_choice: str | dict | None = None


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
    object: str | None = None
    created: int | None = None
    model: str | None = None
    choices: list[ChatCompletionChoice] = []
    usage: ChatCompletionUsage | None = None


# ========== Job Status ==========

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float | None = None
    result_file_id: str | None = None
    result_url: str | None = None
    error: str | None = None
    # Transcription-specific
    language: str | None = None
    duration_s: float | None = None
    speakers_count: int | None = None
    # Analysis-specific
    scenes_count: int | None = None
    faces_count: int | None = None
    # Render-specific
    output_size_mb: float | None = None
    # Common
    elapsed_seconds: float | None = None


# ========== Webhooks ==========

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


class VideoAnalyzeWebhook(BaseModel):
    job_id: str
    status: str
    result_file_id: str | None = None
    result_url: str | None = None
    duration_s: float | None = None
    scenes_count: int | None = None
    faces_count: int | None = None
    elapsed_seconds: float | None = None
    error: str | None = None
