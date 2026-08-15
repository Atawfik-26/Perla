import json
import os
import re
import uuid
from datetime import datetime, date


MEMORY_FILE = "memory.json"

# أقصى عدد عناصر في الذاكرة. لو اتعدى، أقدم عنصر (مش reminder)
# بيتشال تلقائيًا عشان الذاكرة متتقلش وتبطئ الردود.
MAX_MEMORY_ITEMS = 300


# =========================================================
# LOAD / SAVE
# =========================================================

def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return []

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if not isinstance(data, list):
                return []

            # توافق مع الذاكرة القديمة (قايمة نصوص بسيطة)
            # بنحولها تلقائيًا للشكل الجديد أول ما تتحمل.
            converted = []

            for entry in data:

                if isinstance(entry, str):

                    converted.append(
                        _make_entry(entry)
                    )

                elif isinstance(entry, dict) and "text" in entry:

                    converted.append(entry)

            return converted

    except Exception:

        return []


def save_memory(memory):

    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            memory,
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# HELPERS
# =========================================================

def _normalize(text):
    """
    بتشيل علامات الترقيم والمسافات الزيادة والحالة
    عشان مقارنة التكرار تبقى أذكى (مش بس تطابق حرفي 100%).
    """

    text = text.strip().lower()

    text = re.sub(r"[.,!؟?،؛;]+$", "", text)

    text = re.sub(r"\s+", " ", text)

    return text


def _tokenize(text):
    """
    بتفكك أي نص (عربي أو إنجليزي) لمجموعة كلمات فريدة،
    مستخدمة في حساب التشابه بين الرسالة الحالية وعناصر الذاكرة.
    """

    if not text:
        return set()

    words = re.findall(
        r"[\w\u0600-\u06FF]+",
        text.lower()
    )

    # كلمات قصيرة أوي (حرف أو حرفين) بتضيف ضوضاء أكتر ما تفيد
    return {w for w in words if len(w) > 1}


def _make_entry(
    text,
    category="عام",
    remind_on=None
):

    return {
        "id": str(uuid.uuid4())[:8],
        "text": text.strip(),
        "category": category,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "remind_on": remind_on,  # تاريخ "YYYY-MM-DD" أو None
        "reminded": False,
    }


def _guess_category(text):
    """
    تصنيف تلقائي بسيط بناءً على كلمات مفتاحية.
    ده fallback بس لما محدش حدد تصنيف صراحة (زي لما أحمد
    نفسه يحفظ حاجة يدويًا) - لو الحفظ التلقائي جاي من
    extract_memories في brain.py، الموديل نفسه بيحدد التصنيف
    الأدق وده بيتفضل عليه.
    """

    t = text.lower()

    categories = {
        "شغل": ["عميل", "كلاينت", "شغل", "براند", "كامبين", "حملة", "بوست", "محتوى"],
        "مواعيد": ["ميعاد", "اجتماع", "meeting", "موعد", "تسليم", "ديدلاين", "deadline"],
        "شخصي": ["أنا", "بحب", "بكره", "حاسس", "مزاجي"],
    }

    for category, keywords in categories.items():

        if any(k in t for k in keywords):

            return category

    return "عام"


# =========================================================
# ADD
# =========================================================

def add_memory(
    memory,
    item,
    category=None,
    remind_on=None
):

    item = str(item).strip()

    if not item:
        return False

    normalized_new = _normalize(item)

    # منع التكرار بمقارنة ذكية (بعد تنظيف الترقيم والمسافات)
    for entry in memory:

        if _normalize(entry["text"]) == normalized_new:

            return False

    entry = _make_entry(
        item,
        category=category or _guess_category(item),
        remind_on=remind_on
    )

    memory.append(entry)

    _enforce_max_size(memory)

    save_memory(memory)

    return True


