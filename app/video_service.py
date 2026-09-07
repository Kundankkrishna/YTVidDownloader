import yt_dlp
import re
import time
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass
from pathlib import Path


class VideoServiceError(Exception):
    pass


class InvalidURLError(VideoServiceError):
    pass


class VideoUnavailableError(VideoServiceError):
    pass


class AgeRestrictedError(VideoServiceError):
    pass


class NetworkError(VideoServiceError):
    pass


class PlaylistError(VideoServiceError):
    pass


@dataclass
class PlaylistInfo:
    title: str
    uploader: str
    video_count: int
    videos: List[Dict[str, Any]]
    url: str

    @classmethod
    def from_ydl(cls, data: Dict[str, Any]) -> "PlaylistInfo":
        entries = data.get("entries", [])
        videos = []
        for entry in entries:
            if entry:
                videos.append({
                    "title": entry.get("title", "Unknown"),
                    "url": entry.get("webpage_url", ""),
                    "duration": entry.get("duration", 0),
                    "video_id": entry.get("id", ""),
                })
        return cls(
            title=data.get("title", "Unknown Playlist"),
            uploader=data.get("uploader", "Unknown"),
            video_count=len(videos),
            videos=videos,
            url=data.get("webpage_url", "")
        )


@dataclass
class VideoInfo:
    title: str
    author: str
    length: int
    views: int
    thumbnail_url: str
    formats: List[Dict[str, Any]]
    duration_string: str
    url: str
    video_id: str

    @classmethod
    def from_ydl(cls, data: Dict[str, Any]) -> "VideoInfo":
        formats = data.get("formats", [])
        video_formats = [f for f in formats if f.get("vcodec") != "none" and f.get("height")]
        
        return cls(
            title=data.get("title", "Unknown"),
            author=data.get("uploader", "Unknown"),
            length=data.get("duration", 0),
            views=data.get("view_count", 0),
            thumbnail_url=data.get("thumbnail", ""),
            formats=video_formats,
            duration_string=cls._format_duration(data.get("duration", 0)),
            url=data.get("webpage_url", ""),
            video_id=data.get("id", "")
        )

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if not seconds:
            return "Unknown"
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours}h {mins}m {secs}s"
        return f"{mins}m {secs}s"


