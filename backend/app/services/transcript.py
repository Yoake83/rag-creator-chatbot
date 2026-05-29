"""
Transcript extraction with graceful fallback chain:

YouTube:
  1. youtube-transcript-api (free, fast, no API key)
  2. yt-dlp + Whisper (slower, works when captions are disabled)

Instagram:
  1. yt-dlp (downloads audio) → Whisper transcription
  2. If yt-dlp fails (private/restricted reel), raises clear error

Whisper model: "base" by default — fast enough on CPU, ~80% accuracy.
Swap to "small" or "medium" for better quality at ~2x cost.
"""

import os
import re
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_youtube_transcript(url: str) -> str:
    """Try captions first, fall back to Whisper."""
    video_id = _extract_youtube_id(url)

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join([entry["text"] for entry in transcript_list])
        logger.info(f"[YouTube] Got captions for {video_id} ({len(full_text)} chars)")
        return full_text
    except Exception as e:
        logger.warning(f"[YouTube] Captions failed ({e}), falling back to Whisper")
        return _whisper_from_url(url)


def get_instagram_transcript(url: str) -> str:
    """Download Instagram reel audio and transcribe with Whisper."""
    logger.info(f"[Instagram] Downloading audio from {url}")
    return _whisper_from_url(url)


def _whisper_from_url(url: str) -> str:
    """Download audio with yt-dlp and transcribe with Whisper."""
    import yt_dlp
    import whisper

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.mp3")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tmpdir, "audio.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",   # 64kbps is fine for speech
            }],
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # yt-dlp may produce .mp3 or .m4a depending on source
        for fname in os.listdir(tmpdir):
            if fname.startswith("audio."):
                audio_path = os.path.join(tmpdir, fname)
                break

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"yt-dlp did not produce audio for {url}")

        model = whisper.load_model("base")
        result = model.transcribe(audio_path, fp16=False)
        transcript = result["text"].strip()
        logger.info(f"[Whisper] Transcribed {len(transcript)} chars from {url}")
        return transcript


def _extract_youtube_id(url: str) -> str:
    patterns = [
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:embed/)([A-Za-z0-9_-]{11})",
        r"(?:shorts/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract YouTube video ID from URL: {url}")
