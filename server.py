from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import os
import uuid
import shutil
import traceback
import json
import time
from datetime import datetime
from collections import defaultdict

from brain import think
from planner import plan_task, needs_planning
from router import router
from file_tools import create_docx, create_pdf, create_pptx
from image_tools import generate_image

from memory import (
    load_memory,
    save_memory,
    add_memory,
    remove_memory,
    get_due_reminders,
    mark_reminded
)

from chat_history import (
    load_history,
    save_history,
    create_chat,
    add_message,
    get_chat,
    get_recent_messages,
    delete_chat,
    touch_chat
)

from voice_free import (
    transcribe_audio,
    text_to_speech,
    voice_chat_pipeline
)


# =========================================================
# APP
# =========================================================

app = FastAPI(title="Perla")


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# RATE LIMIT
# =========================================================

RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW = 60

request_counts = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):

    client_ip = (
        request.client.host
        if request.client
        else "unknown"
    )

    now = time.time()

    request_counts[client_ip] = [
        t
        for t in request_counts[client_ip]
        if now - t < RATE_LIMIT_WINDOW
    ]

    if len(request_counts[client_ip]) >= RATE_LIMIT_REQUESTS:

        return JSONResponse(
            status_code=429,
            content={
                "error": True,
                "message": "كترت الطلبات شوية. استنى دقيقة وجرب تاني."
            }
        )

    request_counts[client_ip].append(now)

    return await call_next(request)


# =========================================================
# MEMORY / HISTORY
# =========================================================

memory = load_memory()
history = load_history()


# =========================================================
# DIRECTORIES
# =========================================================

UPLOAD_DIR = "uploads"
FILES_DIR = "files"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)


# =========================================================
# TASK TYPES
# =========================================================

FILE_TASK_TYPES = {
    "file_word",
    "file_pdf",
    "file_pptx",
}

IMAGE_TASK_TYPE = "image_generate"


# =========================================================
# ACTIVE CHAT
# =========================================================

if not history:

    active_chat = create_chat(
        history,
        "محادثة جديدة"
    )

    save_history(history)

else:

    active_chat = history[0]


# =========================================================
# STATIC FILES
# =========================================================

app.mount(
    "/static",
    StaticFiles(directory="web"),
    name="static"
)

app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR),
    name="uploads"
)

app.mount(
    "/files",
    StaticFiles(directory=FILES_DIR),
    name="files"
)


# =========================================================
# MODELS
# =========================================================

class Message(BaseModel):
    message: str


class MemoryItem(BaseModel):
    item: str


class ReminderItem(BaseModel):
    item: str
    remind_on: str


# =========================================================
# FILE GENERATION
# =========================================================

def handle_file_generation(
    message,
    memory,
    recent_history,
    history,
    task_type
):

    print(
        f"\n[PERLA FILE] إنشاء ملف من النوع: {task_type}"
    )

    content = think(
        (
            "اكتب محتوى جاهز فقط، من غير مقدمات "
            "مثل أكيد أو تمام، عشان يتحط داخل ملف.\n\n"
            f"طلب المستخدم:\n{message}"
        ),
        memory,
        recent_history,
        history_obj=history,
        task_type="creative"
    )

    if not content:
        raise RuntimeError(
            "بيرلا لم تستطع توليد محتوى الملف."
        )

    title = (
        message
        .strip()
        .replace("\n", " ")
    )[:50]

    # -----------------------------------------------------
    # WORD
    # -----------------------------------------------------

    if task_type == "file_word":

        path, filename = create_docx(
            content,
            title=title
        )

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    elif task_type == "file_pdf":

        path, filename = create_pdf(
            content,
            title=title
        )

    # -----------------------------------------------------
    # POWERPOINT
    # -----------------------------------------------------

    elif task_type == "file_pptx":

        path, filename = create_pptx(
            content,
            title=title
        )

    else:

        raise ValueError(
            f"نوع ملف غير معروف: {task_type}"
        )

    if not os.path.exists(path):

        raise RuntimeError(
            "تم استدعاء أداة إنشاء الملف لكن الملف لم يتم إنشاؤه."
        )

    file_url = f"/files/{filename}"

    reply = (
        f"جهزتلك الملف يا تيتو ✅\n\n"
        f"[تحميل الملف]({file_url})"
    )

    print(
        f"[PERLA FILE] تم إنشاء: {path}"
    )

    return reply, file_url


