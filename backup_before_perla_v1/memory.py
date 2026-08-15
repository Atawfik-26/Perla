import json
import os


MEMORY_FILE = "memory.json"


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

            return data

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


def add_memory(memory, item):

    item = str(item).strip()

    if not item:
        return False

    if item in memory:
        return False

    memory.append(item)

    save_memory(memory)

    return True


def remove_memory(memory, item):

    if item not in memory:
        return False

    memory.remove(item)

    save_memory(memory)

    return True


def clear_memory(memory):

    memory.clear()

    save_memory(memory)


def memory_contains(memory, item):

    return item in memory


def get_memories(memory):

    return list(memory)