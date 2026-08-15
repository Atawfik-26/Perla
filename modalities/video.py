def create_video_input(video_url):
    return {
        "type": "video_url",
        "video_url": {
            "url": video_url
        }
    }


def build_video_message(text, video_url):
    return {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": text
            },
            create_video_input(video_url)
        ]
    }