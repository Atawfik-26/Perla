import json
import os
import re
import uuid
from datetime import datetime


HISTORY_FILE = "chat_history.json"

# أقصى عدد محادثات محفوظة. لو اتعدى، أقدم محادثة (اللي محدش
# فتحها أو اتكلم فيها من زمان) بتتشال تلقائيًا عشان الملف
# متكبرش أوي ويبطئ تحميل بيرلا مع الوقت.
MAX_CHATS = 100


# =========================================================
# LOAD / SAVE
# =========================================================

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


def _enforce_max_size(history):
    """
    لو عدد المحادثات زاد عن الحد الأقصى، نشيل أقدم محادثة
    (حسب آخر تعديل عليها) عشان نفضي مكان للجديد.
    """

    while len(history) > MAX_CHATS:

        oldest_index = min(
            range(len(history)),
            key=lambda i: history[i].get(
                "updated_at",
                history[i].get("created_at", "")
            )
        )

        history.pop(oldest_index)


# =========================================================
# CREATE
# =========================================================

def create_chat(
    history,
    title="محادثة جديدة"
):

    now = datetime.now().isoformat()

    chat = {

        "id": str(uuid.uuid4()),

        "title": title,

        "created_at": now,

        "updated_at": now,

        "messages": []
    }

    history.insert(
        0,
        chat
    )

    _enforce_max_size(history)

    save_history(history)

    return chat


# =========================================================
# MESSAGES
# =========================================================

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

    # كل ما يتضاف رسالة، المحادثة دي بقت "الأحدث نشاطًا"
    chat["updated_at"] = datetime.now().isoformat()


def touch_chat(history, chat_id):
    """
    بتنقل المحادثة اللي اتفتحت أو اتكلم فيها لأول القايمة،
    زي أي تطبيق شات عادي (آخر حاجة اتكلمت فيها تطلع فوق).
    """

    for index, chat in enumerate(history):

        if chat.get("id") == chat_id:

            chat["updated_at"] = datetime.now().isoformat()

            history.insert(
                0,
                history.pop(index)
            )

            return chat

    return None


# =========================================================
# READ
# =========================================================

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


# =========================================================
# DELETE
# =========================================================

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


# =========================================================
# CROSS-CHAT CONTEXT SEARCH (الربط بين السياقات)
# =========================================================
#
# بيرلا كانت بس بتشوف المحادثة المفتوحة دلوقتي. الدالة دي
# بتدور جوه كل المحادثات التانية عن رسايل المستخدم اللي فيها
# كلمات مشتركة مع الرسالة الحالية، وبترجع أفضل النتايج عشان
# تتحط كـ"سياق محتمل الصلة" في البرومبت - يعني بيرلا تقدر
# تستفيد من حاجة اتقالت في محادثة قديمة، مش بس اللي قدامها.
# =========================================================

def _tokenize(text):

    if not text:
        return set()

    words = re.findall(
        r"[\w\u0600-\u06FF]+",
        text.lower()
    )

    return {w for w in words if len(w) > 1}


def search_related_context(
    history,
    query,
    exclude_chat_id=None,
    limit=3,
    snippet_chars=180
):

    query = (query or "").strip()

    if not query:
        return []

    query_words = _tokenize(query)

    if not query_words:
        return []

    candidates = []

    for chat in history:

        if chat.get("id") == exclude_chat_id:
            continue

        title = chat.get("title", "محادثة سابقة")

        for msg in chat.get("messages", []):

            if msg.get("role") != "user":
                continue

            content = (msg.get("content") or "").strip()

            if not content:
                continue

            overlap = len(
                query_words & _tokenize(content)
            )

            # لازم كلمتين مشتركتين على الأقل عشان نتجنب
            # تطابقات عشوائية (زي كلمة شايعة واحدة بس)
            if overlap >= 2:

                snippet = content

                if len(snippet) > snippet_chars:

                    snippet = snippet[:snippet_chars] + "..."

                candidates.append(
                    (overlap, title, snippet)
                )

    candidates.sort(
        key=lambda c: c[0],
        reverse=True
    )

    seen = set()
    results = []

    for overlap, title, snippet in candidates:

        key = (title, snippet)

        if key in seen:
            continue

        seen.add(key)

        results.append({
            "title": title,
            "snippet": snippet
        })

        if len(results) >= limit:
            break

    return results