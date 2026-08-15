from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Form
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pydantic import BaseModel

import os
import uuid
import shutil


from brain import think


from memory import (
    load_memory,
    save_memory,
    add_memory,
    remove_memory
)


from chat_history import (
    load_history,
    save_history,
    create_chat,
    add_message,
    get_chat,
    get_recent_messages,
    delete_chat
)


app = FastAPI(
    title="Perla"
)


# =========================================
# DATA
# =========================================

memory = load_memory()

history = load_history()


# =========================================
# UPLOADS
# =========================================

UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# =========================================
# DEFAULT CHAT
# =========================================

if not history:

    active_chat = create_chat(
        history,
        "محادثة جديدة"
    )

else:

    active_chat = history[0]


# =========================================
# STATIC
# =========================================

app.mount(

    "/static",

    StaticFiles(
        directory="web"
    ),

    name="static"
)


app.mount(

    "/uploads",

    StaticFiles(
        directory=UPLOAD_DIR
    ),

    name="uploads"
)


# =========================================
# MODELS
# =========================================

class Message(BaseModel):

    message: str


class MemoryItem(BaseModel):

    item: str


# =========================================
# PAGES
# =========================================

@app.get("/")
def home():

    return FileResponse(
        "web/index.html"
    )


@app.get("/app")
def web_app():

    return FileResponse(
        "web/index.html"
    )


# =========================================
# CURRENT CHAT
# =========================================

@app.get("/current-chat")
def current_chat():

    return {
        "chat":
            active_chat
    }


# =========================================
# CHATS
# =========================================

@app.get("/chats")
def get_chats():

    chats = []


    for chat in history:

        chats.append({

            "id":
                chat.get("id"),

            "title":
                chat.get(
                    "title",
                    "محادثة جديدة"
                )
        })


    return {
        "chats":
            chats
    }


@app.post("/chats")
def new_chat():

    global active_chat


    active_chat = create_chat(

        history,

        "محادثة جديدة"
    )


    save_history(
        history
    )


    return {
        "chat":
            active_chat
    }


@app.get("/chats/{chat_id}")
def open_chat(
    chat_id: str
):

    global active_chat


    chat = get_chat(

        history,

        chat_id
    )


    if chat is None:

        raise HTTPException(

            status_code=404,

            detail="Chat not found"
        )


    active_chat = chat


    return {
        "chat":
            active_chat
    }


@app.delete("/chats/{chat_id}")
def remove_chat_route(
    chat_id: str
):

    global active_chat


    if len(history) <= 1:

        active_chat = history[0]

        active_chat["messages"] = []

        active_chat["title"] = (
            "محادثة جديدة"
        )

        save_history(
            history
        )


        return {
            "active_chat":
                active_chat
        }


    deleted = delete_chat(

        history,

        chat_id
    )


    if not deleted:

        raise HTTPException(

            status_code=404,

            detail="Chat not found"
        )


    if active_chat.get("id") == chat_id:

        active_chat = history[0]


    save_history(
        history
    )


    return {
        "active_chat":
            active_chat
    }


# =========================================
# NORMAL CHAT
# =========================================

@app.post("/chat")
def chat(
    data: Message
):

    message = (
        data.message
        .strip()
    )


    if not message:

        return {

            "response":
                "قولّي حاجة يا أحمد 😄",

            "chat_id":
                active_chat.get("id")
        }


    if not active_chat.get(
        "messages"
    ):

        title = (
            message
            .replace(
                "\n",
                " "
            )
            .strip()
        )


        if len(title) > 35:

            title = (
                title[:35]
                + "..."
            )


        active_chat["title"] = title


    add_message(

        active_chat,

        "user",

        message
    )


    recent_history = get_recent_messages(

        active_chat,

        20
    )


    response = think(

        message,

        memory,

        recent_history
    )


    add_message(

        active_chat,

        "assistant",

        response
    )


    save_memory(
        memory
    )

    save_history(
        history
    )


    return {

        "response":
            response,

        "chat_id":
            active_chat.get("id")
    }


