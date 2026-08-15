import os
import base64

from dotenv import load_dotenv
from openai import OpenAI

from config import PERSONALITY


load_dotenv()


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

OPENROUTER_MODEL = "openai/gpt-4o"

MAX_TOKENS = 2000


# =========================================
# API KEY
# =========================================

def get_api_key():

    return os.getenv(
        "OPENROUTER_API_KEY"
    )


# =========================================
# CONTEXT
# =========================================

def build_context(
    memory,
    history
):

    memory_text = "\n".join(

        f"- {item}"

        for item in memory

    ) if memory else (
        "لا توجد معلومات محفوظة حتى الآن."
    )


    history_lines = []


    for item in history[-20:]:

        role = item.get(
            "role",
            "user"
        )

        content = item.get(
            "content",
            ""
        )


        if item.get("image"):

            content += (
                " [هذه الرسالة تحتوي على صورة مرفقة]"
            )


        history_lines.append(

            f"{role}: {content}"

        )


    history_text = "\n".join(

        history_lines

    ) if history_lines else (
        "لا توجد محادثة سابقة."
    )


    return f"""
{PERSONALITY}

الذاكرة الحالية لأحمد:
{memory_text}

المحادثة الحالية:
{history_text}

تعليمات:
- استخدمي الذاكرة عندما تكون مفيدة.
- لا تختلقي معلومات.
- لا تدّعي تنفيذ شيء لم يتم تنفيذه.
- كوني طبيعية في العربية المصرية.
- إذا أرسل أحمد صورة، حللي الصورة فعليًا.
- إذا أرسل أحمد صورة في رسالة سابقة ثم سأل عنها لاحقًا، استخدمي الصورة إذا تم توفيرها لك.
- لا تفترضي محتوى صورة لم ترَيها.
"""


# =========================================
# IMAGE
# =========================================

def image_to_data_url(
    image_path,
    content_type
):

    with open(
        image_path,
        "rb"
    ) as image_file:

        encoded = base64.b64encode(
            image_file.read()
        ).decode("utf-8")


    return (
        f"data:{content_type};base64,"
        f"{encoded}"
    )


# =========================================
# FIND IMAGE
# =========================================

def find_last_image(history):

    for item in reversed(history):

        image = item.get(
            "image"
        )


        if not image:

            continue


        path = image.get(
            "path"
        )


        if not path:

            continue


        if not os.path.exists(path):

            continue


        return {

            "path":
                path,

            "content_type":
                image.get(
                    "content_type",
                    "image/jpeg"
                )
        }


    return None


# =========================================
# IMAGE REQUEST DETECTION
# =========================================

def wants_previous_image(
    message
):

    if not message:

        return False


    words = [

        "الصورة",
        "صورة",
        "الصوره",
        "صوره",

        "فاكر الصورة",
        "فاكرة الصورة",

        "الصورة اللي",
        "الصورة دي",
        "الصورة دى",

        "اللي بعتها",
        "اللى بعتها",

        "بعتها قبل",
        "بعتها لك",
        "بعتهالك",

        "في الصورة",
        "فى الصورة",

        "موجود في الصورة",
        "موجودة في الصورة",

        "شايف الصورة",
        "شوف الصورة",

        "حلل الصورة",
        "حللي الصورة",

        "احلل الصورة",

        "وصف الصورة",
        "اوصف الصورة"
    ]


    message = message.lower()


    return any(
        word in message
        for word in words
    )


# =========================================
# THINK
# =========================================

def think(
    message,
    memory,
    history=None,
    image_path=None,
    image_content_type=None
):

    message = (
        message or ""
    ).strip()


    history = history or []


    if (
        not message
        and not image_path
    ):

        return (
            "قولّي حاجة يا أحمد 😄"
        )


    api_key = get_api_key()


    if not api_key:

        return (
            "مفتاح OpenRouter مش متوصل."
        )


    try:

        client = OpenAI(

            api_key=api_key,

            base_url=
                OPENROUTER_BASE_URL
        )


        instructions = build_context(
            memory,
            history
        )


        # =====================================
        # DETERMINE IMAGE
        # =====================================

        image_info = None


        # صورة جديدة
        if image_path:

            image_info = {

                "path":
                    image_path,

                "content_type":
                    image_content_type
                    or "image/jpeg"
            }


        # صورة سابقة
        elif wants_previous_image(
            message
        ):

            image_info = find_last_image(
                history
            )


        # =====================================
        # TEXT ONLY
        # =====================================

        if not image_info:

            response = client.chat.completions.create(

                model=
                    OPENROUTER_MODEL,

                max_tokens=
                    MAX_TOKENS,

                messages=[

                    {
                        "role":
                            "system",

                        "content":
                            instructions
                    },

                    {
                        "role":
                            "user",

                        "content":
                            message
                    }
                ]
            )


        # =====================================
        # WITH IMAGE
        # =====================================

        else:

            image_url = image_to_data_url(

                image_info["path"],

                image_info[
                    "content_type"
                ]
            )


            user_content = []


            user_content.append({

                "type":
                    "text",

                "text":
                    message
                    or
                    "حللي الصورة دي."
            })


            user_content.append({

                "type":
                    "image_url",

                "image_url": {

                    "url":
                        image_url
                }
            })


            response = client.chat.completions.create(

                model=
                    OPENROUTER_MODEL,

                max_tokens=
                    MAX_TOKENS,

                messages=[

                    {
                        "role":
                            "system",

                        "content":
                            instructions
                    },

                    {
                        "role":
                            "user",

                        "content":
                            user_content
                    }
                ]
            )


        # =====================================
        # RESULT
        # =====================================

        result = (
            response
            .choices[0]
            .message
            .content
        )


        if not result:

            return (
                "الموديل رجع رد فاضي 😅"
            )


        return result


    except Exception as error:

        print(
            "OPENROUTER ERROR:",
            repr(error)
        )


        return (
            "حصلت مشكلة في الاتصال بالعقل الحقيقي 😕"
        )