# =========================================================
# IMAGE GENERATION
# =========================================================

def handle_image_generation(message):

    print(
        "\n[PERLA IMAGE] بدء توليد الصورة..."
    )

    try:

        path, filename = generate_image(
            message
        )

        if not os.path.exists(path):

            raise RuntimeError(
                "أداة الصور رجعت مسار لكن الملف غير موجود."
            )

        file_url = f"/files/{filename}"

        reply = (
            f"جهزتلك الصورة يا تيتو 🖼️\n\n"
            f"[عرض الصورة]({file_url})"
        )

        print(
            f"[PERLA IMAGE] تم إنشاء: {path}"
        )

        return reply, file_url

    except Exception as error:

        print(
            f"[PERLA IMAGE ERROR] {repr(error)}"
        )

        traceback.print_exc()

        return (
            f"معرفتش أولد الصورة 😕\n\n"
            f"السبب: {str(error)}",
            None
        )


# =========================================================
# HOME
# =========================================================

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


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "perla": "ready",
        "chat_id": active_chat.get("id")
    }


# =========================================================
# CURRENT CHAT
# =========================================================

@app.get("/current-chat")
def current_chat():

    return {
        "chat": active_chat
    }


# =========================================================
# CHATS
# =========================================================

@app.get("/chats")
def get_chats():

    return {
        "chats": [
            {
                "id": c.get("id"),
                "title": c.get(
                    "title",
                    "محادثة جديدة"
                )
            }
            for c in history
        ]
    }


@app.post("/chats")
def new_chat():

    global active_chat

    active_chat = create_chat(
        history,
        "محادثة جديدة"
    )

    save_history(history)

    return {
        "chat": active_chat
    }


@app.get("/chats/{chat_id}")
def open_chat(chat_id: str):

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

    touch_chat(
        history,
        chat_id
    )

    save_history(history)

    return {
        "chat": active_chat
    }


