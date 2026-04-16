#!/usr/bin/env python3
"""Seed default style presets into the database."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


PRESETS = [
    {
        "name": "default",
        "captions_config": {
            "style": "viral_yellow_karaoke",
            "font": "Montserrat Black",
            "font_size": 110,
            "max_words_per_page": 3,
            "max_gap_s": 0.35,
            "position": {"v_anchor": "middle", "v_offset": 0},
        },
        "reframe_config": {
            "mode": "active_speaker",
            "smoothing": {"type": "ema", "alpha": 0.15},
            "min_hold_ms": 800,
        },
        "overlay_config": {
            "emojis_enabled": True,
            "max_emojis_per_clip": 4,
        },
        "audio_config": {
            "loudnorm": {"I": -14, "TP": -1, "LRA": 9},
            "background_music_volume": 0.12,
        },
    },
    {
        "name": "minimal_white",
        "captions_config": {
            "style": "minimal_white",
            "font": "Inter Bold",
            "font_size": 90,
            "max_words_per_page": 2,
            "max_gap_s": 0.3,
            "position": {"v_anchor": "bottom", "v_offset": -100},
        },
        "reframe_config": {
            "mode": "active_speaker",
            "smoothing": {"type": "ema", "alpha": 0.2},
            "min_hold_ms": 1000,
        },
        "overlay_config": {
            "emojis_enabled": False,
        },
        "audio_config": {
            "loudnorm": {"I": -14, "TP": -1, "LRA": 9},
        },
    },
    {
        "name": "hormozi_style",
        "captions_config": {
            "style": "hormozi_bold",
            "font": "Impact",
            "font_size": 130,
            "max_words_per_page": 2,
            "max_gap_s": 0.25,
            "position": {"v_anchor": "middle", "v_offset": 50},
        },
        "reframe_config": {
            "mode": "active_speaker",
            "smoothing": {"type": "ema", "alpha": 0.1},
            "min_hold_ms": 600,
        },
        "overlay_config": {
            "emojis_enabled": True,
            "max_emojis_per_clip": 6,
        },
        "audio_config": {
            "loudnorm": {"I": -14, "TP": -1, "LRA": 9},
            "background_music_volume": 0.08,
        },
    },
]


async def main():
    from opus_clone.db import get_db_session
    from opus_clone.models.db import StylePreset

    for preset_data in PRESETS:
        async with get_db_session() as session:
            from sqlalchemy import select

            existing = await session.execute(
                select(StylePreset).where(StylePreset.name == preset_data["name"])
            )
            if existing.scalar_one_or_none():
                print(f"  Preset '{preset_data['name']}' already exists, skipping")
                continue

            preset = StylePreset(**preset_data)
            session.add(preset)
            print(f"  Created preset '{preset_data['name']}'")

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
