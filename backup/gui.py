import customtkinter as ctk

from brain import think
from memory import load_memory, save_memory
from chat_history import load_history, save_history, add_message
from ui import PerlaUI


memory = load_memory()
history = load_history()


def handle_message(message):

    ui.add_message("user", message)
    add_message(history, "user", message)

    ui.set_status("بتفكر...")

    app.update_idletasks()

    response = think(
        message,
        memory,
        history
    )

    add_message(history, "assistant", response)

    save_memory(memory)
    save_history(history)

    ui.add_message(
        "assistant",
        response
    )

    ui.set_status("جاهزة")


app = ctk.CTk()

ui = PerlaUI(
    app,
    handle_message
)


# عرض المحادثات القديمة
for item in history:

    role = item.get("role")
    content = item.get("content", "")

    if role == "user":
        ui.add_message("user", content)

    elif role == "assistant":
        ui.add_message("assistant", content)


ui.entry.focus()

app.mainloop()