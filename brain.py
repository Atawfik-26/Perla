import os
import base64
import mimetypes
import json
import traceback

from dotenv import load_dotenv
from openai import OpenAI

from config import PERSONALITY
from router import router
from model_selector import get_model_candidates
from memory import add_memory, get_relevant_memories
from chat_history import search_related_context
from tools import TOOLS_SCHEMA, execute_tool


load_dotenv()


# =========================================================
# CONFIG
# =========================================================

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MAX_TOKENS = int(
    os.getenv(
        "PERLA_MAX_TOKENS",
        "3000"
    )
)

MEMORY_CHECK_MODEL = os.getenv(
    "PERLA_MEMORY_MODEL",
    "openai/gpt-4o-mini"
)

MAX_TOOL_ITERATIONS = 5


# =========================================================
# API
# =========================================================

def get_api_key():
    return os.getenv("OPENROUTER_API_KEY")


# =========================================================
# CONTEXT
# =========================================================

def build_context(memory, history, message="", history_obj=None):
    """
    بيبني الـsystem prompt الكامل.
    """

    # --- الذاكرة المرتبطة بالموضوع (مش الكل) ---
    relevant = get_relevant_memories(memory, message, limit=40)

    memory_text = (
        "\n".join(f"- {item}" for item in relevant)
        if relevant
        else "لا توجد معلومات محفوظة حتى الآن."
    )

    # --- سياق من محادثات قديمة ---
    related_chats = []
    if history_obj and message:
        try:
            related = search_related_context(
                history_obj,
                message,
                limit=2,
                snippet_chars=150
            )
            if related:
                related_chats = [
                    f"من \"{r['title']}\": {r['snippet']}"
                    for r in related
                ]
        except Exception:
            pass

    related_text = (
        "\n".join(related_chats)
        if related_chats
        else ""
    )

    # --- تاريخ المحادثة الحالي ---
    history_text = (
        "\n".join(
            f"{item.get('role', 'user')}: "
            f"{item.get('content', '')}"
            for item in (history or [])[-20:]
        )
        if history
        else "لا توجد محادثة سابقة."
    )

    context_parts = [PERSONALITY]

    context_parts.append(f"""
الذاكرة الحالية لأحمد (الأكثر صلة بالموضوع):
{memory_text}
""")

    if related_text:
        context_parts.append(f"""
محادثات سابقة قد تكون ذات صلة:
{related_text}
""")

    context_parts.append(f"""
المحادثة الحالية:
{history_text}

تعليمات بيرلا:
- أنتِ بيرلا.
- تحدثي بالعربية المصرية الطبيعية.
- استخدمي الذاكرة عندما تكون مفيدة.
- لا تختلقي معلومات.
- لا تدّعي تنفيذ شيء لم يتم تنفيذه.
- إذا أُرسلت صورة، حللي محتوى الصورة فعليًا.
- إذا أُرسل صوت، تعاملِي معه فعليًا إذا كان الموديل يدعمه.
- إذا أُرسل فيديو، حلليه فعليًا إذا كان الموديل يدعمه.
- عندك أدوات فعلية: read_file (قراءة ملف) و fetch_url (فتح رابط).
  لو أحمد طلب منك تقرأي ملف أو تفتحي لينك، استخدمي الأداة فعليًا.
- كوني طبيعية وودودة.
- لا تطولي بدون داعٍ.
""")

    return "\n".join(context_parts)


# =========================================================
# FILE → DATA URL
# =========================================================

def file_to_data_url(path, content_type=None):

    if not content_type:
        content_type, _ = mimetypes.guess_type(path)

    content_type = content_type or "application/octet-stream"

    with open(path, "rb") as file:
        encoded = base64.b64encode(file.read()).decode("utf-8")

    return f"data:{content_type};base64,{encoded}"


# =========================================================
# MODEL ROUTING
# =========================================================

def choose_models(
    message,
    image_path=None,
    audio_path=None,
    video_path=None,
    task_type=None
):
    """
    بيختار الموديل المناسب للمهمة.
    لو task_type جاهز من بره (من server.py)، مبنحسبش تاني.
    """

    if task_type is None:
        task_type = router.choose(
            message=message,
            has_image=bool(image_path),
            has_audio=bool(audio_path),
            has_video=bool(video_path)
        )

    candidates = get_model_candidates(task_type)

    print("\n========== PERLA ROUTING ==========")
    print(f"[PERLA TASK]       {task_type}")
    print(f"[PERLA CANDIDATES] {candidates}")
    print("===================================\n")

    return task_type, candidates


# =========================================================
# BUILD USER CONTENT
# =========================================================

def build_user_content(
    message,
    image_path=None,
    image_content_type=None,
    audio_path=None,
    audio_content_type=None,
    video_path=None,
    video_content_type=None
):

    if not image_path and not audio_path and not video_path:
        return message

    # --- IMAGE ---
    if image_path:
        image_url = file_to_data_url(image_path, image_content_type)
        return [
            {
                "type": "text",
                "text": message or "حللي الصورة دي ووصفيلي اللي فيها."
            },
            {
                "type": "image_url",
                "image_url": {"url": image_url}
            }
        ]

    # --- AUDIO ---
    if audio_path:
        audio_url = file_to_data_url(audio_path, audio_content_type)
        audio_format = "wav"
        return [
            {
                "type": "text",
                "text": message or "حللي التسجيل الصوتي ده."
            },
            {
                "type": "input_audio",
                "input_audio": {
                    "data": audio_url,
                    "format": audio_format
                }
            }
        ]

    # --- VIDEO ---
    if video_path:
        return [
            {
                "type": "text",
                "text": (
                    message
                    or "حللي الفيديو ده."
                    + "\n[ملحوظة: الفيديو متاح على السيرفر بس "
                    + "مش كل الموديلات بتقدر تحلله مباشرة.]"
                )
            }
        ]

    return message


