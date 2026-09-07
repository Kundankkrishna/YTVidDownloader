import os
from app.ytd_main import YouTubeDownloaderApp


def get_cookies_config():
    """Get cookies configuration from environment variables."""
    cookies_file = os.environ.get("YTD_COOKIES_FILE")
    cookies_from_browser = os.environ.get("YTD_COOKIES_FROM_BROWSER")
    return cookies_file, cookies_from_browser


if __name__ == "__main__":
    cookies_file, cookies_from_browser = get_cookies_config()
    app = YouTubeDownloaderApp(
        cookies_file=cookies_file,
        cookies_from_browser=cookies_from_browser
    )
    app.run()