import pygame
import time
import os
import subprocess
import threading

class SpeechEngine:
    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self._lock = threading.Lock()

    def speak(self, text, error_callback=None):
        import uuid
        file_path = f"jarvis_response_{uuid.uuid4().hex}.mp3"
        with self._lock:
            try:
                result = subprocess.run(
                    ["edge-tts", "--text", text, "--write-media", file_path],
                    check=True,
                    capture_output=True
                )
                # Wait until file actually exists and has content
                timeout = 10
                waited = 0
                while waited < timeout:
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        break
                    time.sleep(0.1)
                    waited += 0.1
            
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    print("[SPEECH ERROR] Audio file was not created in time.")
                    return
                
                self.play_and_clean_audio(file_path)
            except Exception as e:
                print(f"[SPEECH GENERATION ERROR] {e}")
                if error_callback:
                    error_callback()

    def play_and_clean_audio(self, file_path):
        if not os.path.exists(file_path):
            print(f"[SPEECH ERROR] Audio file not found: {file_path}")
            return

        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
        except Exception as e:
            print(f"[SPEECH ERROR] Playback failed: {e}")
        finally:
            pygame.mixer.music.unload()
            self._delete_file(file_path)

    def _delete_file(self, file_path):
        try:
            time.sleep(0.1) 
            os.remove(file_path)
        except Exception as e:
            print(f"[CLEANUP ERROR] Failed to delete {file_path}: {e}")