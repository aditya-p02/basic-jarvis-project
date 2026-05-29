import os
import time
import asyncio
import threading
import edge_tts
from playsound import playsound

class SpeechEngine:
    def __init__(self, voice="en-US-AndrewNeural"):
        self.voice = voice

    def speak(self, text, error_callback=None):
        def run_speak():
            try:
                # Strip out any bad quote marks that mess up audio parsing
                safe_text = text.replace('"', '').replace("'", "")
                audio_file = f"jarvis_response_{int(time.time())}.mp3"
                
                async def generate_audio():
                    communicate = edge_tts.Communicate(safe_text, self.voice)
                    await communicate.save(audio_file)
                
                asyncio.run(generate_audio())
                
                if os.path.exists(audio_file):
                    playsound(audio_file)
                    try:
                        os.remove(audio_file)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[SPEECH ERROR] {e}")
                if error_callback:
                    error_callback()
                
        threading.Thread(target=run_speak, daemon=True).start()