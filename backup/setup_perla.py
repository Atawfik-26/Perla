import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
BACKUP = ROOT / "backup_before_perla_v1"


def backup_file(path):
    if path.exists():
        BACKUP.mkdir(exist_ok=True)
        target = BACKUP / path.name

        if not target.exists():
            shutil.copy2(path, target)
            print(f"[BACKUP] {path.name}")


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[WRITE] {path}")


# =========================================================
# DIRECTORIES
# =========================================================

WEB.mkdir(exist_ok=True)
(ROOT / "uploads").mkdir(exist_ok=True)


# =========================================================
# BACKUP
# =========================================================

for filename in [
    "brain.py",
    "main.py",
    "config.py",
    "memory.py",
    "chat_history.py",
]:
    backup_file(ROOT / filename)


# =========================================================
# BRAIN
# =========================================================

brain = r'''
import os
import base64

from dotenv import load_dotenv
from openai import OpenAI

from config import PERSONALITY


load_dotenv()


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-4o"
)

MAX_TOKENS = int(
    os.getenv(
        "PERLA_MAX_TOKENS",
        "4096"
    )
)


def get_api_key():
    return os.getenv("OPENROUTER_API_KEY")


def build_context(memory, history):

    memory_text = "\n".join(
        f"- {item}"
        for item in memory
    ) if memory else "لا توجد معلومات محفوظة حتى الآن."

    history_text = "\n".join(
        f"{item.get('role', 'user')}: "
        f"{item.get('content', '')}"
        for item in history[-20:]
    ) if history else "لا توجد محادثة سابقة."

    return f"""
{PERSONALITY}

الذاكرة الحالية لأحمد:
{memory_text}

المحادثة الحالية:
{history_text}

تعليمات مهمة:
- أنتِ بيرلا.
- تحدثي بالعربية المصرية الطبيعية.
- استخدمي الذاكرة عندما تكون مفيدة.
- لا تختلقي معلومات.
- لا تدّعي تنفيذ شيء لم يتم تنفيذه.
- إذا أُرسلت صورة، حللي الصورة فعليًا.
- إذا كان السؤال متعلقًا بالصورة، اعتمدي على محتوى الصورة.
- لا تقولي إنك لا تستطيعين رؤية الصورة إذا تم إرسالها لك فعليًا.
- كوني ودودة وطبيعية ومختصرة عندما لا يحتاج السؤال إلى تفصيل.
"""


def image_to_data_url(path, content_type):

    with open(path, "rb") as f:
        encoded = base64.b64encode(
            f.read()
        ).decode("utf-8")

    return (
        f"data:{content_type};base64,"
        f"{encoded}"
    )


def think(
    message,
    memory,
    history=None,
    image_path=None,
    image_content_type=None
):

    message = (message or "").strip()

    if not message and not image_path:
        return "قولّي حاجة يا أحمد 😄"

    api_key = get_api_key()

    if not api_key:
        return (
            "مفتاح OpenRouter مش موجود في ملف .env."
        )

    try:

        client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL
        )

        instructions = build_context(
            memory or [],
            history or []
        )

        if image_path:

            image_url = image_to_data_url(
                image_path,
                image_content_type or "image/jpeg"
            )

            user_content = [
                {
                    "type": "text",
                    "text": (
                        message
                        or
                        "حللي الصورة دي ووصفيلي اللي فيها."
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                }
            ]

        else:

            user_content = message

        response = client.chat.completions.create(

            model=OPENROUTER_MODEL,

            max_tokens=MAX_TOKENS,

            messages=[
                {
                    "role": "system",
                    "content": instructions
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        )

        result = (
            response
            .choices[0]
            .message
            .content
        )

        if not result:
            return "الموديل رجع رد فاضي 😅"

        return result

    except Exception as error:

        print(
            "\n========== PERLA BRAIN ERROR =========="
        )

        print(repr(error))

        print(
            "========================================\n"
        )

        return (
            "حصل خطأ في العقل 😕\n\n"
            "بص على CMD عشان نعرف السبب الحقيقي."
        )
'''


write_file(
    ROOT / "brain.py",
    brain
)


# =========================================================
# MAIN SERVER
# =========================================================