@app.delete("/chats/{chat_id}")
def remove_chat_route(chat_id: str):

    global active_chat

    if len(history) <= 1:

        active_chat = history[0]

        active_chat["messages"] = []

        active_chat["title"] = (
            "محادثة جديدة"
        )

        save_history(history)

        return {
            "active_chat": active_chat
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

    save_history(history)

    return {
        "active_chat": active_chat
    }


# =========================================================
# EXPORT CHAT
# =========================================================

@app.get("/chats/{chat_id}/export")
def export_chat(
    chat_id: str,
    format: str = "markdown"
):

    chat = get_chat(
        history,
        chat_id
    )

    if chat is None:

        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    if format == "json":

        return JSONResponse(
            content=chat
        )

    title = chat.get(
        "title",
        "محادثة بيرلا"
    )

    lines = [
        f"# {title}",
        f"\n**تاريخ الإنشاء:** "
        f"{chat.get('created_at', '')}",
        "---\n"
    ]

    for msg in chat.get(
        "messages",
        []
    ):

        role = (
            "🧑 أحمد"
            if msg.get("role") == "user"
            else "🤖 بيرلا"
        )

        lines.append(
            f"### {role}\n"
            f"{msg.get('content', '')}\n"
        )

    return JSONResponse(
        content={
            "title": title,
            "markdown": "\n".join(lines),
            "filename": (
                f"perla_{chat_id[:8]}.md"
            )
        }
    )


# =========================================================
# STREAM CHAT
# =========================================================

@app.post("/chat/stream")
async def chat_stream(data: Message):

    message = (
        data.message
        .strip()
    )

    if not message:

        async def empty_stream():

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "content": (
                            "قولّي حاجة يا أحمد 😄"
                        )
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

        return StreamingResponse(
            empty_stream(),
            media_type="text/event-stream"
        )

    if not active_chat.get(
        "messages"
    ):

        title = (
            message
            .replace("\n", " ")
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

    # =====================================================
    # ROUTER
    # =====================================================

    task_type = router.choose(
        message=message
    )

    print(
        "\n========== PERLA SERVER ROUTING =========="
    )

    print(
        f"[SERVER TASK] {task_type}"
    )

    print(
        "===========================================\n"
    )

    # =====================================================
    # FILES / IMAGE
    # =====================================================

    if (
        task_type in FILE_TASK_TYPES
        or task_type == IMAGE_TASK_TYPE
    ):

        try:

            if task_type in FILE_TASK_TYPES:

                response, file_url = (
                    handle_file_generation(
                        message,
                        memory,
                        recent_history,
                        history,
                        task_type
                    )
                )

            else:

                response, file_url = (
                    handle_image_generation(
                        message
                    )
                )

        except Exception as error:

            traceback.print_exc()

            response = (
                "حصل خطأ وأنا بحاول "
                "أجهز الملف 😕\n\n"
                f"{str(error)}"
            )

            file_url = None

        add_message(
            active_chat,
            "assistant",
            response
        )

        save_memory(memory)
        save_history(history)

        async def file_stream():

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "done",
                        "content": response,
                        "file_url": file_url,
                        "task_type": task_type,
                        "chat_id": (
                            active_chat.get("id")
                        )
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

        return StreamingResponse(
            file_stream(),
            media_type="text/event-stream"
        )

    # =====================================================
    # PLANNER
    # =====================================================

    if needs_planning(
        message,
        task_type
    ):

        response = plan_task(
            message,
            memory
        )

        add_message(
            active_chat,
            "assistant",
            response
        )

        save_memory(memory)
        save_history(history)

        async def plan_stream():

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "planned",
                        "content": response,
                        "chat_id": (
                            active_chat.get("id")
                        )
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

        return StreamingResponse(
            plan_stream(),
            media_type="text/event-stream"
        )

    # =====================================================
    # NORMAL AI STREAM
    # =====================================================

    from openai import AsyncOpenAI

    from brain import (
        get_api_key,
        OPENROUTER_BASE_URL,
        build_context,
        choose_models
    )

    api_key = get_api_key()

    if not api_key:

        async def err():

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "content": (
                            "مفتاح OpenRouter "
                            "مش موجود في ملف .env."
                        )
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

        return StreamingResponse(
            err(),
            media_type="text/event-stream"
        )

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL
    )

    instructions = build_context(
        memory or [],
        recent_history,
        message,
        history
    )

    _, candidates = choose_models(
        message,
        task_type=task_type
    )

    async def generate():

        full_response = ""
        used_model = None

        for model in candidates:

            try:

                used_model = model

                print(
                    f"[PERLA STREAM] "
                    f"Trying model: {model}"
                )

                stream = (
                    await client.chat.completions.create(
                        model=model,
                        max_tokens=3000,
                        messages=[
                            {
                                "role": "system",
                                "content": instructions
                            },
                            {
                                "role": "user",
                                "content": message
                            }
                        ],
                        stream=True
                    )
                )

                async for chunk in stream:

                    if (
                        not chunk.choices
                    ):
                        continue

                    delta = (
                        chunk.choices[0]
                        .delta.content
                        or ""
                    )

                    if delta:

                        full_response += delta

                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "chunk",
                                    "content": delta
                                },
                                ensure_ascii=False
                            )
                            + "\n\n"
                        )

                break

            except Exception as error:

                print(
                    f"[PERLA STREAM] "
                    f"{model} فشل: "
                    f"{repr(error)}"
                )

                continue

        if not full_response:

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "content": (
                            "كل الموديلات فشلت 😕"
                        )
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

            return

        yield (
            "data: "
            + json.dumps(
                {
                    "type": "done",
                    "content": full_response,
                    "model": used_model,
                    "chat_id": (
                        active_chat.get("id")
                    )
                },
                ensure_ascii=False
            )
            + "\n\n"
        )

        add_message(
            active_chat,
            "assistant",
            full_response
        )

        save_memory(memory)
        save_history(history)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


# =========================================================
# NORMAL CHAT
# =========================================================

