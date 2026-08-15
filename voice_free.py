import os
import uuid
import tempfile

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def transcribe_audio(file_path: str, language: str = "ar-EG") -> str:
    try:
        import speech_recognition as sr
        from pydub import AudioSegment
    except ImportError:
        raise RuntimeError("محتاج تثبت: pip install SpeechRecognition pydub")

    wav_path = os.path.join(tempfile.gettempdir(), f"voice_{uuid.uuid4().hex[:8]}.wav")
    try:
        audio = AudioSegment.from_file(file_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(wav_path, format="wav")
    except Exception:
        wav_path = file_path

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio_data, language=language)
        return text.strip()
    except sr.UnknownValueError:
        return "مش قادر أفهم الصوت. جرب تتكلم أوضح."
    except sr.RequestError as e:
        return f"مشكلة في الاتصال: {str(e)}"
    finally:
        if wav_path != file_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except:
                pass


def text_to_speech(text: str, voice: str = None) -> str:
    try:
        from gtts import gTTS
    except ImportError:
        raise RuntimeError("محتاج تثبت: pip install gtts")

    if not text or not text.strip():
        raise ValueError("النص فاضي")

    filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join(UPLOAD_DIR, filename)

    tts = gTTS(text=text[:4000], lang="ar", slow=False)
    tts.save(output_path)

    return output_path


def voice_chat_pipeline(audio_path: str, brain_think_func, memory=None, history=None, history_obj=None, message: str = "", voice: str = None):
    transcription = transcribe_audio(audio_path)

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

    audio_out_path = text_to_speech(llm_response)

    return {
        "transcription": transcription,
        "response": llm_response,
        "audio_url": f"/uploads/{os.path.basename(audio_out_path)}"
    }