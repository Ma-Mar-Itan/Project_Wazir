"""Project Oracle — Whisper voice transcription. Optional."""

from typing import Optional

import requests

from config import CONFIG


def transcribe_voice_file(filepath: str) -> Optional[str]:
    """Send an audio file to OpenAI Whisper. Returns text or None if no API key."""
    if not CONFIG.OPENAI_API_KEY:
        return None
    with open(filepath, "rb") as f:
        files = {"file": ("voice.ogg", f, "audio/ogg")}
        data = {"model": "whisper-1"}
        res = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {CONFIG.OPENAI_API_KEY}"},
            files=files,
            data=data,
            timeout=120,
        )
    res.raise_for_status()
    return res.json().get("text")
