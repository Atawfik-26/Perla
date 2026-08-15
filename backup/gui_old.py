import customtkinter as ctk
from tkinter import END

from brain import think
from memory import load_memory, save_memory
from chat_history import load_history, save_history, add_message


# =========================
# إعدادات بيرلا
# =========================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

memory = load_memory()
history = load_history()


# =========================
# النافذة الرئيسية
# =========================

app = ctk.CTk()
app.title("Perla")
app.geometry("900x700")
app.minsize(700, 550)


# =========================
# الهيدر
# =========================

header = ctk.CTkFrame(
    app,
    height=70,
    corner_radius=0
)

header.pack(
    fill="x",
    side="top"
)

header.pack_propagate(False)


title = ctk.CTkLabel(
    header,
    text="بيرلا",
    font=("Arial", 25, "bold")
)

title.pack(
    side="left",
    padx=25
)


status = ctk.CTkLabel(
    header,
    text="● جاهزة",
    font=("Arial", 13)
)

status.pack(
    side="right",
    padx=25
)


# =========================
# منطقة المحادثة
# =========================

chat_frame = ctk.CTkScrollableFrame(
    app,
    corner_radius=0
)

chat_frame.pack(
    fill="both",
    expand=True,
    padx=10,
    pady=(10, 5)
)


# =========================
# إضافة رسالة
# =========================

def add_chat_message(sender, message):
    if sender == "user":
        bubble_color = "#2563EB"
        anchor = "e"
        name = "أنت"
    else:
        bubble_color = "#2B2B2B"
        anchor = "w"
        name = "بيرلا"

    bubble = ctk.CTkFrame(
        chat_frame,
        fg_color=bubble_color,
        corner_radius=15
    )

    bubble.pack(
        anchor=anchor,
        padx=10,
        pady=6
    )

    name_label = ctk.CTkLabel(
        bubble,
        text=name,
        font=("Arial", 11, "bold")
    )

    name_label.pack(
        anchor="w",
        padx=12,
        pady=(8, 0)
    )

    message_label = ctk.CTkLabel(
        bubble,
        text=message,
        font=("Arial", 14),
        justify="left",
        wraplength=600
    )

    message_label.pack(
        padx=12,
        pady=(3, 10)
    )


# =========================
# عرض المحادثة القديمة
# =========================

def show_old_history():
    for item in history:
        role = item.get("role")
        content = item.get("content", "")

        if role == "user":
            add_chat_message("user", content)

        elif role == "assistant":
            add_chat_message("assistant", content)


# =========================
# إرسال الرسالة
# =========================

def send_message(event=None):

    message = entry.get().strip()

    if not message:
        return

    add_chat_message("user", message)

    add_message(
        history,
        "user",
        message
    )

    status.configure(
        text="● بتفكر..."
    )

    app.update_idletasks()

    response = think(
        message,
        memory,
        history
    )

    add_message(
        history,
        "assistant",
        response
    )

    save_memory(memory)
    save_history(history)

    add_chat_message(
        "assistant",
        response
    )

    status.configure(
        text="● جاهزة"
    )

    entry.delete(
        0,
        END
    )

    chat_frame._parent_canvas.yview_moveto(1.0)


# =========================
# منطقة الكتابة
# =========================

input_frame = ctk.CTkFrame(
    app,
    corner_radius=15
)

input_frame.pack(
    fill="x",
    padx=15,
    pady=(5, 15)
)


entry = ctk.CTkEntry(
    input_frame,
    placeholder_text="اكتب لبيرلا...",
    height=50,
    font=("Arial", 14)
)

entry.pack(
    side="left",
    fill="x",
    expand=True,
    padx=(12, 6),
    pady=12
)


send_button = ctk.CTkButton(
    input_frame,
    text="إرسال",
    width=100,
    height=45,
    font=("Arial", 14, "bold"),
    command=send_message
)

send_button.pack(
    side="right",
    padx=(6, 12),
    pady=12
)


entry.bind(
    "<Return>",
    send_message
)


# =========================
# تشغيل
# =========================

show_old_history()

entry.focus()

app.mainloop()