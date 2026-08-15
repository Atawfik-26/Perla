import base64
import mimetypes
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_api_key():
    return os.getenv("OPENROUTER_API_KEY")


def image_to_data_url(image_path):

    mime_type, _ = mimetypes.guess_type(image_path)

    if not mime_type:
        mime_type = "image/jpeg"

    with open(image_path, "rb") as image_file:

        encoded = base64.b64encode(
            image_file.read()
        ).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def analyze_image(
    image_path,
    question="حللي الصورة دي."
):

    api_key = get_api_key()

    if not api_key:

        return (
            "مش قادر أحلل الصورة لأن "
            "OpenRouter API Key مش متوصل."
        )


    if not os.path.exists(image_path):

        return "الصورة مش موجودة في المسار المحدد."


    try:

        client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL
        )


        image_url = image_to_data_url(
            image_path
        )


        response = client.chat.completions.create(

            model="openrouter/auto",

            messages=[

                {
                    "role": "system",
                    "content": (
                        "أنتِ بيرلا. "
                        "حللي الصور بدقة، "
                        "ولا تدّعي رؤية شيء غير موجود."
                    )
                },

                {
                    "role": "user",

                    "content": [

                        {
                            "type": "text",
                            "text": question
                        },

                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }

                    ]
                }

            ]
        )


        result = response.choices[0].message.content


        if not result:

            return "الموديل رجع رد فاضي 😅"


        actual_model = getattr(
            response,
            "model",
            None
        )

        if actual_model:

            print(
                "PERLA VISION MODEL:",
                actual_model
            )


        return result


    except Exception as error:

        print(
            "VISION ERROR:",
            repr(error)
        )

        return (
            "حصلت مشكلة وأنا بحاول أحلل الصورة 😕"
        )