import os
import uuid
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# =========================================================
# CONFIG
# =========================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
TTS_VOICE = os.getenv("PERLA_TTS_VOICE", "alloy")
TTS_MODEL = os.getenv("PERLA_TTS_MODEL", "tts-1")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# CLIENT
# =========================================================

_client = None

def get_voice_client():
    global _client
    if _client is None and OpenAI is not None and OPENAI_API_KEY:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


# =========================================================
# STT - Speech to Text (Whisper)
# =========================================================

def transcribe_audio(file_path: str, language: str = "ar") -> str:
    """
    بيحول ملف صوتي لنص باستخدام Whisper.
    بيرجع النص العربي (أو اللغة المحددة).
    """
    client = get_voice_client()
    if not client:
        raise RuntimeError(
            "مفتاح OpenAI API مش موجود. "
            "ضيف OPENAI_API_KEY أو OPENROUTER_API_KEY في .env"
        )

    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language
        )

    return transcript.text.strip()


# =========================================================
# TTS - Text to Speech (OpenAI TTS)
# =========================================================

def text_to_speech(
    text: str,
    output_path: str = None,
    voice: str = None
) -> str:
    """
    بيحول نص لملف صوتي MP3.
    بيرجع مسار الملف.
    """
    client = get_voice_client()
    if not client:
        raise RuntimeError(
            "مفتاح OpenAI API مش موجود. "
            "ضيف OPENAI_API_KEY أو OPENROUTER_API_KEY في .env"
        )

    if not text or not text.strip():
        raise ValueError("النص فاضي")

    voice = voice or TTS_VOICE

    if output_path is None:
        filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
        output_path = os.path.join(UPLOAD_DIR, filename)

    # OpenAI TTS limit ~4096 chars
    text = text[:4000]

    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=voice,
        input=text
    )

    response.stream_to_file(output_path)

    return output_path


def text_to_speech_bytes(text: str, voice: str = None) -> bytes:
    """
    بيحول نص لـ bytes صوتية (مفيد للـ streaming).
    """
    client = get_voice_client()
    if not client:
        raise RuntimeError("مفتاح API مش موجود")

    voice = voice or TTS_VOICE
    text = text[:4000]

    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=voice,
        input=text
    )

    return response.content


# =========================================================
# VOICE CHAT PIPELINE
# =========================================================

def voice_chat_pipeline(
    audio_path: str,
    brain_think_func,
    memory=None,
    history=None,
    history_obj=None,
    message: str = "",
    voice: str = None
):
    """
    Pipeline كامل:
    1. STT: صوت -> نص
    2. LLM: نص -> رد
    3. TTS: رد -> صوت

    بيرجع dict فيه: transcription, response, audio_path
    """
    # 1. STT
    transcription = transcribe_audio(audio_path)

    # 2. LLM
    full_message = message.strip()
    if full_message:
        full_message += f"\n\n[تسجيل صوتي: {transcription}]"
    else:
        full_message = transcription

    llm_response = brain_think_func(
        message=full_message,
        memory=memory,
        history=history,
        history_obj=history_obj
    )

    # 3. TTS
    audio_out_path = text_to_speech(llm_response, voice=voice)

    return {
        "transcription": transcription,
        "response": llm_response,
        "audio_path": audio_out_path,
        "audio_url": f"/uploads/{os.path.basename(audio_out_path)}"
    }
