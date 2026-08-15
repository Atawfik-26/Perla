def create_audio_input(audio_url):
    return {
        "type": "input_audio",
        "input_audio": {
            "data": audio_url,
            "format": "wav"
        }
    }


def build_audio_message(text, audio_url):
    return {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": text
            },
            create_audio_input(audio_url)
        ]
    }