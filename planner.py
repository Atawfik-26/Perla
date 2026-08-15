import json

from openai import OpenAI

from brain import (
    get_api_key,
    OPENROUTER_BASE_URL,
    send_request_with_fallback,
)

from model_selector import get_model_candidates


# =========================================================
# PERLA PLANNER
# =========================================================
#
# الفكرة:
# 1. ناخد مهمة كبيرة من أحمد (زي "اعمليلي خطة كامبين لـ BABULLES")
# 2. نبعتها لموديل تحليل قوي عشان يقسمها لخطوات واضحة (JSON)
# 3. ننفذ كل خطوة لوحدها، باستخدام نفس الـfallback بتاع brain.py
# 4. نجمع كل النتايج في رد نهائي واحد منظم
# =========================================================


PLAN_SYSTEM_PROMPT = """
أنتِ مخططة مهام داخل بيرلا.
مهمتك تقسيم المهمة الكبيرة اللي هتوصلك إلى خطوات فرعية
واضحة وقابلة للتنفيذ، كل خطوة تقدر تتحل لوحدها.

اكتبي الرد **بصيغة JSON فقط** بدون أي شرح إضافي، بالشكل ده:

{
  "steps": [
    "وصف الخطوة الأولى",
    "وصف الخطوة الثانية",
    "..."
  ]
}

قواعد:
- من 2 إلى 6 خطوات كحد أقصى (متقسميش المهمة أكتر من اللازم).
- كل خطوة لازم تكون واضحة ومحددة، مش عامة.
- لو المهمة بسيطة أصلاً ومحتاجاش تقسيم، رجعي خطوة واحدة بس.
"""


def _get_client():

    api_key = get_api_key()

    if not api_key:

        return None

    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL
    )


# =========================================================
# AUTO-DETECT: هل المهمة دي محتاجة تخطيط بدون ما أحمد يطلب؟
# =========================================================
#
# ده هو "التخطيط الذاتي": مش لازم أحمد يدوس على زرار الخطة
# (🗺️) كل مرة. أي رسالة نص عادية بتوصل لـ /chat بتتفحص هنا
# الأول، ولو شكلها مهمة كبيرة/مركبة، بيرلا بتقسمها وتنفذها
# تلقائيًا زي بالظبط لو أحمد كان طالب /chat/plan بنفسه.
#
# القرار مبني على قواعد بسيطة وسريعة (heuristics) من غير ما
# نستهلك استدعاء موديل إضافي لكل رسالة بتوصل - ده مهم عشان
# السرعة والتكلفة، ومناسب لأن الإشارات دي غالبًا واضحة في
# نص الرسالة نفسها.
# =========================================================

PLANNING_KEYWORDS = [
    "خطة كاملة",
    "خطة متكاملة",
    "خطوة بخطوة",
    "قسم المهمة",
    "قسمها خطوات",
    "كامبين كامل",
    "استراتيجية كاملة",
    "دراسة جدوى",
    "من الألف للياء",
    "خطوات متتالية",
    "نفذ المهمة دي",
    "اعمل خطة",
    "اعملي خطة",
    "محتاجة خطوات",
    "خطة عمل",
    "پلان",
    "plan",
]

# لو الرسالة طويلة ومفصلة كده (بالحروف تقريبًا) مع نوع مهمة
# "reasoning"، الأغلب إنها مهمة مركبة تستاهل تقسيم، حتى من
# غير كلمة مفتاحية صريحة.
MIN_LENGTH_FOR_AUTO_PLAN = 220


def needs_planning(message, task_type=None):
    """
    بترجع True لو المهمة تستاهل تتقسم لخطوات تلقائيًا.
    """

    if not message:
        return False

    text = message.strip().lower()

    for keyword in PLANNING_KEYWORDS:

        if keyword in text:

            return True

    if (
        task_type == "reasoning"
        and len(text) >= MIN_LENGTH_FOR_AUTO_PLAN
    ):

        return True

    return False


# =========================================================
# STEP 1: DECOMPOSE TASK INTO STEPS
# =========================================================

