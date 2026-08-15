def create_image_input(image_url):
    return {
        "type": "image_url",
        "image_url": {
            "url": image_url
        }
    }


def build_vision_message(text, image_url):
    return {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": text
            },
            create_image_input(image_url)
        ]
    }