import sounddevice as sd
import numpy as np
import speech_recognition as sr
import queue
from PyQt5.QtCore import QThread, pyqtSignal

class VoiceEngine(QThread):
    command_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.q = queue.Queue()

    def audio_callback(self, indata, frames, time, status):
        self.q.put(indata.copy())

    def run(self):
        recognizer = sr.Recognizer()
        sample_rate = 16000
        
        # 1. INCREASE SENSITIVITY TO IGNORE BACKGROUND NOISE/MEET CALLS
        VOLUME_THRESHOLD = 400  # Changed from 150 to 400
        SILENCE_LIMIT = 1.2    
        
        print("[SYSTEM] Advanced Audio Stream Online...")
        
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', callback=self.audio_callback):
            while self.running:
                self.status_signal.emit("LISTENING")
                
                audio_buffer = []
                recording = False
                silence_timer = 0
                
                while self.running:
                    chunk = self.q.get()
                    volume = np.abs(chunk).mean() 
                    
                    if volume > VOLUME_THRESHOLD:
                        if not recording:
                            print("[SYSTEM] Voice detected. Recording...")
                        recording = True
                        silence_timer = 0
                        audio_buffer.append(chunk)
                    
                    elif recording:
                        silence_timer += len(chunk) / sample_rate
                        audio_buffer.append(chunk)
                        
                        if silence_timer > SILENCE_LIMIT:
                            break
                            
                if audio_buffer:
                    self.status_signal.emit("THINKING")
                    audio_data = np.concatenate(audio_buffer)
                    sr_audio = sr.AudioData(audio_data.tobytes(), sample_rate, 2)
                    
                    try:
                        text = recognizer.recognize_google(sr_audio).lower()
                        print(f"[USER SAID] {text}")
                        self.command_signal.emit(text)
                        
                    # 2. PRINT WHEN IT HEARS UNRECOGNIZABLE NOISE
                    except sr.UnknownValueError:
                        print("[SYSTEM] Audio processed, but no clear words were recognized (Mic conflict or static).")
                    except Exception as e:
                        print(f"[ERROR] Translation Error: {e}")

    def stop(self):
        self.running = False