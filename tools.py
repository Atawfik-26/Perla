import os
import re
import json

import requests


# =========================================================
# PERLA TOOLS — قدرات تنفيذ عملي حقيقية
# =========================================================
#
# الفكرة: بدل ما بيرلا تقول "مش قادرة أقرا ملفات أو أفتح
# لينكات"، بقى عندها أدوات فعلية تقدر تستخدمها. الموديل هو
# اللي بيقرر لوحده إمتى يستخدم أداة، إحنا بس بنوفرها له
# وبننفذها لما يطلبها (tool calling / function calling).
#
# أمان مهم:
# - read_file مسموح ليها بس تقرا من جوه مجلدات محددة
#   (uploads و files) عشان محدش يقدر يخليها تقرا ملفات
#   حساسة على الجهاز (زي .env مثلاً).
# - fetch_url بتجيب نص الصفحة بس (من غير سكريبتات)، وبتحدد
#   حجم أقصى عشان متطولش أو تجيب حاجة ضخمة أوي.
# =========================================================


ALLOWED_READ_DIRS = ["uploads", "files"]

MAX_FILE_CHARS = 8000
MAX_FETCH_CHARS = 8000

REQUEST_TIMEOUT_SECONDS = 10


# =========================================================
# READ FILE
# =========================================================

def _is_path_allowed(path):
    """
    بترجع True بس لو المسار جوه واحد من المجلدات المسموحة،
    ومفيهوش محاولة خروج زي "../" عشان توصل لمكان تاني.
    """

    normalized = os.path.normpath(path)

    if os.path.isabs(normalized):
        return False

    if normalized.startswith(".."):
        return False

    top_level = normalized.split(os.sep)[0]

    return top_level in ALLOWED_READ_DIRS


def read_file(path):

    path = (path or "").strip()

    if not path:
        return "محتاجة اسم أو مسار الملف عشان أقراه."

    if not _is_path_allowed(path):

        return (
            "معلش، بيرلا بس بتقدر تقرا ملفات جوه مجلدات "
            "uploads أو files، مش أي مكان تاني على الجهاز."
        )

    if not os.path.exists(path):

        return f"مفيش ملف بالاسم ده: {path}"

    if not os.path.isfile(path):

        return f"المسار ده مش ملف: {path}"

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            content = file.read(MAX_FILE_CHARS + 1)

        if len(content) > MAX_FILE_CHARS:

            content = (
                content[:MAX_FILE_CHARS]
                + "\n...[الملف طويل، اتقطع هنا]"
            )

        if not content.strip():

            return "الملف موجود بس فاضي أو مش نص قابل للقراءة."

        return content

    except Exception as error:

        return f"حصل خطأ وأنا بقرا الملف: {repr(error)}"


# =========================================================
# FETCH URL
# =========================================================

def fetch_url(url):

    url = (url or "").strip()

    if not url:
        return "محتاجة الرابط عشان أفتحه."

    if not re.match(r"^https?://", url, re.IGNORECASE):

        return "الرابط لازم يبدأ بـ http:// أو https://"

    try:

        response = requests.get(

            url,

            timeout=REQUEST_TIMEOUT_SECONDS,

            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; PerlaBot/1.0)"
                )
            }

        )

        response.raise_for_status()

        html = response.text

        # شيل السكريبتات والستايلات الأول عشان متبقاش جوه النص
        html = re.sub(
            r"<script.*?</script>",
            " ",
            html,
            flags=re.S | re.I
        )

        html = re.sub(
            r"<style.*?</style>",
            " ",
            html,
            flags=re.S | re.I
        )

        # شيل أي تاج HTML وسيب النص بس
        text = re.sub(r"<[^>]+>", " ", html)

        text = re.sub(r"\s+", " ", text).strip()

        if not text:

            return "فتحت الرابط بس مالقتش نص واضح جواه."

        if len(text) > MAX_FETCH_CHARS:

            text = (
                text[:MAX_FETCH_CHARS]
                + "...[المحتوى طويل، اتقطع هنا]"
            )

        return text

    except requests.exceptions.Timeout:

        return "الرابط استغرق وقت طويل ومفتحش."

    except requests.exceptions.RequestException as error:

        return f"معرفتش أفتح الرابط: {repr(error)}"

    except Exception as error:

        return f"حصل خطأ وأنا بفتح الرابط: {repr(error)}"


# =========================================================
# TOOL SCHEMA (بيتبعت للموديل عشان يعرف الأدوات المتاحة)
# =========================================================

TOOLS_SCHEMA = [

    {
        "type": "function",

        "function": {

            "name": "read_file",

            "description": (
                "اقرأ محتوى ملف نصي محفوظ فعليًا على سيرفر بيرلا "
                "(زي ملف رفعه أحمد في مجلد uploads أو files). "
                "استخدمي الأداة دي فعليًا لما أحمد يطلب منك تقرأي "
                "أو تلخصي ملف موجود، بدل ما تقوليله إنك مش قادرة."
            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "path": {

                        "type": "string",

                        "description": (
                            "مسار الملف، مثلا uploads/report.txt "
                            "أو files/notes.txt"
                        )

                    }

                },

                "required": ["path"]

            }

        }

    },

    {
        "type": "function",

        "function": {

            "name": "fetch_url",

            "description": (
                "افتحي رابط إنترنت فعليًا وارجعي النص الموجود "
                "في الصفحة. استخدمي الأداة دي لما أحمد يبعتلك "
                "لينك ويطلب منك تقرأيه أو تلخصيه أو تجيبي منه "
                "معلومة، بدل ما تقوليله إنك مش قادرة تفتحي روابط."
            ),

            "parameters": {

                "type": "object",

                "properties": {

                    "url": {

                        "type": "string",

                        "description": (
                            "الرابط الكامل، لازم يبدأ بـ "
                            "http:// أو https://"
                        )

                    }

                },

                "required": ["url"]

            }

        }

    }

]


# =========================================================
# EXECUTE TOOL BY NAME
# =========================================================

def execute_tool(name, arguments_json):
    """
    بتاخد اسم الأداة والـarguments (كـJSON string جاي من
    الموديل) وبتنفذ الأداة المناسبة، وبترجع نتيجة نصية دايمًا
    (حتى لو فشلت) عشان الموديل يقدر يكمل ويرد على أحمد.
    """

    try:

        args = (
            json.loads(arguments_json)
            if arguments_json
            else {}
        )

    except Exception:

        args = {}

    if name == "read_file":

        return read_file(
            args.get("path", "")
        )

    if name == "fetch_url":

        return fetch_url(
            args.get("url", "")
        )

    return f"أداة غير معروفة: {name}"