main = r'''
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
import traceback

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
    title="Perla",
    version="1.0"
)


memory = load_memory()
history = load_history()


UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


if not history:

    active_chat = create_chat(
        history,
        "محادثة جديدة"
    )

else:

    active_chat = history[0]


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


class Message(BaseModel):
    message: str


class MemoryItem(BaseModel):
    item: str


@app.get("/")
def home():
    return FileResponse(
        "web/index.html"
    )


@app.get("/health")
def health():

    return {
        "status": "ok",
        "perla": "ready",
        "chat_id": active_chat.get("id")
    }


@app.get("/current-chat")
def current_chat():

    return {
        "chat": active_chat
    }


@app.get("/chats")
def get_chats():

    return {
        "chats": [
            {
                "id": chat.get("id"),
                "title": chat.get(
                    "title",
                    "محادثة جديدة"
                )
            }
            for chat in history
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

    return {
        "chat": active_chat
    }


@app.delete("/chats/{chat_id}")
def remove_chat_route(chat_id: str):

    global active_chat

    if len(history) <= 1:

        active_chat = history[0]

        active_chat["messages"] = []

        active_chat["title"] = "محادثة جديدة"

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


@app.post("/chat")
def chat(data: Message):

    message = data.message.strip()

    if not message:

        return {
            "response": "قولّي حاجة يا أحمد 😄",
            "chat_id": active_chat.get("id")
        }

    if not active_chat.get("messages"):

        title = (
            message
            .replace("\n", " ")
            .strip()
        )

        if len(title) > 35:
            title = title[:35] + "..."

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

    save_memory(memory)
    save_history(history)

    return {
        "response": response,
        "chat_id": active_chat.get("id")
    }


@app.post("/chat/multimodal")
async def multimodal_chat(

    message: str = Form(""),

    file: UploadFile | None = File(None)

):

    message = message.strip()

    if not message and file is None:

        return {
            "response":
                "ابعتلي رسالة أو صورة 😄",

            "chat_id":
                active_chat.get("id")
        }


    file_info = None


    if file is not None:

        content_type = (
            file.content_type or ""
        )

        if not content_type.startswith(
            "image/"
        ):

            return {
                "response":
                    "بيرلا بتدعم الصور فقط حاليًا 🖼️",

                "chat_id":
                    active_chat.get("id")
            }


        extension = os.path.splitext(
            file.filename or ""
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


    combined_message = message


    if file_info:

        combined_message += (
            "\n\n[تم إرفاق صورة]"
        )


    if not active_chat.get("messages"):

        title = (
            message
            or
            file_info["original_name"]
        )

        title = (
            title
            .replace("\n", " ")
            .strip()
        )

        if len(title) > 35:
            title = title[:35] + "..."

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

        "response":
            response,

        "chat_id":
            active_chat.get("id"),

        "file":
            file_info
    }


@app.get("/memory")
def get_memory():

    return {
        "memory": memory
    }


@app.post("/memory")
def create_memory(data: MemoryItem):

    item = data.item.strip()

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
def delete_memory(data: MemoryItem):

    item = data.item.strip()

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


@app.exception_handler(Exception)
async def global_error_handler(
    request,
    exc
):

    print(
        "\n========== PERLA SERVER ERROR =========="
    )

    traceback.print_exc()

    print(
        "========================================\n"
    )

    return {
        "error": True,
        "message":
            "حصل خطأ في بيرلا. راجع CMD لمعرفة السبب."
    }
'''


write_file(
    ROOT / "main.py",
    main
)


# =========================================================
# ENV EXAMPLE
# =========================================================

env_example = r'''
OPENROUTER_API_KEY=ضع_مفتاح_OpenRouter_هنا

OPENROUTER_MODEL=openai/gpt-4o

# يمكنك رفع الرقم بعد شحن الرصيد
PERLA_MAX_TOKENS=4096

# مفتاح OpenAI للصوت لاحقًا
OPENAI_API_KEY=ضع_مفتاح_OpenAI_هنا
'''


if not (ROOT / ".env.example").exists():

    write_file(
        ROOT / ".env.example",
        env_example
    )


# =========================================================
# DONE
# =========================================================

print()
print("=" * 55)
print("PERLA v1 FILE SETUP COMPLETE")
print("=" * 55)
print()
print("تم تحديث:")
print("- brain.py")
print("- main.py")
print()
print("تم الحفاظ على:")
print("- config.py")
print("- memory.py")
print("- chat_history.py")
print("- modalities/")
print("- uploads/")
print()
print("Backup موجود في:")
print("backup_before_perla_v1")
print()
print("الخطوة التالية:")
print("شغل السيرفر واختبر /health")
print("=" * 55)