# =========================================
# MULTIMODAL CHAT
# =========================================

@app.post(
    "/chat/multimodal"
)
async def multimodal_chat(

    message: str = Form(""),

    file: UploadFile | None =
        File(None)
):

    message = (
        message
        .strip()
    )


    if (
        not message
        and file is None
    ):

        return {

            "response":
                "ابعتلي رسالة أو صورة 😄",

            "chat_id":
                active_chat.get("id")
        }


    file_info = None


    # =====================================
    # SAVE IMAGE
    # =====================================

    if file is not None:

        content_type = (

            file.content_type
            or ""
        )


        if not content_type.startswith(
            "image/"
        ):

            return {

                "response":
                    "بيرلا بتدعم الصور فقط 🖼️",

                "chat_id":
                    active_chat.get("id")
            }


        extension = os.path.splitext(

            file.filename
            or ""
        )[1]


        if not extension:

            extension = ".jpg"


        filename = (

            str(uuid.uuid4())
            + extension
        )


        file_path = os.path.join(

            UPLOAD_DIR,

            filename
        )


        with open(

            file_path,

            "wb"
        ) as buffer:

            shutil.copyfileobj(

                file.file,

                buffer
            )


        file_info = {

            "original_name":
                file.filename,

            "filename":
                filename,

            "content_type":
                content_type,

            "path":
                file_path,

            "url":
                f"/uploads/{filename}"
        }


    # =====================================
    # CHAT TITLE
    # =====================================

    if not active_chat.get(
        "messages"
    ):

        title = (

            message

            or

            file_info[
                "original_name"
            ]
        )


        title = (
            title
            .replace(
                "\n",
                " "
            )
            .strip()
        )


        if len(title) > 35:

            title = (
                title[:35]
                + "..."
            )


        active_chat["title"] = title


    # =====================================
    # USER MESSAGE
    # =====================================

    combined_message = message


    if file_info:

        if combined_message:

            combined_message += (
                "\n\n[تم إرفاق صورة]"
            )

        else:

            combined_message = (
                "[تم إرفاق صورة]"
            )


    add_message(

        active_chat,

        "user",

        combined_message,

        image=file_info
    )


    # =====================================
    # HISTORY
    # =====================================

    recent_history = get_recent_messages(

        active_chat,

        20
    )


    # =====================================
    # BRAIN
    # =====================================

    response = think(

        message,

        memory,

        recent_history,

        image_path=(

            file_info["path"]

            if file_info

            else None
        ),

        image_content_type=(

            file_info["content_type"]

            if file_info

            else None
        )
    )


    # =====================================
    # ASSISTANT
    # =====================================

    add_message(

        active_chat,

        "assistant",

        response
    )


    save_memory(
        memory
    )

    save_history(
        history
    )


    return {

        "response":
            response,

        "chat_id":
            active_chat.get("id"),

        "file":
            file_info
    }


# =========================================
# MEMORY
# =========================================

@app.get("/memory")
def get_memory():

    return {
        "memory":
            memory
    }


@app.post("/memory")
def create_memory(
    data: MemoryItem
):

    item = (
        data.item
        .strip()
    )


    if not item:

        return {

            "success":
                False,

            "message":
                "Empty memory"
        }


    add_memory(

        memory,

        item
    )


    save_memory(
        memory
    )


    return {

        "success":
            True,

        "memory":
            memory
    }


@app.delete("/memory")
def delete_memory(
    data: MemoryItem
):

    item = (
        data.item
        .strip()
    )


    remove_memory(

        memory,

        item
    )


    save_memory(
        memory
    )


    return {

        "success":
            True,

        "memory":
            memory
    }


@app.delete("/memory/all")
def delete_all_memory():

    memory.clear()

    save_memory(
        memory
    )


    return {

        "success":
            True,

        "memory":
            []
    }