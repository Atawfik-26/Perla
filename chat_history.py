import json
import os
import uuid
from datetime import datetime


HISTORY_FILE = "chat_history.json"

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

    chat["updated_at"] = datetime.now().isoformat()


def touch_chat(history, chat_id):

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
# CROSS-CHAT CONTEXT SEARCH (جديد)
# =========================================================
#
# الفكرة: لما أحمد يبعت رسالة، بندور في كل المحادثات
# القديمة (غير المحادثة الحالية) عن رسائل فيها كلمات
# مشتركة مع سؤاله الحالي، وبنرجع أهمهم كـ"سياق محتمل
# يفيد الرد" - ده بيحل مشكلة إن بيرلا كانت مش بتربط
# بين كلام امبارح وكلام النهاردة لو مكنش في محادثة واحدة.
#
# ملحوظة: ده بحث بسيط بالكلمات المشتركة (keyword overlap)،
# مش بحث ذكي بالمعنى (semantic search) - يعني ممكن يفوّت
# روابط مش فيها كلمات متطابقة حرفيًا، لكنه بداية كويسة
# ومفيهاش تكلفة إضافية (مفيش استدعاء API زيادة).
# =========================================================

_STOPWORDS = {
    "في", "من", "على", "الى", "إلى", "عن", "مع", "أو", "او",
    "أن", "ان", "إن", "هو", "هي", "أنا", "انا", "إنت", "انت",
    "انتِ", "إنتي", "انتي", "ده", "دي", "دة", "هذا", "هذه",
    "كده", "كدا", "بس", "يا", "ايه", "إيه", "أنتِ", "زي",
    "لو", "علشان", "عشان", "وهو", "وهي", "كان", "كانت",
    "يكون", "بقى", "بقا", "the", "and", "for", "with", "you",
    "your", "this", "that", "have", "what", "how",
}


def _tokenize(text):

    text = (text or "").lower()

    words = re.findall(
        r"[a-zA-Z\u0600-\u06FF]{3,}",
        text
    )

    return [
        w for w in words
        if w not in _STOPWORDS
    ]


def search_related_context(
    history,
    query,
    current_chat_id=None,
    max_snippets=3,
    snippet_max_chars=280
):
    """
    بتدور في كل المحادثات القديمة (غير المحادثة الحالية)
    عن أعلى الرسائل تطابقًا مع الكلمات المهمة في query،
    وبترجع أفضل النتائج كقايمة dicts:
    [{"chat_title": ..., "snippet": ...}, ...]

    لو مفيش تطابق كافي، بترجع قايمة فاضية - ومتأثرش على
    باقي الرد، بيرلا هترد عادي من غير السياق الإضافي ده.
    """

    query_words = set(_tokenize(query))

    if not query_words:
        return []

    scored = []

    for chat in history:

        if chat.get("id") == current_chat_id:
            continue

        chat_title = chat.get(
            "title",
            "محادثة قديمة"
        )

        for message in chat.get("messages", []):

            content = message.get("content", "")

            if not content or len(content) < 15:
                continue

            message_words = set(_tokenize(content))

            overlap = query_words & message_words

            if len(overlap) < 2:
                continue

            score = len(overlap)

            snippet = content.strip()

            if len(snippet) > snippet_max_chars:

                snippet = snippet[:snippet_max_chars] + "..."

            scored.append({

                "score": score,

                "chat_title": chat_title,

                "snippet": snippet

            })

    if not scored:
        return []

    scored.sort(

        key=lambda item: item["score"],

        reverse=True

    )

    # منع تكرار نفس المحادثة أكتر من مرة في النتايج
    # عشان نديله تنوع بدل ما ناخد 3 جمل من نفس المحادثة

    seen_chats = set()

    results = []

    for item in scored:

        if item["chat_title"] in seen_chats:
            continue

        seen_chats.add(item["chat_title"])

        results.append({

            "chat_title": item["chat_title"],

            "snippet": item["snippet"]

        })

        if len(results) >= max_snippets:
            break

    return results


import re  # noqa: E402 (لازم يكون فوق فعليًا - شايله هنا لسهولة اللصق، بايثون هيقبله برضه)
