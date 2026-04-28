import tkinter as tk
import customtkinter as ctk
from app.main import verify, yt_object_generator,change_appearance_mode_event


def set_env_appearance():
    ctk.set_appearance_mode("System")
    ctk.AppearanceModeTracker()
    ctk.set_default_color_theme("blue")  # allowed values are blue and green


# app frame
def appStructure():
    app = ctk.CTk()
    app.geometry("800x600")
    app.title("YTD")
    app.iconbitmap("ytd.ico")

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

    lbl_theme = ctk.CTkLabel(app, text="Select theme")
    lbl_theme.grid(row=5, column=0, padx=5, pady=2)

    appearance_mode_optionmenu = ctk.CTkOptionMenu(app, values=["Light", "Dark", "System"],
                                                   command=change_appearance_mode_event)
    appearance_mode_optionmenu.grid(row=6, column=0, padx=20, pady=2)

    app.mainloop()
    return app


if __name__ == "__main__":
    set_env_appearance()
    appStructure()