@app.post("/chat")
def chat(data: Message):

    message = (
        data.message
        .strip()
    )

    if not message:

        return {
            "response": (
                "قولّي حاجة يا أحمد 😄"
            ),
            "chat_id": (
                active_chat.get("id")
            )
        }

    if not active_chat.get(
        "messages"
    ):

        title = (
            message
            .replace("\n", " ")
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

    task_type = router.choose(
        message=message
    )

    print(
        f"[PERLA TASK] {task_type}"
    )

    file_url = None
    auto_planned = False

    # =====================================================
    # FILE
    # =====================================================

    if task_type in FILE_TASK_TYPES:

        response, file_url = (
            handle_file_generation(
                message,
                memory,
                recent_history,
                history,
                task_type
            )
        )

    # =====================================================
    # IMAGE
    # =====================================================

    elif task_type == IMAGE_TASK_TYPE:

        response, file_url = (
            handle_image_generation(
                message
            )
        )

    # =====================================================
    # NORMAL
    # =====================================================

    else:

        auto_planned = needs_planning(
            message,
            task_type
        )

        if auto_planned:

            response = plan_task(
                message,
                memory
            )

        else:

            response = think(
                message,
                memory,
                recent_history,
                history_obj=history,
                task_type=task_type
            )

    add_message(
        active_chat,
        "assistant",
        response
    )

    save_memory(memory)
    save_history(history)

    return {
        "response": response,
        "chat_id": active_chat.get("id"),
        "planned": auto_planned,
        "file_url": file_url,
        "task_type": task_type
    }


# =========================================================
# PLANNER
# =========================================================

@app.post("/chat/plan")
def chat_plan(data: Message):

    message = (
        data.message
        .strip()
    )

    if not message:

        return {
            "response": (
                "قولّي المهمة يا أحمد 😄"
            ),
            "chat_id": (
                active_chat.get("id")
            )
        }

    if not active_chat.get(
        "messages"
    ):

        title = (
            message
            .replace("\n", " ")
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

    response = plan_task(
        message,
        memory
    )

    add_message(
        active_chat,
        "assistant",
        response
    )

    save_memory(memory)
    save_history(history)

    return {
        "response": response,
        "chat_id": active_chat.get("id")
    }


# =========================================================
# IMAGE / MULTIMODAL CHAT
# =========================================================

@app.post("/chat/multimodal")
async def multimodal_chat(
    message: str = Form(""),
    file: UploadFile | None = File(None)
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
            "response": (
                "ابعتلي رسالة أو صورة 😄"
            ),
            "chat_id": (
                active_chat.get("id")
            )
        }

    file_info = None

    if file is not None:

        content_type = (
            file.content_type
            or ""
        )

        if not content_type.startswith(
            "image/"
        ):

            return {
                "response": (
                    "بيرلا بتدعم الصور "
                    "فقط دلوقتي 🖼️"
                ),
                "chat_id": (
                    active_chat.get("id")
                )
            }

        extension = os.path.splitext(
            file.filename or ""
        )[1] or ".jpg"

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
            "original_name": file.filename,
            "filename": filename,
            "content_type": content_type,
            "path": file_path,
            "url": (
                f"/uploads/{filename}"
            )
        }

    if not active_chat.get(
        "messages"
    ):

        title = (
            message
            or file_info["original_name"]
        )

        title = (
            title
            .replace("\n", " ")
            .strip()
        )

        if len(title) > 35:

            title = (
                title[:35]
                + "..."
            )

        active_chat["title"] = title

    combined_message = message

    if file_info:

        combined_message += (
            "\n\n[صورة مرفقة]"
        )

    add_message(
        active_chat,
        "user",
        combined_message
    )

    if file_info:

        active_chat["messages"][-1][
            "image"
        ] = {
            "url": file_info["url"],
            "filename": file_info["filename"],
            "original_name": file_info[
                "original_name"
            ],
            "content_type": file_info[
                "content_type"
            ],
            "path": file_info["path"]
        }

    recent_history = get_recent_messages(
        active_chat,
        20
    )

    response = think(
        message,
        memory,
        recent_history,
        history_obj=history,
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

    add_message(
        active_chat,
        "assistant",
        response
    )

    save_memory(memory)
    save_history(history)

    return {
        "response": response,
        "chat_id": active_chat.get("id"),
        "file": file_info
    }


# =========================================================
# AUDIO CHAT
# =========================================================

@app.post("/chat/audio")
async def audio_chat(
    message: str = Form(""),
    audio: UploadFile | None = File(None)
):

    message = (
        message or ""
    ).strip()

    if audio is None:

        return {
            "response": (
                "مش لاقي التسجيل "
                "الصوتي يا أحمد 🎤"
            ),
            "chat_id": (
                active_chat.get("id")
            )
        }

    content_type = (
        audio.content_type
        or ""
    )

    if not content_type.startswith(
        "audio/"
    ):

        return {
            "response": (
                "الملف اللي وصل "
                "مش تسجيل صوتي 🎤"
            ),
            "chat_id": (
                active_chat.get("id")
            )
        }

    extension = os.path.splitext(
        audio.filename or ""
    )[1]

    if not extension:

        if "webm" in content_type:

            extension = ".webm"

        elif "wav" in content_type:

            extension = ".wav"

        elif "mpeg" in content_type:

            extension = ".mp3"

        elif "mp4" in content_type:

            extension = ".m4a"

        else:

            extension = ".webm"

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
            audio.file,
            buffer
        )

    combined_message = (
        message
        if message
        else "[تسجيل صوتي]"
    )

    if not active_chat.get(
        "messages"
    ):

        title = (
            message
            if message
            else "تسجيل صوتي"
        )

        title = (
            title
            .replace("\n", " ")
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
        combined_message
    )

    recent_history = get_recent_messages(
        active_chat,
        20
    )

    response = think(
        message,
        memory,
        recent_history,
        history_obj=history,
        audio_path=file_path,
        audio_content_type=content_type
    )

    add_message(
        active_chat,
        "assistant",
        response
    )

    save_memory(memory)
    save_history(history)

    return {
        "response": response,
        "chat_id": active_chat.get("id"),
        "file": {
            "filename": filename,
            "content_type": content_type,
            "url": (
                f"/uploads/{filename}"
            )
        }
    }


# =========================================================
# VIDEO CHAT / ANALYSIS
# =========================================================

@app.post("/chat/video")
async def video_chat(
    message: str = Form(""),
    video: UploadFile | None = File(None)
):

    message = (
        message or ""
    ).strip()

    if video is None:

        return {
            "response": (
                "مش لاقي فيديو يا أحمد 🎬"
            ),
            "chat_id": (
                active_chat.get("id")
            )
        }

    content_type = (
        video.content_type
        or ""
    )

    if not content_type.startswith(
        "video/"
    ):

        return {
            "response": (
                "الملف اللي وصل "
                "مش فيديو 🎬"
            ),
            "chat_id": (
                active_chat.get("id")
            )
        }

    extension = os.path.splitext(
        video.filename or ""
    )[1]

    if not extension:

        if "mp4" in content_type:

            extension = ".mp4"

        elif "webm" in content_type:

            extension = ".webm"

        elif "quicktime" in content_type:

            extension = ".mov"

        elif "x-matroska" in content_type:

            extension = ".mkv"

        else:

            extension = ".mp4"

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
            video.file,
            buffer
        )

    combined_message = (
        message
        if message
        else "[فيديو مرفق]"
    )

    if not active_chat.get(
        "messages"
    ):

        title = (
            message
            if message
            else "فيديو مرفق"
        )

        title = (
            title
            .replace("\n", " ")
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
        combined_message
    )

    active_chat["messages"][-1][
        "video"
    ] = {
        "url": (
            f"/uploads/{filename}"
        ),
        "filename": filename,
        "original_name": video.filename,
        "content_type": content_type,
        "path": file_path
    }

    recent_history = get_recent_messages(
        active_chat,
        20
    )

    response = think(
        message,
        memory,
        recent_history,
        history_obj=history,
        video_path=file_path,
        video_content_type=content_type
    )

    add_message(
        active_chat,
        "assistant",
        response
    )

    save_memory(memory)
    save_history(history)

    return {
        "response": response,
        "chat_id": active_chat.get("id"),
        "file": {
            "filename": filename,
            "content_type": content_type,
            "url": (
                f"/uploads/{filename}"
            )
        }
    }


