import json
from config import PERLA_NAME, USER_NAME
from ai import get_ai_response

MEMORY_FILE = "memory.json"


def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return []


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)


memory = load_memory()

print(PERLA_NAME + " is ready")
print("Type remember to save a memory")
print("Type memories to view memories")
print("Type exit to quit")

while True:
    message = input("You: ").strip()

    if message.lower() == "exit":
        print(PERLA_NAME + ": Bye " + USER_NAME)
        break

    elif message.lower() == "remember":
        text = input("Memory: ").strip()

        if text:
            memory.append(text)
            save_memory(memory)
            print(PERLA_NAME + ": Memory saved")

    elif message.lower() == "memories":
        print("Saved memories:")

        if not memory:
            print("No memories yet")
        else:
            for i, item in enumerate(memory, 1):
                print(str(i) + ". " + item)

    else:
        response = get_ai_response(message, memory)
        print(PERLA_NAME + ": " + response)