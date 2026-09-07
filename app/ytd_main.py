import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import urllib.request
import threading
import os
import webbrowser
from datetime import datetime
from typing import Optional
from app.video_service import VideoService, VideoServiceError, InvalidURLError, VideoUnavailableError, AgeRestrictedError, NetworkError, PlaylistError, PlaylistInfo
from app.history import HistoryManager, DownloadHistoryEntry


class YouTubeDownloaderApp:
    def __init__(self, cookies_file: Optional[str] = None, cookies_from_browser: Optional[str] = None):
        self.app = ctk.CTk()
        self.app.title("YTD")
        self.app.iconbitmap("app/ytd.ico")
        self.app.geometry("800x600")

        self.video_service = VideoService(cookies_file=cookies_file, cookies_from_browser=cookies_from_browser)
        self.history_manager = HistoryManager()
        self.current_video_info = None
        self.is_fetching = False
        self.is_downloading = False

        self.res_var = tk.StringVar()
        self.url_var = tk.StringVar()

        self._setup_ui()
        self._setup_menu()

    def _setup_ui(self):
        lbl_prompt = ctk.CTkLabel(master=self.app, text="YouTube Link: ")
        lbl_prompt.grid(padx=10, pady=10, row=1, column=0)

        self.ent_link = ctk.CTkEntry(master=self.app, width=400, textvariable=self.url_var)
        self.ent_link.grid(padx=10, pady=10, row=1, column=1)

        self.btn_verify = ctk.CTkButton(master=self.app, text="Verify", command=self._on_verify)
        self.btn_verify.grid(padx=10, pady=10, row=1, column=2)

        btn_exit = ctk.CTkButton(master=self.app, text="Exit", width=70, corner_radius=10, fg_color="red", command=self.app.quit)
        btn_exit.grid(padx=10, pady=10, row=10, column=2)

        lbl_theme = ctk.CTkLabel(self.app, text="Select theme")
        lbl_theme.grid(row=5, column=0, padx=5, pady=2)

        appearance_mode_optionmenu = ctk.CTkOptionMenu(self.app, values=["Light", "Dark", "System"], command=self._change_appearance_mode)
        appearance_mode_optionmenu.set("System")
        appearance_mode_optionmenu.grid(row=6, column=0, padx=20, pady=2)

        self.lbl_status = ctk.CTkLabel(self.app, text="")
        self.lbl_status.grid(padx=10, pady=5, row=7, column=1)

        self.frm_details = None
        self.lbl_thumbnail = None
        self.lbl_vid_name = None
        self.lbl_vid_author = None
        self.lbl_vid_length = None
        self.lbl_vid_views = None
        self.menu_options = None
        self.btn_download = None
        self.lbl_filesize = None
        self.progress_bar = None
        self.lbl_episode = None

    def _change_appearance_mode(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def _setup_menu(self):
        menubar = tk.Menu(self.app)
        self.app.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Clear History", command=self._clear_history)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.app.quit)
        
        history_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="History", menu=history_menu)
        history_menu.add_command(label="View History", command=self._show_history)
        history_menu.add_command(label="Open Download Folder", command=self._open_download_folder)

    def _open_download_folder(self):
        import subprocess
        import platform
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if platform.system() == "Windows":
            os.startfile(download_dir)
        elif platform.system() == "Darwin":
            subprocess.run(["open", download_dir])
        else:
            subprocess.run(["xdg-open", download_dir])

    def _show_history(self):
        HistoryWindow(self.app, self.history_manager)

    def _clear_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all download history?"):
            self.history_manager.clear_history()
            self._show_error("History cleared")

    def _on_verify(self):
        url = self.url_var.get().strip()
        if not url:
            self._show_error("Please enter a YouTube URL")
            return

        if not self.video_service.validate_url(url):
            self._show_error("Invalid YouTube URL")
            return

        if self.is_fetching:
            return

        # Check if it's a playlist
        if self.video_service.is_playlist_url(url):
            self._on_verify_playlist(url)
            return

        self.is_fetching = True
        self._set_ui_fetching_state(True)
        self._clear_details()

        thread = threading.Thread(target=self._fetch_video_info_thread, args=(url,), daemon=True)
        thread.start()

    def _on_verify_playlist(self, url: str):
        if self.is_fetching:
            return

        self.is_fetching = True
        self._set_ui_fetching_state(True)
        self._clear_details()
        self.lbl_status.configure(text="Fetching playlist info...")

        thread = threading.Thread(target=self._fetch_playlist_info_thread, args=(url,), daemon=True)
        thread.start()

    def _fetch_playlist_info_thread(self, url: str):
        try:
            playlist_info = self.video_service.fetch_playlist_info(url)
            self.app.after(0, lambda: self._on_fetch_playlist_success(playlist_info))
        except InvalidURLError:
            self.app.after(0, lambda: self._on_fetch_error("Invalid YouTube URL"))
        except PlaylistError as e:
            self.app.after(0, lambda err=e: self._on_fetch_error(str(err)))
        except VideoServiceError as e:
            self.app.after(0, lambda err=e: self._on_fetch_error(str(err)))
        except Exception as e:
            self.app.after(0, lambda err=e: self._on_fetch_error(f"Unexpected error: {err}"))

    def _on_fetch_playlist_success(self, playlist_info: PlaylistInfo):
        self.is_fetching = False
        self._set_ui_fetching_state(False)
        self._show_playlist_details(playlist_info)

    def _show_playlist_details(self, playlist_info: PlaylistInfo):
        self.frm_details = ctk.CTkFrame(master=self.app, fg_color="grey", width=480, height=300)

        lbl_playlist_name = ctk.CTkLabel(master=self.frm_details, text=f"Playlist: {playlist_info.title}", font=("Arial", 16, "bold"), wraplength=450)
        lbl_playlist_name.grid(padx=5, pady=5)

        lbl_playlist_author = ctk.CTkLabel(master=self.frm_details, text=f"Author: {playlist_info.uploader}", font=("Arial", 16))
        lbl_playlist_author.grid(padx=5, pady=5)

        lbl_playlist_count = ctk.CTkLabel(master=self.frm_details, text=f"Videos: {playlist_info.video_count}", font=("Arial", 16))
        lbl_playlist_count.grid(padx=5, pady=5)

        self.frm_details.grid(padx=10, pady=10, row=3, column=1)

        # Playlist download options
        self._show_playlist_download_options(playlist_info)

    def _show_playlist_download_options(self, playlist_info: PlaylistInfo):
        # Resolution selector
        resolutions = ["Best available", "1080p", "720p", "480p", "360p", "Audio only (MP3)"]
        self.menu_options = ctk.CTkOptionMenu(master=self.app, values=resolutions, command=self._on_playlist_resolution_select, variable=self.res_var)
        self.menu_options.set("Select Quality")
        self.menu_options.grid(padx=10, pady=10, row=4, column=1)

        # Store playlist info for download
        self.current_playlist_info = playlist_info

    def _on_playlist_resolution_select(self, choice):
        self._show_playlist_download_button()

    def _show_playlist_download_button(self):
        if self.btn_download:
            self.btn_download.destroy()
        self.btn_download = ctk.CTkButton(self.app, text="Download Playlist", command=self._on_download_playlist)
        self.btn_download.grid(padx=10, pady=10, row=5, column=1)

    def _on_download_playlist(self):
        if not hasattr(self, 'current_playlist_info') or self.is_downloading:
            return

        quality = self.res_var.get()
        if not quality or quality == "Select Quality":
            self._show_error("Please select a quality option")
            return

        output_dir = filedialog.askdirectory(initialdir=".", title="Select folder to save playlist")
        if not output_dir:
            return

        # Parse quality selection
        audio_only = quality == "Audio only (MP3)"
        resolution = None if quality == "Best available" or audio_only else quality

        self.is_downloading = True
        self.btn_download.configure(text="Downloading...", state="disabled")
        self.lbl_status.configure(text="Downloading playlist...")

        if self.progress_bar:
            self.progress_bar.destroy()
        self.progress_bar = ctk.CTkProgressBar(self.app, width=400)
        self.progress_bar.grid(padx=10, pady=10, row=8, column=1)
        self.progress_bar.set(0)

        # Add episode label
        if self.lbl_episode:
            self.lbl_episode.destroy()
        self.lbl_episode = ctk.CTkLabel(self.app, text="", font=("Arial", 12))
        self.lbl_episode.grid(padx=10, pady=5, row=9, column=1)

        thread = threading.Thread(target=self._download_playlist_thread, args=(self.current_playlist_info.url, output_dir, resolution, audio_only), daemon=True)
        thread.start()

    def _download_playlist_thread(self, url: str, output_dir: str, resolution: Optional[str], audio_only: bool):
        try:
            current_video_title = ""
            current_video_index = 0
            total_videos = len(self.current_playlist_info.videos) if hasattr(self, 'current_playlist_info') else 0

            def progress_hook(data):
                nonlocal current_video_title, current_video_index
                
                if data["status"] == "downloading":
                    total = data.get("total_bytes") or data.get("total_bytes_estimate")
                    downloaded = data.get("downloaded_bytes", 0)
                    if total:
                        progress = downloaded / total
                        self.app.after(0, lambda: self.progress_bar.set(progress))
                        self.app.after(0, lambda: self.lbl_status.configure(text=f"Downloading... {progress*100:.1f}%"))
                    
                    # Update episode title if available
                    filename = data.get("filename", "")
                    if filename and filename != current_video_title:
                        current_video_title = filename
                        # Extract video title from filename
                        import os
                        video_title = os.path.splitext(os.path.basename(filename))[0]
                        if video_title:
                            self.app.after(0, lambda vt=video_title: self.lbl_episode.configure(text=f"Episode: {vt}"))

                elif data["status"] == "finished":
                    current_video_index += 1
                    filename = data.get("filename", "")
                    if filename:
                        import os
                        video_title = os.path.splitext(os.path.basename(filename))[0]
                        self.app.after(0, lambda vt=video_title, idx=current_video_index, tot=total_videos: 
                            self.lbl_episode.configure(text=f"Episode {idx}/{tot}: {vt}"))
                        self.app.after(0, lambda idx=current_video_index, tot=total_videos: 
                            self.lbl_status.configure(text=f"Downloaded {idx}/{tot} videos"))

            self.video_service.download_playlist(url, output_dir, resolution=resolution, audio_only=audio_only, progress_callback=progress_hook)
            self.app.after(0, self._on_download_success)
        except VideoServiceError as e:
            self.app.after(0, lambda err=e: self._on_download_error(str(err)))
        except Exception as e:
            self.app.after(0, lambda err=e: self._on_download_error(f"Download failed: {err}"))

    def _fetch_video_info_thread(self, url: str):
        try:
            video_info = self.video_service.fetch_video_info(url, progress_callback=self._on_fetch_progress)
            self.app.after(0, lambda: self._on_fetch_success(video_info))
        except InvalidURLError:
            self.app.after(0, lambda: self._on_fetch_error("Invalid YouTube URL"))
        except VideoUnavailableError:
            self.app.after(0, lambda: self._on_fetch_error("Video is unavailable, private, or deleted"))
        except AgeRestrictedError:
            self.app.after(0, lambda: self._on_fetch_error("Video is age-restricted"))
        except NetworkError:
            self.app.after(0, lambda: self._on_fetch_error("Network error - check your connection"))
        except VideoServiceError as e:
            self.app.after(0, lambda err=e: self._on_fetch_error(str(err)))
        except Exception as e:
            self.app.after(0, lambda err=e: self._on_fetch_error(f"Unexpected error: {err}"))

    def _on_fetch_progress(self, data: dict):
        pass

    def _on_fetch_success(self, video_info):
        self.current_video_info = video_info
        self.is_fetching = False
        self._set_ui_fetching_state(False)
        self._show_video_details(video_info)

    def _on_fetch_error(self, error_msg: str):
        self.is_fetching = False
        self._set_ui_fetching_state(False)
        self._show_error(error_msg)

    def _set_ui_fetching_state(self, fetching: bool):
        if fetching:
            self.btn_verify.configure(text="Fetching...", state="disabled")
            self.lbl_status.configure(text="Fetching video info...")
        else:
            self.btn_verify.configure(text="Verify", state="normal")
            self.lbl_status.configure(text="")

    def _clear_details(self):
        if self.frm_details:
            self.frm_details.destroy()
            self.frm_details = None
        if self.menu_options:
            self.menu_options.destroy()
            self.menu_options = None
        if self.btn_download:
            self.btn_download.destroy()
            self.btn_download = None
        if self.lbl_filesize:
            self.lbl_filesize.destroy()
            self.lbl_filesize = None
        if self.progress_bar:
            self.progress_bar.destroy()
            self.progress_bar = None
        if self.lbl_episode:
            self.lbl_episode.destroy()
            self.lbl_episode = None

    def _show_video_details(self, video_info):
        self.frm_details = ctk.CTkFrame(master=self.app, fg_color="grey", width=480, height=300)

        thumb_url = video_info.thumbnail_url
        thumbnail_file = "vid_thumbnail.png"

        try:
            urllib.request.urlretrieve(thumb_url, thumbnail_file)
            thumb_img = ctk.CTkImage(Image.open(thumbnail_file), size=(300, 225))
            self.lbl_thumbnail = ctk.CTkLabel(self.frm_details, image=thumb_img, text="")
            self.lbl_thumbnail.grid()
        except Exception:
            self.lbl_thumbnail = ctk.CTkLabel(self.frm_details, text="[Thumbnail unavailable]")
            self.lbl_thumbnail.grid()

        self.lbl_vid_name = ctk.CTkLabel(master=self.frm_details, text=f"Video Title: {video_info.title}", font=("Arial", 16, "bold"), wraplength=450)
        self.lbl_vid_name.grid(padx=5, pady=5)

        self.lbl_vid_author = ctk.CTkLabel(master=self.frm_details, text=f"Author: {video_info.author}", font=("Arial", 16))
        self.lbl_vid_author.grid(padx=5, pady=5)

        self.lbl_vid_length = ctk.CTkLabel(master=self.frm_details, text=f"Length: {video_info.duration_string}", font=("Arial", 16))
        self.lbl_vid_length.grid(padx=5, pady=5)

        self.lbl_vid_views = ctk.CTkLabel(master=self.frm_details, text=f"Views: {video_info.views:,}", font=("Arial", 16))
        self.lbl_vid_views.grid(padx=5, pady=5)

        self.frm_details.grid(padx=10, pady=10, row=3, column=1)

        resolutions = self.video_service.get_resolutions(video_info)
        if resolutions:
            # Add audio-only option
            options = resolutions + ["Audio only (MP3)"]
            self.menu_options = ctk.CTkOptionMenu(master=self.app, values=options, command=self._on_resolution_select, variable=self.res_var)
            self.menu_options.set("Select Quality")
            self.menu_options.grid(padx=10, pady=10, row=4, column=1)

    def _on_resolution_select(self, choice):
        if not self.current_video_info:
            return

        quality = self.res_var.get()
        if not quality or quality == "Select Quality":
            return

        if quality != "Audio only (MP3)":
            fmt = self.video_service.get_format_for_resolution(self.current_video_info, quality)
            if fmt:
                filesize_mb = fmt.get("filesize") or fmt.get("filesize_approx")
                if filesize_mb:
                    size_mb = filesize_mb / (1024 * 1024)
                    if self.lbl_filesize:
                        self.lbl_filesize.destroy()
                    self.lbl_filesize = ctk.CTkLabel(self.app, text=f"Download size: {size_mb:.1f} MB for {quality}")
                    self.lbl_filesize.grid(padx=10, pady=10, row=9, column=1)
        else:
            if self.lbl_filesize:
                self.lbl_filesize.destroy()
            self.lbl_filesize = ctk.CTkLabel(self.app, text="Audio only download (MP3)")
            self.lbl_filesize.grid(padx=10, pady=10, row=9, column=1)

        self._show_download_button()

    def _show_download_button(self):
        if self.btn_download:
            self.btn_download.destroy()
        self.btn_download = ctk.CTkButton(self.app, text="Download", command=self._on_download)
        self.btn_download.grid(padx=10, pady=10, row=5, column=1)

    def _on_download(self):
        if not self.current_video_info or self.is_downloading:
            return

        quality = self.res_var.get()
        if not quality or quality == "Select Quality":
            self._show_error("Please select a quality option")
            return

        audio_only = quality == "Audio only (MP3)"
        resolution = None if audio_only else quality

        file_ext = ".mp3" if audio_only else ".mp4"
        file_types = (("MP3 Files", "*.mp3"), ("All Files", "*.*")) if audio_only else (("MP4 Files", "*.mp4"), ("All Files", "*.*"))

        file_path = filedialog.asksaveasfilename(
            initialdir=".",
            title="Save file as",
            initialfile=self.current_video_info.title,
            filetypes=file_types
        )
        if not file_path:
            return

        if not file_path.endswith(file_ext):
            file_path += file_ext

        # Store download info for history
        self._last_download = {
            "file_path": file_path,
            "resolution": quality,
            "audio_only": audio_only
        }

        self.is_downloading = True
        self.btn_download.configure(text="Downloading...", state="disabled")
        self.lbl_status.configure(text="Downloading...")

        if self.progress_bar:
            self.progress_bar.destroy()
        self.progress_bar = ctk.CTkProgressBar(self.app, width=400)
        self.progress_bar.grid(padx=10, pady=10, row=8, column=1)
        self.progress_bar.set(0)

        thread = threading.Thread(target=self._download_thread, args=(self.current_video_info.url, file_path, resolution, audio_only), daemon=True)
        thread.start()

    def _download_thread(self, url: str, output_path: str, resolution: Optional[str], audio_only: bool):
        try:
            def progress_hook(data):
                if data["status"] == "downloading":
                    total = data.get("total_bytes") or data.get("total_bytes_estimate")
                    downloaded = data.get("downloaded_bytes", 0)
                    if total:
                        progress = downloaded / total
                        self.app.after(0, lambda: self.progress_bar.set(progress))
                        self.app.after(0, lambda: self.lbl_status.configure(text=f"Downloading... {progress*100:.1f}%"))

            self.video_service.download_video(url, output_path, resolution=resolution, audio_only=audio_only, progress_callback=progress_hook)
            self.app.after(0, self._on_download_success)
        except VideoServiceError as e:
            self.app.after(0, lambda err=e: self._on_download_error(str(err)))
        except Exception as e:
            self.app.after(0, lambda err=e: self._on_download_error(f"Download failed: {err}"))

    def _on_download_success(self):
        self.is_downloading = False
        self.btn_download.configure(text="Download", state="normal")
        self.lbl_status.configure(text="Download complete!")
        if self.progress_bar:
            self.progress_bar.set(1.0)
        if self.lbl_episode:
            self.lbl_episode.configure(text="All episodes downloaded!")
        
        # Add to history
        if hasattr(self, '_last_download') and self.current_video_info:
            self._add_to_history(self._last_download)
        
        messagebox.showinfo("Success", "Video downloaded successfully!")

    def _add_to_history(self, download_info: dict):
        if not self.current_video_info:
            return
        
        file_path = download_info.get("file_path", "")
        file_size = 0
        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
        
        entry = DownloadHistoryEntry(
            title=self.current_video_info.title,
            url=self.current_video_info.url,
            video_id=self.current_video_info.video_id,
            author=self.current_video_info.author,
            resolution=download_info.get("resolution", "Unknown"),
            audio_only=download_info.get("audio_only", False),
            file_path=file_path,
            file_size=file_size,
            download_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            duration=self.current_video_info.length,
            thumbnail_url=self.current_video_info.thumbnail_url
        )
        self.history_manager.add_entry(entry)

    def _on_download_error(self, error_msg: str):
        self.is_downloading = False
        self.btn_download.configure(text="Download", state="normal")
        self.lbl_status.configure(text="Download failed")
        if self.progress_bar:
            self.progress_bar.set(0)
        if self.lbl_episode:
            self.lbl_episode.configure(text="")
        self._show_error(error_msg)

    def _show_error(self, message: str):
        self.lbl_status.configure(text=f"Error: {message}")
        messagebox.showerror("Error", message)

    def run(self):
        self.app.mainloop()