# =========================================================
# STT
# =========================================================

@app.post("/stt")
async def stt_endpoint(
    audio: UploadFile = File(...)
):

    extension = os.path.splitext(
        audio.filename or ""
    )[1] or ".webm"

    filename = (
        f"stt_"
        f"{uuid.uuid4().hex[:8]}"
        f"{extension}"
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
            audio.file,
            buffer
        )

    try:

        text = transcribe_audio(
            file_path
        )

        return {
            "success": True,
            "text": text,
            "filename": filename
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =========================================================
# TTS
# =========================================================

@app.post("/tts")
async def tts_endpoint(
    data: Message
):

    text = (
        data.message
        .strip()
    )

    if not text:

        raise HTTPException(
            status_code=400,
            detail="النص فاضي"
        )

    try:

        audio_path = text_to_speech(
            text
        )

        filename = os.path.basename(
            audio_path
        )

        return {
            "success": True,
            "audio_url": (
                f"/uploads/{filename}"
            ),
            "filename": filename
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =========================================================
# VOICE CHAT
# =========================================================

@app.post("/chat/voice")
async def chat_voice(
    audio: UploadFile = File(...),
    message: str = Form(""),
    voice: str = Form("alloy")
):

    extension = os.path.splitext(
        audio.filename or ""
    )[1]

    if not extension:

        content_type = (
            audio.content_type
            or ""
        )

        if "webm" in content_type:

            extension = ".webm"

        elif "wav" in content_type:

            extension = ".wav"

        elif (
            "mp3" in content_type
            or "mpeg" in content_type
        ):

            extension = ".mp3"

        else:

            extension = ".webm"

    filename = (
        f"voice_in_"
        f"{uuid.uuid4().hex[:8]}"
        f"{extension}"
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
            audio.file,
            buffer
        )

    try:

        result = voice_chat_pipeline(
            audio_path=file_path,
            brain_think_func=think,
            memory=memory,
            history=get_recent_messages(
                active_chat,
                20
            ),
            history_obj=history,
            message=message,
            voice=voice
        )

    except Exception as error:

        print(
            f"[PERLA VOICE ERROR] "
            f"{repr(error)}"
        )

        traceback.print_exc()

        return {
            "success": False,
            "error": str(error),
            "chat_id": (
                active_chat.get("id")
            )
        }

    combined = (
        message.strip()
    )

    if combined:

        combined += (
            f"\n[صوت: "
            f"{result['transcription']}]"
        )

    else:

        combined = result[
            "transcription"
        ]

    if not active_chat.get(
        "messages"
    ):

        title = (
            result["transcription"]
            .replace("\n", " ")
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
        combined
    )

    add_message(
        active_chat,
        "assistant",
        result["response"]
    )

    save_memory(memory)
    save_history(history)

    return {
        "success": True,
        "transcription": result[
            "transcription"
        ],
        "response": result["response"],
        "audio_url": result["audio_url"],
        "chat_id": active_chat.get("id")
    }


# =========================================================
# VOICE STREAM
# =========================================================

@app.post("/chat/voice/stream")
async def chat_voice_stream(
    audio: UploadFile = File(...),
    message: str = Form(""),
    voice: str = Form("alloy")
):

    extension = os.path.splitext(
        audio.filename or ""
    )[1] or ".webm"

    filename = (
        f"voice_in_"
        f"{uuid.uuid4().hex[:8]}"
        f"{extension}"
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
            audio.file,
            buffer
        )

    async def generate():

        try:

            transcription = (
                transcribe_audio(
                    file_path
                )
            )

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "transcription",
                        "content": transcription
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

        except Exception as error:

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "content": (
                            f"STT Error: "
                            f"{str(error)}"
                        )
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

            return

        full_message = (
            message.strip()
        )

        if full_message:

            full_message += (
                f"\n[صوت: "
                f"{transcription}]"
            )

        else:

            full_message = transcription

        from brain import (
            get_api_key,
            OPENROUTER_BASE_URL,
            build_context,
            choose_models
        )

        api_key = get_api_key()

        if not api_key:

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "content": (
                            "مفتاح API مش موجود"
                        )
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

            return

        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL
        )

        recent = get_recent_messages(
            active_chat,
            20
        )

        instructions = build_context(
            memory or [],
            recent,
            full_message,
            history
        )

        _, candidates = choose_models(
            full_message
        )

        full_response = ""
        used_model = None

        for model in candidates:

            try:

                used_model = model

                stream = (
                    await client
                    .chat
                    .completions
                    .create(
                        model=model,
                        max_tokens=3000,
                        messages=[
                            {
                                "role": "system",
                                "content": instructions
                            },
                            {
                                "role": "user",
                                "content": full_message
                            }
                        ],
                        stream=True
                    )
                )

                async for chunk in stream:

                    if not chunk.choices:

                        continue

                    delta = (
                        chunk.choices[0]
                        .delta.content
                        or ""
                    )

                    if delta:

                        full_response += delta

                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "chunk",
                                    "content": delta
                                },
                                ensure_ascii=False
                            )
                            + "\n\n"
                        )

                break

            except Exception as error:

                print(
                    f"[PERLA VOICE STREAM] "
                    f"{model} فشل: "
                    f"{repr(error)}"
                )

                continue

        if not full_response:

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "content": (
                            "كل الموديلات فشلت 😕"
                        )
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

            return

        try:

            audio_out_path = (
                text_to_speech(
                    full_response
                )
            )

            audio_filename = (
                os.path.basename(
                    audio_out_path
                )
            )

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "audio",
                        "audio_url": (
                            f"/uploads/"
                            f"{audio_filename}"
                        )
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

        except Exception as error:

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "content": (
                            f"TTS Error: "
                            f"{str(error)}"
                        )
                    },
                    ensure_ascii=False
                )
                + "\n\n"
            )

        yield (
            "data: "
            + json.dumps(
                {
                    "type": "done",
                    "content": full_response,
                    "model": used_model,
                    "chat_id": (
                        active_chat.get("id")
                    )
                },
                ensure_ascii=False
            )
            + "\n\n"
        )

        combined = (
            message.strip()
        )

        if combined:

            combined += (
                f"\n[صوت: "
                f"{transcription}]"
            )

        else:

            combined = transcription

        if not active_chat.get(
            "messages"
        ):

            title = (
                transcription
                .replace("\n", " ")
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
            combined
        )

        add_message(
            active_chat,
            "assistant",
            full_response
        )

        save_memory(memory)
        save_history(history)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


