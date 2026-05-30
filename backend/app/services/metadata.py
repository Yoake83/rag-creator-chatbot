"""
Metadata extraction.

YouTube: yt-dlp (free, no API key, comprehensive)
Instagram: yt-dlp for basic info + Apify for follower count
           (Apify free tier: 5 actor runs/mo — enough for demos)

Engagement rate formula: (likes + comments) / views × 100
Returns 0.0 if views == 0 to avoid ZeroDivisionError.
"""

import re
import logging
from typing import Dict, Any

import yt_dlp

from app.core.config import settings
from app.models.schemas import VideoMetadata

logger = logging.getLogger(__name__)


def extract_youtube_metadata(url: str, video_id: str = "A") -> VideoMetadata:
    logger.info(f"[YouTube] Extracting metadata from {url}")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    views = info.get("view_count") or 0
    likes = info.get("like_count") or 0
    comments = info.get("comment_count") or 0
    engagement = _compute_engagement(likes, comments, views)

    hashtags = [
        tag for tag in (info.get("tags") or [])
        if tag.startswith("#")
    ] or [f"#{t}" for t in (info.get("tags") or [])[:10]]

    return VideoMetadata(
        video_id=video_id,
        url=url,
        platform="youtube",
        title=info.get("title"),
        creator=info.get("uploader"),
        follower_count=info.get("channel_follower_count"),
        views=views,
        likes=likes,
        comments=comments,
        engagement_rate=engagement,
        hashtags=hashtags[:10],
        upload_date=_format_date(info.get("upload_date")),
        duration_seconds=info.get("duration"),
        thumbnail_url=info.get("thumbnail"),
    )


def extract_instagram_metadata(url: str, video_id: str = "B") -> VideoMetadata:
    logger.info(f"[Instagram] Extracting metadata from {url}")

    # Try yt-dlp first (gets basic info without auth)
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    info: Dict[str, Any] = {}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False) or {}
    except Exception as e:
        logger.warning(f"[Instagram] yt-dlp metadata failed: {e}")

    views = info.get("view_count") or info.get("play_count") or 0
    likes = info.get("like_count") or 0
    comments = info.get("comment_count") or 0
    engagement = _compute_engagement(likes, comments, views)

    # Attempt Apify enrichment for follower count if token is set
    follower_count = info.get("channel_follower_count")
    if not follower_count and settings.apify_token:
        follower_count = _get_instagram_followers_apify(url)

    hashtags = _extract_instagram_hashtags(info.get("description") or "")

    return VideoMetadata(
        video_id=video_id,
        url=url,
        platform="instagram",
        title=info.get("title") or info.get("description", "")[:80],
        creator=info.get("uploader") or info.get("channel"),
        follower_count=follower_count,
        views=views,
        likes=likes,
        comments=comments,
        engagement_rate=engagement,
        hashtags=hashtags[:10],
        upload_date=_format_date(info.get("upload_date")),
        duration_seconds=info.get("duration"),
        thumbnail_url=info.get("thumbnail"),
    )


# ── helpers ───────────────────────────────────────────────────────────────────

def _compute_engagement(likes: int, comments: int, views: int) -> float:
    if views == 0:
        return 0.0
    return round((likes + comments) / views * 100, 4)


def _format_date(raw: str | None) -> str | None:
    """Convert YYYYMMDD → YYYY-MM-DD."""
    if not raw or len(raw) != 8:
        return raw
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def _extract_instagram_hashtags(text: str) -> list[str]:
    return re.findall(r"#\w+", text)


def _get_instagram_followers_apify(url: str) -> int | None:
    """
    Use Apify's Instagram Profile Scraper to get follower count.
    Free tier allows 5 runs/month — enough for demo and light usage.
    """
    try:
        from apify_client import ApifyClient

        username_match = re.search(r"instagram\.com/([^/?]+)", url)
        if not username_match:
            return None

        username = username_match.group(1).strip("/")
        client = ApifyClient(settings.apify_token)

        run = client.actor("apify/instagram-profile-scraper").call(
            run_input={"usernames": [username]}
        )
        items = list(client.dataset(run.get("defaultDatasetId")).iterate_items())
        if items:
            return items[0].get("followersCount")
    except Exception as e:
        logger.warning(f"[Apify] Follower count fetch failed: {e}")

    return None
