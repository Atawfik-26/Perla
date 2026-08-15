import json
import os

HISTORY_FILE = "chat_history.json"


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)


def add_message(history, role, content):
    history.append({
        "role": role,
        "content": content
    })


def clear_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump([], file, ensure_ascii=False, indent=2)
