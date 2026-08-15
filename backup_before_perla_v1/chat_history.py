import json
import os
import uuid
from datetime import datetime


HISTORY_FILE = "chat_history.json"


def load_history():

    if not os.path.exists(HISTORY_FILE):
        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if not isinstance(data, list):
                return []

            return data

    except Exception:

        return []


def save_history(history):

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            ensure_ascii=False,
            indent=2
        )


def create_chat(
    history,
    title="محادثة جديدة"
):

    chat = {

        "id": str(uuid.uuid4()),

        "title": title,

        "created_at":
            datetime.now().isoformat(),

        "messages": []
    }

    history.insert(
        0,
        chat
    )

    save_history(history)

    return chat


def add_message(
    chat,
    role,
    content,
    image=None
):

    chat.setdefault(
        "messages",
        []
    )

    message = {

        "role": role,

        "content": content
    }

    if image:

        message["image"] = image

    chat["messages"].append(
        message
    )


def get_chat(
    history,
    chat_id
):

    for chat in history:

        if chat.get("id") == chat_id:

            return chat

    return None


def get_recent_messages(
    chat,
    limit=20
):

    messages = chat.get(
        "messages",
        []
    )

    return messages[-limit:]


def get_all_chats(history):

    return list(history)


def delete_chat(
    history,
    chat_id
):

    for index, chat in enumerate(history):

        if chat.get("id") == chat_id:

            history.pop(index)

            save_history(history)

            return True

    return False


def clear_history(history):

    history.clear()

    save_history(history)


def chat_exists(
    history,
    chat_id
):

    return get_chat(
        history,
        chat_id
    ) is not None