# =========================================================
# SINGLE MODEL REQUEST
# =========================================================

def send_request(
    client,
    model,
    instructions,
    user_content,
    enable_tools=True
):
    """
    بيبعت request للموديل.
    enable_tools=False للـplanner عشان ميستخدمش أدوات غير لازمة.
    """

    print(f"[PERLA] Sending request using {model}")

    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": user_content}
    ]

    kwargs = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "messages": messages,
    }

    if enable_tools:
        kwargs["tools"] = TOOLS_SCHEMA

    for iteration in range(MAX_TOOL_ITERATIONS):

        response = client.chat.completions.create(**kwargs)

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)

        if not tool_calls:
            result = message.content
            if not result:
                raise RuntimeError("Model returned empty response")
            return result

        print(
            f"[PERLA TOOLS] الموديل طلب {len(tool_calls)} أداة/أدوات "
            f"(محاولة {iteration + 1})"
        )

        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments
                    }
                }
                for call in tool_calls
            ]
        })

        for call in tool_calls:
            print(
                f"[PERLA TOOLS] بتنفذ: {call.function.name}"
                f"({call.function.arguments})"
            )
            tool_result = execute_tool(
                call.function.name,
                call.function.arguments
            )
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": tool_result
            })

    raise RuntimeError(
        "Perla used tools too many times without a final answer"
    )


# =========================================================
# REQUEST WITH FALLBACK
# =========================================================

def send_request_with_fallback(
    client,
    candidates,
    instructions,
    user_content,
    enable_tools=True
):

    last_error = None

    for model in candidates:
        try:
            result = send_request(
                client, model, instructions, user_content,
                enable_tools=enable_tools
            )
            print(f"[PERLA MODEL USED] {model}")
            return result, model
        except Exception as error:
            last_error = error
            print(f"[PERLA FALLBACK] {model} فشل: {repr(error)}")
            print("[PERLA FALLBACK] بجرب الموديل اللي بعده...\n")
            continue

    raise last_error or RuntimeError("All candidate models failed")


# =========================================================
# AUTOMATIC MEMORY EXTRACTION
# =========================================================

MEMORY_EXTRACTION_PROMPT = """أنت أداة استخراج معلومات فقط.
اقرأ رسالة المستخدم التالية وحدد: هل فيها معلومة شخصية دائمة
تستاهل تُحفظ في ذاكرة مساعد شخصي؟ (مثل: اسم، مهنة، تفضيل،
معلومة عن شخص مهم في حياته، حدث مهم، عادة، هدف طويل المدى).

تجاهل: كلام عابر، أسئلة عادية، طلبات مؤقتة، حاجات مش هتفرق
بعد شوية.

رد بصيغة JSON فقط، من غير أي شرح أو تنسيق إضافي:
{"memories": ["جملة قصيرة وواضحة", "..."]}

لو مفيش حاجة تستاهل الحفظ:
{"memories": []}

رسالة المستخدم:
"""


def extract_memories(client, message, memory_list):
    """
    بترجع True لو ضافت حاجة جديدة للذاكرة.
    """

    if not message:
        return False

    try:
        response = client.chat.completions.create(
            model=MEMORY_CHECK_MODEL,
            max_tokens=300,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "أنت أداة استخراج JSON فقط. "
                        "لا تكتبي أي كلام غير الـJSON نفسه."
                    )
                },
                {
                    "role": "user",
                    "content": MEMORY_EXTRACTION_PROMPT + message
                }
            ]
        )

        raw = (
            response.choices[0].message.content or ""
        ).strip()

        if raw.startswith("```"):
            raw = raw.strip("`").replace("json", "", 1).strip()

        data = json.loads(raw)
        new_items = data.get("memories", [])

        added_any = False
        for item in new_items:
            item = str(item).strip()
            if not item:
                continue
            if add_memory(memory_list, item):
                added_any = True
                print(f"[PERLA MEMORY] اتضاف تلقائيًا: {item}")

        return added_any

    except Exception as error:
        print(f"[PERLA MEMORY] فشل استخراج الذاكرة: {repr(error)}")
        return False


# =========================================================
# THINK
# =========================================================

def think(
    message,
    memory,
    history=None,
    history_obj=None,
    image_path=None,
    image_content_type=None,
    audio_path=None,
    audio_content_type=None,
    video_path=None,
    video_content_type=None,
    task_type=None
):

    message = (message or "").strip()

    if (
        not message
        and not image_path
        and not audio_path
        and not video_path
    ):
        return "قولّي حاجة يا أحمد 😄"

    api_key = get_api_key()
    if not api_key:
        return "مفتاح OpenRouter مش موجود في ملف .env."

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL
        )

        instructions = build_context(
            memory or [],
            history or [],
            message,
            history_obj
        )

        task_type, candidates = choose_models(
            message,
            image_path=image_path,
            audio_path=audio_path,
            video_path=video_path,
            task_type=task_type
        )

        user_content = build_user_content(
            message,
            image_path=image_path,
            image_content_type=image_content_type,
            audio_path=audio_path,
            audio_content_type=audio_content_type,
            video_path=video_path,
            video_content_type=video_content_type
        )

        result, used_model = send_request_with_fallback(
            client,
            candidates,
            instructions,
            user_content,
            enable_tools=True
        )

        if message:
            extract_memories(client, message, memory)

        return result

    except Exception as error:
        print("\n========== PERLA BRAIN ERROR ==========")
        print(repr(error))
        print("========================================\n")
        return (
            "حصل خطأ في عقل بيرلا 😕\n\n"
            "بص على CMD عشان نعرف السبب."
        )