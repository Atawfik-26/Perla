# =========================================================
# PERLA MODEL SELECTOR
# =========================================================

import os


# =========================================================
# AUTO
# =========================================================

AUTO_MODEL = os.getenv(
    "PERLA_AUTO_MODEL",
    "openrouter/auto"
)


# =========================================================
# MODEL POOL
# =========================================================

MODELS = {

    "openai": os.getenv(
        "PERLA_OPENAI_MODEL",
        "openai/gpt-4o"
    ),

    "claude": os.getenv(
        "PERLA_CLAUDE_MODEL",
        "anthropic/claude-sonnet-4"
    ),

    "gemini": os.getenv(
        "PERLA_GEMINI_MODEL",
        "google/gemini-2.5-pro-preview"
    ),

    "deepseek": os.getenv(
        "PERLA_DEEPSEEK_MODEL",
        "deepseek/deepseek-chat"
    ),

    "auto": AUTO_MODEL,
}


# =========================================================
# TASK STRATEGY
# =========================================================

TASK_MODELS = {

    "fast": [
        "gemini",
        "deepseek",
        "auto",
    ],

    "reasoning": [
        "deepseek",
        "claude",
        "openai",
        "auto",
    ],

    "coding": [
        "deepseek",
        "claude",
        "openai",
        "auto",
    ],

    "research": [
        "gemini",
        "claude",
        "openai",
        "auto",
    ],

    "math": [
        "deepseek",
        "openai",
        "claude",
        "auto",
    ],

    "creative": [
        "claude",
        "gemini",
        "openai",
        "auto",
    ],

    "vision": [
        "gemini",
        "claude",
        "openai",
        "auto",
    ],

    "audio": [
        "gemini",
        "openai",
        "auto",
    ],

    "auto": [
        "auto",
    ],
}


# =========================================================
# SELECT MODEL
# =========================================================

def select_model(task_type=None):

    task_type = (task_type or "auto").strip().lower()

    candidates = TASK_MODELS.get(
        task_type,
        TASK_MODELS["auto"]
    )

    if not candidates:
        return AUTO_MODEL

    for model_key in candidates:
        model = MODELS.get(model_key)
        if model:
            return model

    return AUTO_MODEL


# =========================================================
# GET CANDIDATES
# =========================================================

def get_model_candidates(task_type=None):

    task_type = (task_type or "auto").strip().lower()

    candidates = TASK_MODELS.get(
        task_type,
        TASK_MODELS["auto"]
    )

    return [
        MODELS[key]
        for key in candidates
        if key in MODELS and MODELS[key]
    ]


# =========================================================
# MODEL INFO
# =========================================================

def get_model_pool():
    return dict(MODELS)


# =========================================================
# DEBUG
# =========================================================

def print_models():

    print("\n========== PERLA MODEL POOL ==========")

    for name, model in MODELS.items():
        print(f"{name:12} -> {model}")

    print("\n========== PERLA TASK ROUTING ==========")

    for task, candidates in TASK_MODELS.items():
        readable = [
            MODELS.get(key, key)
            for key in candidates
        ]
        print(f"{task:12} -> " + " -> ".join(readable))

    print("========================================\n")


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print_models()

    print("TEST:")

    tests = [
        "fast",
        "reasoning",
        "coding",
        "research",
        "math",
        "creative",
        "vision",
        "audio",
    ]

    for task in tests:
        print(f"{task:12} -> {select_model(task)}")