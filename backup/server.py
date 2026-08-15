from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from brain import think
from memory import load_memory, save_memory
from chat_history import load_history, save_history, add_message


app = FastAPI(title="Perla")


memory = load_memory()
history = load_history()


app.mount(
    "/static",
    StaticFiles(directory="web"),
    name="static"
)


class Message(BaseModel):
    message: str


@app.get("/")
def home():
    return FileResponse("web/index.html")


@app.get("/app")
def web_app():
    return FileResponse("web/index.html")


@app.post("/chat")
def chat(data: Message):

    message = data.message.strip()

    if not message:
        return {
            "response": "قولّي حاجة يا أحمد 😄"
        }

    add_message(
        history,
        "user",
        message
    )

    response = think(
        message,
        memory,
        history
    )

    add_message(
        history,
        "assistant",
        response
    )

    save_memory(memory)
    save_history(history)

    return {
        "response": response
    }