# =========================================================
# MEMORY
# =========================================================

@app.get("/memory")
def get_memory():

    return {
        "memory": memory
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
            "success": False,
            "message": "Empty memory"
        }

    add_memory(
        memory,
        item
    )

    save_memory(memory)

    return {
        "success": True,
        "memory": memory
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

    save_memory(memory)

    return {
        "success": True,
        "memory": memory
    }


@app.delete("/memory/all")
def delete_all_memory():

    memory.clear()

    save_memory(memory)

    return {
        "success": True,
        "memory": []
    }


# =========================================================
# REMINDERS
# =========================================================

@app.post("/reminders")
def create_reminder(
    data: ReminderItem
):

    item = (
        data.item
        .strip()
    )

    if not item:

        return {
            "success": False,
            "message": "Empty reminder"
        }

    try:

        datetime.strptime(
            data.remind_on,
            "%Y-%m-%d"
        )

    except ValueError:

        return {
            "success": False,
            "message": (
                "صيغة التاريخ غلط. "
                "استخدم YYYY-MM-DD"
            )
        }

    add_memory(
        memory,
        item,
        remind_on=data.remind_on
    )

    save_memory(memory)

    return {
        "success": True,
        "memory": memory
    }


@app.get("/reminders/due")
def due_reminders():

    due = get_due_reminders(
        memory
    )

    for entry in due:

        mark_reminded(
            memory,
            entry["id"]
        )

    if due:

        save_memory(memory)

    return {
        "reminders": [
            entry["text"]
            for entry in due
        ]
    }


# =========================================================
# GLOBAL ERROR
# =========================================================

@app.exception_handler(Exception)
async def global_error_handler(
    request,
    exc
):

    print(
        "\n========== "
        "PERLA SERVER ERROR "
        "=========="
    )

    traceback.print_exc()

    print(
        "========================================\n"
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": (
                "حصل خطأ في بيرلا. "
                "راجع CMD لمعرفة السبب."
            )
        }
    )