class VideoService:
    YOUTUBE_URL_PATTERN = re.compile(
        r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$"
    )

    def __init__(self, cookies_file: Optional[str] = None, cookies_from_browser: Optional[str] = None):
        self._ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        
        # Add cookies support for authentication
        if cookies_file:
            self._ydl_opts["cookiefile"] = cookies_file
        if cookies_from_browser:
            self._ydl_opts["cookies_from_browser"] = (cookies_from_browser,)
        
        self._cached_info: Optional[VideoInfo] = None
        self._cached_url: Optional[str] = None
        self._max_retries = 3
        self._retry_delay = 1.0

    PLAYLIST_URL_PATTERN = re.compile(
        r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/(playlist|watch\?.*list=).+$"
    )

    def is_playlist_url(self, url: str) -> bool:
        return bool(self.PLAYLIST_URL_PATTERN.match(url.strip()))

    def validate_url(self, url: str) -> bool:
        return bool(self.YOUTUBE_URL_PATTERN.match(url.strip()))

    def fetch_video_info(self, url: str, progress_callback: Optional[Callable] = None) -> VideoInfo:
        if not self.validate_url(url):
            raise InvalidURLError("Invalid YouTube URL")

        if self._cached_url == url and self._cached_info:
            return self._cached_info

        def progress_hook(d):
            if progress_callback and d["status"] == "downloading":
                progress_callback(d)

        ydl_opts = {**self._ydl_opts, "progress_hooks": [progress_hook] if progress_callback else []}

        last_exception = None
        for attempt in range(self._max_retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    data = ydl.extract_info(url, download=False)
                break
            except yt_dlp.utils.DownloadError as e:
                last_exception = e
                err_msg = str(e).lower()
                if "unavailable" in err_msg or "private" in err_msg or "deleted" in err_msg:
                    raise VideoUnavailableError("Video is unavailable, private, or deleted")
                if "age" in err_msg and "restrict" in err_msg:
                    raise AgeRestrictedError("Video is age-restricted")
                if "network" in err_msg or "connection" in err_msg or "timeout" in err_msg:
                    if attempt < self._max_retries - 1:
                        time.sleep(self._retry_delay * (attempt + 1))
                        continue
                    raise NetworkError("Network error - check your connection")
                raise VideoServiceError(f"Failed to fetch video: {e}")
            except Exception as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay * (attempt + 1))
                    continue
                raise VideoServiceError(f"Unexpected error: {e}")
        else:
            raise VideoServiceError(f"Failed after {self._max_retries} attempts: {last_exception}")

        if not data:
            raise VideoUnavailableError("No video data returned")

        if data.get("_type") == "playlist":
            raise PlaylistError("URL is a playlist, not a single video")

        formats = data.get("formats", [])
        playable_formats = [f for f in formats if f.get("vcodec") != "none" or f.get("acodec") != "none"]
        if not playable_formats:
            raise VideoUnavailableError("No playable formats available for this video (may be a Short, live stream, or restricted content)")

        self._cached_info = VideoInfo.from_ydl(data)
        self._cached_url = url
        return self._cached_info

    def fetch_playlist_info(self, url: str) -> PlaylistInfo:
        if not self.validate_url(url):
            raise InvalidURLError("Invalid YouTube URL")
        if not self.is_playlist_url(url):
            raise PlaylistError("URL is not a playlist")

        ydl_opts = {**self._ydl_opts, "extract_flat": "in_playlist"}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as e:
            raise PlaylistError(f"Failed to fetch playlist: {e}")

        if not data or data.get("_type") != "playlist":
            raise PlaylistError("No playlist data returned")

        return PlaylistInfo.from_ydl(data)

    def download_playlist(
        self,
        url: str,
        output_dir: str,
        resolution: Optional[str] = None,
        audio_only: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        if audio_only:
            format_spec = "bestaudio/best"
        elif resolution:
            height = int(resolution[:-1])
            format_spec = (
                f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={height}]+bestaudio/"
                f"best[height<={height}]/"
                f"bestvideo[height<=?{height}]+bestaudio/"
                f"best"
            )
        else:
            format_spec = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

        ydl_opts = {
            **self._ydl_opts,
            "format": format_spec,
            "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
            "progress_hooks": [progress_callback] if progress_callback else [],
            "merge_output_format": "mp4",
        }

        downloaded_files = []
        def progress_hook(d):
            if progress_callback:
                progress_callback(d)
            if d["status"] == "finished":
                downloaded_files.append(d.get("filename", ""))

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            raise VideoServiceError(f"Playlist download failed: {e}")

        return downloaded_files

    def get_resolutions(self, video_info: VideoInfo) -> List[str]:
        resolutions = set()
        for fmt in video_info.formats:
            height = fmt.get("height")
            if height:
                resolutions.add(f"{height}p")
        return sorted(resolutions, key=lambda x: int(x[:-1]), reverse=True)

    def get_format_for_resolution(self, video_info: VideoInfo, resolution: str) -> Optional[Dict[str, Any]]:
        height = int(resolution[:-1])
        for fmt in video_info.formats:
            if fmt.get("height") == height:
                return fmt
        return None

    def download_video(
        self,
        url: str,
        output_path: str,
        resolution: Optional[str] = None,
        audio_only: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> str:
        def progress_hook(d):
            if progress_callback:
                progress_callback(d)

        if audio_only:
            format_spec = "bestaudio/best"
        elif resolution:
            height = int(resolution[:-1])
            # More flexible format selection with fallbacks
            format_spec = (
                f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={height}]+bestaudio/"
                f"best[height<={height}]/"
                f"bestvideo[height<=?{height}]+bestaudio/"
                f"best"
            )
        else:
            format_spec = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

        ydl_opts = {
            **self._ydl_opts,
            "format": format_spec,
            "outtmpl": output_path,
            "progress_hooks": [progress_hook] if progress_callback else [],
            "merge_output_format": "mp4",
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            raise VideoServiceError(f"Download failed: {e}")
        except Exception as e:
            raise VideoServiceError(f"Download error: {e}")

        return output_path

    def clear_cache(self):
        self._cached_info = None
        self._cached_url = None