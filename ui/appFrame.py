import customtkinter as ctk
from app.ytd_main import YouTubeDownloaderApp


def set_env_appearance():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")


def appStructure():
    set_env_appearance()
    app = YouTubeDownloaderApp()
    return app.app


if __name__ == "__main__":
    set_env_appearance()
    app = YouTubeDownloaderApp()
    app.run()