def _enforce_max_size(memory):
    """
    لو الذاكرة كبرت عن الحد الأقصى، نشيل أقدم العناصر
    اللي مش reminders لسه مستنية (عشان متضيعش تذكيرات مهمة).
    """

    if len(memory) <= MAX_MEMORY_ITEMS:
        return

    # رتب حسب الأقدم الأول، بس سيب أي remind_on لسه معلق
    removable = [
        e for e in memory
        if not e.get("remind_on") or e.get("reminded")
    ]

    removable.sort(key=lambda e: e.get("created_at", ""))

    while len(memory) > MAX_MEMORY_ITEMS and removable:

        oldest = removable.pop(0)

        if oldest in memory:
            memory.remove(oldest)


# =========================================================
# REMOVE / CLEAR
# =========================================================

def remove_memory(memory, item):

    normalized_target = _normalize(str(item))

    for entry in memory:

        if _normalize(entry["text"]) == normalized_target:

            memory.remove(entry)

            save_memory(memory)

            return True

    return False


def clear_memory(memory):

    memory.clear()

    save_memory(memory)


def memory_contains(memory, item):

    normalized_target = _normalize(str(item))

    return any(
        _normalize(e["text"]) == normalized_target
        for e in memory
    )


# =========================================================
# READ
# =========================================================

def get_memories(memory):
    """
    بترجع نصوص الذاكرة بس (زي القديم) عشان تتحط في الـcontext
    اللي بيتبعت للموديل في brain.py من غير ما نغير حاجة هناك.
    """

    return [entry["text"] for entry in memory]


def get_memories_by_category(memory, category):

    return [
        entry["text"]
        for entry in memory
        if entry.get("category") == category
    ]


# =========================================================
# RELEVANT MEMORIES (الربط الذكي بين الذاكرة والرسالة الحالية)
# =========================================================
#
# بدل ما نحط الذاكرة كلها (لحد 300 عنصر) في كل برومبت - ده
# بيبوظ التركيز ويزود التكلفة من غير داعي - بنختار بس العناصر
# الأكتر صلة بالرسالة الحالية عن طريق تطابق الكلمات المشتركة.
# لو مفيش رسالة، أو عدد عناصر الذاكرة أصلاً صغير، بنرجع الكل
# زي ما هو من غير فلترة.
# =========================================================

def get_relevant_memories(
    memory,
    message="",
    limit=40
):

    if not memory:
        return []

    if not message or len(memory) <= limit:

        return get_memories(memory)

    message_words = _tokenize(message)

    if not message_words:

        # مفيش كلمات نقدر نقارن بيها - رجّع الأحدث بدل عشوائي
        newest = sorted(
            memory,
            key=lambda e: e.get("created_at", ""),
            reverse=True
        )

        return get_memories(newest[:limit])

    scored = []

    for entry in memory:

        overlap = len(
            message_words & _tokenize(entry.get("text", ""))
        )

        scored.append((overlap, entry))

    best_overlap = max(score for score, _ in scored)

    if best_overlap == 0:

        # مفيش أي تطابق كلمات - الأحدث أفضل من عشوائي
        newest = sorted(
            memory,
            key=lambda e: e.get("created_at", ""),
            reverse=True
        )

        return get_memories(newest[:limit])

    scored.sort(
        key=lambda pair: (
            pair[0],
            pair[1].get("created_at", "")
        ),
        reverse=True
    )

    top_entries = [entry for _, entry in scored[:limit]]

    return get_memories(top_entries)


# =========================================================
# REMINDERS
# =========================================================

def get_due_reminders(memory):
    """
    بترجع كل التذكيرات اللي ميعادها وصل (النهاردة أو قبل كده)
    ولسه مترجعتش. استخدمها لما تفتح بيرلا أول حاجة في اليوم،
    أو لما تسألها "فيه حاجة تفكرني بيها؟".
    """

    today = date.today().isoformat()

    due = [
        entry for entry in memory
        if entry.get("remind_on")
        and entry["remind_on"] <= today
        and not entry.get("reminded")
    ]

    return due


def mark_reminded(memory, entry_id):

    for entry in memory:

        if entry.get("id") == entry_id:

            entry["reminded"] = True

            save_memory(memory)

            return True

    return False