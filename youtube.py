import os
import asyncio
import yt_dlp
from youtube_search import YoutubeSearch

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def search_youtube(query: str):
    """YouTube pe search karta hai, pehla result deta hai."""
    loop = asyncio.get_event_loop()

    def _search():
        results = YoutubeSearch(query, max_results=1).to_dict()
        return results[0] if results else None

    return await loop.run_in_executor(None, _search)


async def search_track(query: str):
    """search_youtube ka normalized wrapper — id/title/duration/thumbnail/url deta hai."""
    result = await search_youtube(query)
    if not result:
        return None

    thumbnails = result.get("thumbnails") or []
    video_id = result.get("id")

    return {
        "id": video_id,
        "title": result.get("title", "Unknown"),
        "duration": result.get("duration", ""),
        "thumbnail": thumbnails[0] if thumbnails else None,
        "channel": result.get("channel") or result.get("uploader") or "",
        "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
    }


class DownloadError(Exception):
    """Audio download ya extract karne me error."""


def _video_id(video: str) -> str:
    """Poora YouTube link ya id — dono se sirf video id nikalta hai."""
    video = (video or "").strip()
    if not video:
        return ""
    if "youtu.be/" in video:
        video = video.split("youtu.be/")[1]
    elif "v=" in video:
        video = video.split("v=")[1]
    elif "/shorts/" in video:
        video = video.split("/shorts/")[1]
    elif "/embed/" in video:
        video = video.split("/embed/")[1]
    for sep in ("?", "&", "/", "#"):
        video = video.split(sep)[0]
    return video


async def get_stream_url(video: str) -> str:
    """
    yt-dlp ka use karke YouTube video ko audio (mp3) me download karta hai
    aur local file path return karta hai.
    """
    video_id = _video_id(video)
    if not video_id:
        raise DownloadError("Video id nahi mila")

    url = f"https://www.youtube.com/watch?v={video_id}"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")

    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, f'{video_id}.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }

    loop = asyncio.get_event_loop()

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    try:
        await loop.run_in_executor(None, _download)
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path
        raise DownloadError("Audio file taiyaar nahi ho saki")
    except Exception as e:
        raise DownloadError(f"yt-dlp download error: {e}")


async def get_related_track(title: str, exclude_id: str = None):
    """Autoplay ke liye milta-julta agla gaana dhoondta hai."""
    loop = asyncio.get_event_loop()
    base = (title or "").split("|")[0].split("(")[0].strip()
    if not base:
        return None

    def _search():
        try:
            return YoutubeSearch(f"{base} song", max_results=8).to_dict()
        except Exception:
            return []

    results = await loop.run_in_executor(None, _search)
    for result in results or []:
        video_id = result.get("id")
        if not video_id or video_id == exclude_id:
            continue
        thumbnails = result.get("thumbnails") or []
        return {
            "id": video_id,
            "title": result.get("title", "Unknown"),
            "duration": result.get("duration", ""),
            "thumbnail": thumbnails[0] if thumbnails else None,
            "channel": result.get("channel") or result.get("uploader") or "",
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }
    return None
    
