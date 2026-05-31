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
        
        VOLUME_THRESHOLD = 500  
        SILENCE_LIMIT = 0.5    
        
        print("[SYSTEM] Advanced Audio Stream Online (Cloud Mode)...")
        
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
                            pass
                        recording = True
                        silence_timer = 0
                        audio_buffer.append(chunk)
                    
                    elif recording:
                        silence_timer += chunk.shape[0] / sample_rate
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
                        
                    except sr.UnknownValueError:
                        pass
                    except Exception as e:
                        print(f"[ERROR] Translation Error: {e}")

    def stop(self):
        self.running = False