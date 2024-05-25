import customtkinter as ctk
import tkinter as tk

from pytube import YouTube


def download(obj, vid_res):
    vid = obj.streams.get_by_resolution(vid_res)
    # vid_size = vid.filesize_mb
    # lbl_filesize = ctk.CTkLabel(app, text=f"Download size: {vid_size} for {res.get()}")
    # lbl_filesize.grid(padx=10, pady=10)
    try:
        print("Downloading Video...")
        lbl_download = ctk.CTkLabel(app, text="Downloading..")
        lbl_download.grid(row=6, column=1)
        vid.download()
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

    lbl_vid_name = ctk.CTkLabel(master=frm_details, text=f"Video Title: {yt_obj.title}")
    lbl_vid_name.grid(padx=10, pady=10)

    lbl_vid_author = ctk.CTkLabel(master=frm_details, text=f"Author: {yt_obj.author}")
    lbl_vid_author.grid(padx=10, pady=10)

    lbl_vid_length = ctk.CTkLabel(master=frm_details, text=f"Length: {yt_obj.length//60} min {yt_obj.length % 60} sec")
    lbl_vid_length.grid(padx=10, pady=10)

    lbl_vid_views = ctk.CTkLabel(master=frm_details, text=f"Views: {yt_obj.views}")
    lbl_vid_views.grid(padx=10, pady=10)

    frm_details.grid(padx=10, pady=10, row=3, column=1)
    vid_list = yt_obj.streams.filter(type="video")
    res_list = list(set([stream.resolution for stream in vid_list]))

    menu_options = ctk.CTkOptionMenu(master=app, values=res_list, command=select_event, variable=res)
    menu_options.set("Select Resolution")
    menu_options.bind("<Button>", select_event)
    menu_options.grid(padx=10, pady=10, row=4, column=1)


# create root app
app = ctk.CTk()
app.geometry("800x600")
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

app.mainloop()
