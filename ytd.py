import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import urllib.request
from pytube import YouTube


details_dict = {}


def change_appearance_mode_event(new_appearance_mode: str):
    ctk.set_appearance_mode(new_appearance_mode)


def dir_selector():
    filename = tk.filedialog.asksaveasfilename(initialdir=".", title="Save file as",
                                               initialfile=details_dict.get("title"), filetypes=(("MP3 Files", "*.mp3"),("All Files", "*.*"), ("MP4 Files", "*.mp4")))
    return filename


def download(obj, vid_res):
    vid = obj.streams.get_by_resolution(vid_res)
    try:
        file_name = dir_selector()
        print(file_name)
        print("Downloading Video...")
        lbl_download = ctk.CTkLabel(app, text="Downloading..")
        lbl_download.grid(row=6, column=1)
        vid.download(filename=file_name)
        lbl_download.configure(text="Downloaded")
        print("Video Downloaded")

    except Exception as e:
        print(e)


def size_calculator(obj, vid_res):
    vid = obj.streams.get_by_resolution(vid_res)
    vid_size = vid.filesize_mb
    lbl_filesize = ctk.CTkLabel(app, text=f"Download size: {vid_size} for {res.get()}")
    lbl_filesize.grid(padx=10, pady=10, row=9, column=1)
    show_btn_download()


def select_event(choice):
    resolution = res.get()
    print("selected resolution: ", resolution)
    size_calculator(yt_object_generator(), res)
    return choice


def yt_object_generator():
    vid_url = ent_link.get()
    vid_obj = YouTube(vid_url)
    return vid_obj


def show_btn_download():
    btn_download = ctk.CTkButton(app, text="Download", command=lambda: download(yt_object_generator(), res))
    btn_download.grid(padx=10, pady=10, row=5, column=1)


def verify(yt_obj):
    frm_details = ctk.CTkFrame(master=app, fg_color="grey", width=480, height=300)

    details_dict.update({"title": yt_obj.title, "author": yt_obj.author, "length": yt_obj.length,
                         "views": yt_obj.views})
    print(details_dict)

    thumb_url = yt_obj.thumbnail_url
    thumbnail_file = "vid_thumbnail.png"

    urllib.request.urlretrieve(thumb_url, thumbnail_file)
    thumb_img = ctk.CTkImage(Image.open(thumbnail_file), size=(300, 225))

    lbl_thumbnail = ctk.CTkLabel(frm_details, image=thumb_img, text="")
    lbl_thumbnail.grid()

    lbl_vid_name = ctk.CTkLabel(master=frm_details, text=f"Video Title: {yt_obj.title}", font=("Arial", 16, "bold"),
                                wraplength=450)
    lbl_vid_name.grid(padx=5, pady=5)

    lbl_vid_author = ctk.CTkLabel(master=frm_details, text=f"Author: {yt_obj.author}", font=("Arial", 16))
    lbl_vid_author.grid(padx=5, pady=5)

    lbl_vid_length = ctk.CTkLabel(master=frm_details, text=f"Length: {yt_obj.length//60} min {yt_obj.length % 60} sec",
                                  font=("Arial", 16))
    lbl_vid_length.grid(padx=5, pady=5)

    lbl_vid_views = ctk.CTkLabel(master=frm_details, text=f"Views: {yt_obj.views}", font=("Arial", 16))
    lbl_vid_views.grid(padx=5, pady=5)

    frm_details.grid(padx=10, pady=10, row=3, column=1)
    vid_list = yt_obj.streams.filter(type="video")
    res_list = list(set([stream.resolution for stream in vid_list]))

    menu_options = ctk.CTkOptionMenu(master=app, values=res_list, command=select_event, variable=res)
    menu_options.set("Select Resolution")
    menu_options.bind("<Button>", select_event)
    menu_options.grid(padx=10, pady=10, row=4, column=1)

    return details_dict


# create root app
app = ctk.CTk()
# app.geometry("800x600")
app.title("YTD")
app.iconbitmap("favicon.ico")

res = tk.StringVar()

lbl_prompt = ctk.CTkLabel(master=app, text="Youtube Link: ")
lbl_prompt.grid(padx=10, pady=10, row=1, column=0)

url_var = tk.StringVar()
ent_link = ctk.CTkEntry(master=app, width=400, textvariable=url_var)
ent_link.grid(padx=10, pady=10, row=1, column=1)

btn_verify = ctk.CTkButton(master=app, text="Verify", command=lambda: verify(yt_object_generator()))
btn_verify.grid(padx=10, pady=10, row=1, column=2)

btn_exit = ctk.CTkButton(master=app, text="Exit", width=70, corner_radius=10, fg_color="red", command=app.quit)
btn_exit.grid(padx=10, pady=10, row=10, column=2)

menu_appearance_modes = ctk.CTkOptionMenu(app, values=["Light", "Dark", "System"], command=change_appearance_mode_event)
menu_appearance_modes.set("System")
menu_appearance_modes.grid(row=6, column=0, padx=20, pady=2)

app.mainloop()