class HistoryWindow:
    def __init__(self, parent, history_manager: HistoryManager):
        self.history_manager = history_manager
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Download History")
        self.window.geometry("900x600")
        self.window.transient(parent)
        self.window.grab_set()
        
        self._setup_ui()
        self._load_history()

    def _setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self.window)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, text="Download History", font=("Arial", 20, "bold")).pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(header_frame, text="Clear All", width=100, fg_color="red", command=self._clear_history).pack(side="right", padx=10, pady=10)
        ctk.CTkButton(header_frame, text="Refresh", width=100, command=self._load_history).pack(side="right", padx=5, pady=10)
        
        # Scrollable list
        self.scroll_frame = ctk.CTkScrollableFrame(self.window)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Status label
        self.lbl_count = ctk.CTkLabel(self.window, text="Loading...")
        self.lbl_count.pack(pady=5)

    def _load_history(self):
        # Clear existing widgets
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        history = self.history_manager.get_history()
        self.lbl_count.configure(text=f"Total downloads: {len(history)}")
        
        if not history:
            ctk.CTkLabel(self.scroll_frame, text="No downloads yet", font=("Arial", 14)).pack(pady=50)
            return
        
        for i, entry in enumerate(history):
            self._create_history_item(entry, i)

    def _create_history_item(self, entry: DownloadHistoryEntry, index: int):
        item_frame = ctk.CTkFrame(self.scroll_frame)
        item_frame.pack(fill="x", padx=5, pady=5)
        
        # Thumbnail
        if entry.thumbnail_url:
            try:
                import urllib.request
                from PIL import Image
                thumb_file = f"thumb_{entry.video_id}.png"
                urllib.request.urlretrieve(entry.thumbnail_url, thumb_file)
                thumb_img = ctk.CTkImage(Image.open(thumb_file), size=(120, 68))
                lbl_thumb = ctk.CTkLabel(item_frame, image=thumb_img, text="")
                lbl_thumb.image = thumb_img  # Keep reference
                lbl_thumb.pack(side="left", padx=10, pady=10)
            except Exception:
                pass
        
        # Info frame
        info_frame = ctk.CTkFrame(item_frame)
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(info_frame, text=entry.title, font=("Arial", 14, "bold"), wraplength=500, anchor="w", justify="left")
        title_label.pack(anchor="w")
        
        # Author
        ctk.CTkLabel(info_frame, text=f"By: {entry.author}", font=("Arial", 11), anchor="w", justify="left").pack(anchor="w")
        
        # Details
        details = []
        if entry.audio_only:
            details.append("Audio only (MP3)")
        else:
            details.append(entry.resolution)
        details.append(f"Duration: {entry.duration // 60}:{entry.duration % 60:02d}")
        details.append(f"Downloaded: {entry.download_time}")
        if entry.file_size > 0:
            size_mb = entry.file_size / (1024 * 1024)
            details.append(f"Size: {size_mb:.1f} MB")
        
        ctk.CTkLabel(info_frame, text=" | ".join(details), font=("Arial", 10), text_color="gray", anchor="w", justify="left").pack(anchor="w")
        
        # Buttons
        btn_frame = ctk.CTkFrame(info_frame)
        btn_frame.pack(anchor="w", pady=5)
        
        ctk.CTkButton(btn_frame, text="Open File", width=100, command=lambda e=entry: self._open_file(e)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Open Folder", width=100, command=lambda e=entry: self._open_folder(e)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Play on YouTube", width=120, command=lambda e=entry: webbrowser.open(e.url)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Remove", width=80, fg_color="red", command=lambda i=index: self._remove_item(i)).pack(side="left", padx=5)

    def _open_file(self, entry: DownloadHistoryEntry):
        if entry.file_path and os.path.exists(entry.file_path):
            import subprocess
            import platform
            if platform.system() == "Windows":
                os.startfile(entry.file_path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", entry.file_path])
            else:
                subprocess.run(["xdg-open", entry.file_path])
        else:
            messagebox.showerror("Error", "File not found")

    def _open_folder(self, entry: DownloadHistoryEntry):
        if entry.file_path and os.path.exists(entry.file_path):
            import subprocess
            import platform
            folder = os.path.dirname(entry.file_path)
            if platform.system() == "Windows":
                subprocess.run(["explorer", "/select,", entry.file_path])
            elif platform.system() == "Darwin":
                subprocess.run(["open", "-R", entry.file_path])
            else:
                subprocess.run(["xdg-open", folder])
        else:
            messagebox.showerror("Error", "File not found")

    def _remove_item(self, index: int):
        if messagebox.askyesno("Remove", "Remove this entry from history?"):
            self.history_manager.remove_entry(index)
            self._load_history()

    def _clear_history(self):
        if messagebox.askyesno("Clear All", "Are you sure you want to clear all download history?"):
            self.history_manager.clear_history()
            self._load_history()


if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.run()