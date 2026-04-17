from pydantic import BaseModel


class LoudnormConfig(BaseModel):
    I: float = -14
    TP: float = -1
    LRA: float = 9


class OutputSpec(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: int = 30
    codec: str = "h264_nvenc"
    preset: str = "p6"
    cq: int = 19
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    loudnorm: LoudnormConfig = LoudnormConfig()


class SourceDimensions(BaseModel):
    width: int = 1920
    height: int = 1080


class ReframeTrack(BaseModel):
    start_ms: int
    end_ms: int
    cx_ratio: float
    cy_ratio: float
    scale: float = 1.0


class SmoothingConfig(BaseModel):
    type: str = "ema"
    alpha: float = 0.15


class ReframeConfig(BaseModel):
    mode: str = "active_speaker"
    source_dimensions: SourceDimensions = SourceDimensions()
    tracks: list[ReframeTrack] = []
    smoothing: SmoothingConfig = SmoothingConfig()
    min_hold_ms: int = 800


class CaptionWord(BaseModel):
    word: str
    start_ms: int
    end_ms: int
    emphasis: bool = False
    color: str | None = None


class CaptionEmoji(BaseModel):
    time_ms: int
    emoji: str
    duration_ms: int = 1200
    size_px: int = 140


class CaptionPosition(BaseModel):
    v_anchor: str = "middle"
    v_offset: int = 0


class CaptionConfig(BaseModel):
    enabled: bool = True
    style: str = "viral_karaoke"
    font: str = "Montserrat Black"
    font_size: int = 120
    color_palette: list[str] = [
        "#FFFFFF",
        "#FFD700",
        "#FF6B00",
        "#00FF88",
        "#00BFFF",
    ]
    stroke_color: str = "#000000"
    stroke_width: int = 4
    words: list[CaptionWord] = []
    emojis: list[CaptionEmoji] = []
    max_words_per_page: int = 3
    max_gap_s: float = 0.35
    position: CaptionPosition = CaptionPosition(v_anchor="middle", v_offset=120)


class ZoomConfig(BaseModel):
    start_ms: int
    end_ms: int
    scale: float = 1.15
    ease: str = "ease_in_out"


class BrollOverlay(BaseModel):
    start_ms: int
    end_ms: int
    source_file_id: str
    mode: str = "fullscreen"
    audio_duck_db: float = -12


class SFX(BaseModel):
    time_ms: int
    source_file_id: str
    volume: float = 0.5


class BackgroundMusic(BaseModel):
    source_file_id: str
    volume: float = 0.12
    loop: bool = True
    fade_in_ms: int = 500
    fade_out_ms: int = 1000


class WatermarkConfig(BaseModel):
    source_file_id: str
    position: str = "top_right"
    margin_px: int = 36
    width_px: int = 180
    opacity: float = 0.85


class TeaserConfig(BaseModel):
    enabled: bool = False
    start_ms: int = 0
    end_ms: int = 0
    text: str = ""


class EDL(BaseModel):
    clip_start_ms: int
    clip_end_ms: int
    output_spec: OutputSpec = OutputSpec()
    reframe: ReframeConfig = ReframeConfig()
    captions: CaptionConfig = CaptionConfig()
    zooms: list[ZoomConfig] = []
    broll_overlays: list[BrollOverlay] = []
    sfx: list[SFX] = []
    background_music: BackgroundMusic | None = None
    watermark: WatermarkConfig | None = None
    teaser: TeaserConfig | None = None
