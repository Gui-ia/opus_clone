"""
Schema Pydantic para o EDL do render worker.

Substitui o model EDL atual no worker. Mantém retrocompatibilidade
com o formato antigo (captions como lista) e adiciona os campos novos.

O worker já usa pysubs2 pra gerar ASS — os campos de styling mapeiam
direto pras propriedades ASS (FontName, FontSize, PrimaryColour,
OutlineColour, Outline, Alignment, MarginV).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ========== Output ==========

class OutputSpec(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: int = 30
    video_codec: str = "h264_nvenc"


# ========== Clips ==========

class ClipEntry(BaseModel):
    file_id: str
    in_point: float
    out_point: float
    volume: float = 1.0
    label: str | None = None  # ex: "teaser" — o worker pode usar pra aplicar efeitos


# ========== Loudnorm ==========

class LoudnormSpec(BaseModel):
    enabled: bool = True
    target_i: float = -14.0
    target_lra: float = 9.0
    target_tp: float = -1.0


# ========== Audio (background track — já existe) ==========

class AudioSpec(BaseModel):
    file_id: str
    volume: float = 0.3


# ========== Captions ==========
# pysubs2 ASS mapping:
#   font       → Style.fontname
#   font_size  → Style.fontsize
#   color      → Style.primarycolor  (hex → ASS &HBBGGRR&)
#   stroke_color → Style.outlinecolor
#   stroke_width → Style.outline
#   position.v_anchor → Style.alignment (middle=5, bottom=2, top=8)
#   position.v_offset → Style.marginv

class CaptionPosition(BaseModel):
    v_anchor: str = "middle"  # "top" | "middle" | "bottom"
    v_offset: int = 120       # px abaixo do anchor


class CaptionSegment(BaseModel):
    start: float
    end: float
    text: str
    color: str | None = None  # hex ex: "#FFFFFF" — se None, usa style default


class CaptionsConfig(BaseModel):
    style: str = "viral_karaoke"
    font: str = "Montserrat Black"
    font_size: int = 120
    stroke_color: str = "#000000"
    stroke_width: int = 4
    position: CaptionPosition = CaptionPosition()
    segments: list[CaptionSegment] = []


# ========== Reframe ==========
# O worker já faz crop EMA via sendcmd. Campos:
#   source_width/height → calcula crop_w = out_h * (9/16), crop_x = cx * source_w - crop_w/2
#   keyframes → sendcmd com crop=x:y:w:h interpolado por EMA(alpha)

class ReframeSmoothing(BaseModel):
    type: str = "ema"
    alpha: float = 0.15


class ReframeKeyframe(BaseModel):
    start: float
    end: float
    cx: float       # 0.0-1.0 normalizado no source
    cy: float       # 0.0-1.0 normalizado no source
    scale: float = 1.0


class ReframeConfig(BaseModel):
    source_width: int = 1920
    source_height: int = 1080
    mode: str = "active_speaker"
    smoothing: ReframeSmoothing = ReframeSmoothing()
    min_hold_ms: int = 800
    keyframes: list[ReframeKeyframe] = []


# ========== Zooms ==========
# Ken Burns zoom em momentos de impacto
# O worker aplica via setpts/zoompan ou scale filter

class ZoomEntry(BaseModel):
    start: float
    end: float
    scale: float = 1.15
    ease: str = "ease_in_out"


# ========== Overlays (B-roll) ==========
# Imagem/video sobreposta ao clip principal
# O worker faz overlay via filter_complex (overlay=x:y:enable='between(t,start,end)')
# audio_duck_db: reduz volume do clip principal enquanto overlay está ativo

class OverlayEntry(BaseModel):
    file_id: str              # uploaded via /v1/files/upload
    start: float
    end: float
    mode: str = "fullscreen"  # "fullscreen" | "picture_in_picture"
    audio_duck_db: float = -6.0


# ========== EDL Principal ==========

class RenderEDL(BaseModel):
    output: OutputSpec
    clips: list[ClipEntry]
    loudnorm: LoudnormSpec = LoudnormSpec()
    audio: AudioSpec | None = None
    captions: CaptionsConfig | list[CaptionSegment] | None = None
    reframe: ReframeConfig | None = None
    zooms: list[ZoomEntry] | None = None
    overlays: list[OverlayEntry] | None = None


# ========== Request (já existe, só troca edl: dict por edl: RenderEDL) ==========

class VideoRenderRequest(BaseModel):
    edl: RenderEDL
    webhook_url: str | None = None


# ========== Exemplo de conversão ASS no worker ==========

PYSUBS2_EXAMPLE = """
# No worker, ao processar captions, converter pra ASS assim:

import pysubs2

def build_ass(captions_config: CaptionsConfig, clip_duration_s: float) -> str:
    subs = pysubs2.SSAFile()

    # Converter v_anchor pra ASS alignment
    anchor_map = {"bottom": 2, "middle": 5, "top": 8}
    alignment = anchor_map.get(captions_config.position.v_anchor, 5)

    # Converter hex pra ASS color (&HAABBGGRR)
    def hex_to_ass(hex_color: str) -> str:
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"&H00{b:02X}{g:02X}{r:02X}"

    # Estilo base
    default_style = pysubs2.SSAStyle(
        fontname=captions_config.font,
        fontsize=captions_config.font_size,
        primarycolor=pysubs2.Color(255, 255, 255),  # branco default
        outlinecolor=pysubs2.Color(0, 0, 0),
        outline=captions_config.stroke_width,
        bold=True,
        alignment=alignment,
        marginv=captions_config.position.v_offset,
    )
    subs.styles["Default"] = default_style

    # Se segmentos têm cores diferentes, criar estilo por cor
    color_styles = {}
    for seg in captions_config.segments:
        color = seg.color or "#FFFFFF"
        if color not in color_styles:
            style_name = f"Color_{color.lstrip('#')}"
            style = default_style.copy()
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            style.primarycolor = pysubs2.Color(r, g, b)
            subs.styles[style_name] = style
            color_styles[color] = style_name

        start_ms = int(seg.start * 1000)
        end_ms = int(seg.end * 1000)
        style_name = color_styles.get(seg.color or "#FFFFFF", "Default")
        event = pysubs2.SSAEvent(
            start=start_ms,
            end=end_ms,
            text=seg.text,
            style=style_name,
        )
        subs.events.append(event)

    return subs.to_string("ass")
"""


if __name__ == "__main__":
    import json

    example = RenderEDL(
        output=OutputSpec(),
        clips=[
            ClipEntry(file_id="abc-123", in_point=32.5, out_point=35.0, label="teaser"),
            ClipEntry(file_id="abc-123", in_point=10.0, out_point=45.0),
        ],
        captions=CaptionsConfig(
            font="Montserrat Black",
            font_size=120,
            stroke_color="#000000",
            stroke_width=4,
            position=CaptionPosition(v_anchor="middle", v_offset=120),
            segments=[
                CaptionSegment(start=0.0, end=1.5, text="QUAL SALÁRIO", color="#FFFFFF"),
                CaptionSegment(start=1.5, end=3.0, text="DE UMA EMISSORA?", color="#FFD700"),
                CaptionSegment(start=3.0, end=4.5, text="QUANTO VOCÊ GANHAVA", color="#FF6B00"),
            ],
        ),
        reframe=ReframeConfig(
            source_width=1920,
            source_height=1080,
            keyframes=[
                ReframeKeyframe(start=0.0, end=15.0, cx=0.4, cy=0.4),
                ReframeKeyframe(start=15.0, end=35.0, cx=0.6, cy=0.4),
            ],
        ),
        zooms=[
            ZoomEntry(start=0.0, end=3.0, scale=1.12),
        ],
        overlays=[
            OverlayEntry(file_id="img-456", start=15.3, end=18.3),
        ],
    )

    print(json.dumps(example.model_dump(), indent=2))
    print("\n\n# ========== EXEMPLO PYSUBS2 ==========")
    print(PYSUBS2_EXAMPLE)
