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
- إذا أُرسلت صورة، حللي