def decompose_task(task):
    """
    بتاخد المهمة الكبيرة وترجع قايمة خطوات (نصوص).
    لو حصل أي مشكلة (موديل فشل، رد مش JSON صحيح)،
    بترجع المهمة الأصلية كخطوة واحدة بدل ما توقف بيرلا.
    """

    client = _get_client()

    if client is None:

        return [task]

    candidates = get_model_candidates("reasoning")

    try:

        raw_result, used_model = send_request_with_fallback(

            client,

            candidates,

            PLAN_SYSTEM_PROMPT,

            task

        )

        # نظفي أي فورمات زيادة (زي ```json```) لو الموديل حطها
        cleaned = (
            raw_result
            .strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        data = json.loads(cleaned)

        steps = data.get("steps", [])

        steps = [
            str(step).strip()
            for step in steps
            if str(step).strip()
        ]

        if not steps:

            return [task]

        return steps

    except Exception as error:

        print(
            f"[PERLA PLANNER] فشل تقسيم المهمة: {repr(error)}"
        )

        # مفيش تقسيم، ننفذ المهمة كخطوة واحدة زي ما هي
        return [task]


# =========================================================
# STEP 2: EXECUTE A SINGLE STEP
# =========================================================

def execute_step(
    step,
    completed_steps,
    memory
):
    """
    بتنفذ خطوة واحدة، وبتدي الموديل سياق الخطوات اللي
    خلصت قبلها عشان يبني عليها بدل ما يبدأ من الصفر كل مرة.
    """

    client = _get_client()

    if client is None:

        return "مش قادرة أنفذ الخطوة دي - مفتاح OpenRouter مش موجود."

    candidates = get_model_candidates("reasoning")

    context_text = (
        "\n".join(
            f"- {s['step']}: {s['result']}"
            for s in completed_steps
        )
        if completed_steps
        else "لسه مفيش خطوات اتنفذت."
    )

    memory_text = (
        "\n".join(f"- {item}" for item in memory)
        if memory
        else "لا توجد معلومات محفوظة."
    )

    instructions = f"""
أنتِ بيرلا، بتنفذي خطوة واحدة من خطة أكبر.

الذاكرة المتاحة:
{memory_text}

الخطوات اللي خلصت قبل كده:
{context_text}

نفذي الخطوة الحالية فقط، بوضوح ومباشرة، من غير مقدمات طويلة.
"""

    try:

        result, used_model = send_request_with_fallback(

            client,

            candidates,

            instructions,

            step

        )

        return result

    except Exception as error:

        print(
            f"[PERLA PLANNER] فشلت الخطوة '{step}': {repr(error)}"
        )

        return (
            "معرفتش أنفذ الخطوة دي بسبب مشكلة تقنية 😕"
        )


# =========================================================
# STEP 3: FULL PLAN + EXECUTE
# =========================================================

def plan_task(
    message,
    memory=None
):
    """
    الدالة الرئيسية: بتقسم المهمة، تنفذ كل خطوة، وترجع
    رد نهائي منظم فيه كل الخطوات ونتايجها.
    """

    memory = memory or []

    message = (message or "").strip()

    if not message:

        return "قولّيلي إيه المهمة الأول يا أحمد 😄"

    print(
        "\n========== PERLA PLANNER =========="
    )

    print(
        f"[PERLA PLANNER] المهمة: {message}"
    )

    steps = decompose_task(message)

    print(
        f"[PERLA PLANNER] عدد الخطوات: {len(steps)}"
    )

    for i, step in enumerate(steps, start=1):

        print(
            f"[PERLA PLANNER] خطوة {i}: {step}"
        )

    print(
        "===================================\n"
    )

    completed_steps = []

    for step in steps:

        result = execute_step(
            step,
            completed_steps,
            memory
        )

        completed_steps.append({
            "step": step,
            "result": result
        })

    # ---------------------------------------------------
    # لو خطوة واحدة بس، مفيش داعي نعرض تقسيم -
    # نرجع النتيجة زي ما هي مباشرة.
    # ---------------------------------------------------

    if len(completed_steps) == 1:

        return completed_steps[0]["result"]

    # ---------------------------------------------------
    # أكتر من خطوة: نبني رد منظم فيه كل خطوة ونتيجتها
    # ---------------------------------------------------

    parts = []

    for i, item in enumerate(completed_steps, start=1):

        parts.append(
            f"**{i}. {item['step']}**\n{item['result']}"
        )

    return "\n\n".join(parts)