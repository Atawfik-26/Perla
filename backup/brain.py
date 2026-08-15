import os
from dotenv import load_dotenv
from openai import OpenAI

from config import PERSONALITY


load_dotenv()


def get_api_key():
    return os.getenv("OPENAI_API_KEY")


def build_context(memory, history):

    memory_text = ""

    if memory:
        memory_text = "\n".join(
            f"- {item}"
            for item in memory
        )

    history_text = ""

    if history:
        recent_history = history[-20:]

        history_text = "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}"
            for item in recent_history
        )

    return f"""
أنتِ بيرلا، المساعدة الشخصية الخاصة بتيتو.

الشخصية والتعليمات:
{PERSONALITY}

معلومات محفوظة عن تيتو:
{memory_text}

المحادثة السابقة:
{history_text}

استخدمي المعلومات السابقة عندما تكون مفيدة.
لا تذكري أنكِ تقرئين ملف ذاكرة أو تاريخ محادثات.
لا تختلقي معلومات غير موجودة.
"""


def think(message, memory, history=None):

    text = message.strip()

    if not text:
        return "قولّي حاجة يا تيتو 😄"

    api_key = get_api_key()

    # لو مفيش API Key، نفضل في الوضع التجريبي
    if not api_key:
        return "العقل التجريبي استلم: " + text

    try:

        client = OpenAI(
            api_key=api_key
        )

        context = build_context(
            memory,
            history or []
        )

        response = client.responses.create(

            model="MODEL_NAME",

            instructions=context,

            input=text

        )

        return response.output_text

    except Exception as error:

        print("AI ERROR:", error)

        return "حصلت مشكلة في الاتصال بالعقل الحقيقي."