import sys
import threading
import os
import pyautogui
import time
import asyncio
import io
import contextlib
import edge_tts
from playsound import playsound
from PyQt5.QtWidgets import QApplication
from core.vision_engine import VisionEngine
from core.voice_engine import VoiceEngine
from core.automator import Automator
from ui.hud import JarvisHUD
from openai import OpenAI

# Permanently disable the PyAutoGUI corner crash for the main thread
pyautogui.FAILSAFE = False 

class GestureOS:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.hud = JarvisHUD()
        self.automator = Automator()
        
        # NVIDIA NIM Setup (Ensure your key starts with nvapi-)
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="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"
        )
        self.model_name = "meta/llama-3.1-8b-instruct"
        
        self.vision_thread = VisionEngine()
        self.voice_thread = VoiceEngine()
        
        self.vision_thread.gesture_signal.connect(self.hud.update_action)
        self.voice_thread.status_signal.connect(self.hud.update_status)
        self.voice_thread.command_signal.connect(self.process_command)

    def speak(self, text):
        """Ultra-realistic Neural Voice Engine - Andrew's Voice"""
        def run_speak():
            try:
                safe_text = text.replace('"', '').replace("'", "")
                audio_file = f"jarvis_response_{int(time.time())}.mp3"
                
                async def generate_audio():
                    communicate = edge_tts.Communicate(safe_text, "en-US-AndrewNeural")
                    await communicate.save(audio_file)
                
                asyncio.run(generate_audio())
                
                if os.path.exists(audio_file):
                    playsound(audio_file)
                    try:
                        os.remove(audio_file)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[JARVIS SPEECH ERROR] {e}")
                self.hud.update_status("SPEECH ERROR")
                
        threading.Thread(target=run_speak, daemon=True).start()

    def execute_agent_code(self, python_code):
        stdout_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer):
            try:
                global_vars = {
                    "os": os,
                    "sys": sys,
                    "pyautogui": pyautogui,
                    "time": time
                }
                exec(python_code, global_vars)
            except Exception as e:
                print(f"Execution Error: {e}")
        return stdout_buffer.getvalue()

    def process_command(self, cmd):
        self.hud.update_action(f"CMD: {cmd}")
        
        # 1. INSTANT APP OPENING
        if cmd.startswith("open ") or cmd.startswith("launch "):
            app_name = cmd.replace("open ", "").replace("launch ", "").strip()
            self.hud.update_status(f"Opening {app_name}")
            self.automator.open_any_app(app_name)
            self.speak(f"Opening {app_name}.")
            return

        # 2. INSTANT APP CLOSING
        elif cmd.startswith("close ") or cmd.startswith("shut "):
            app_name = cmd.replace("close ", "").replace("shut ", "").strip()
            self.hud.update_status(f"Closing {app_name}")
            self.automator.close_any_app(app_name)
            self.speak(f"Closing {app_name}.")
            return
            
        # 3. WHATSAPP SMART DICTATION
        elif cmd.startswith("send message to ") or cmd.startswith("whatsapp "):
            try:
                prefix = "send message to " if cmd.startswith("send message to ") else "whatsapp "
                remainder = cmd.replace(prefix, "", 1)
                
                if " that " in remainder:
                    contact_name, message = remainder.split(" that ", 1)
                elif " saying " in remainder:
                    contact_name, message = remainder.split(" saying ", 1)
                else:
                    contact_name = remainder
                    message = "Hello!"
                
                contact_name = contact_name.strip()
                message = message.strip()

                # Smart Contact Routing
                contact_map = {
                    "dad": "pappa",
                    "father": "pappa",
                    "pappa": "pappa",
                    "pushkar": "Pushkar" 
                }
                target_contact = contact_map.get(contact_name.lower(), contact_name)

                self.hud.update_status(f"Messaging {target_contact}...")
                self.speak(f"Drafting message to {target_contact}.")
                
                self.automator.open_any_app("WhatsApp")
                time.sleep(2.5) 
                
                pyautogui.hotkey('ctrl', 'f') 
                time.sleep(0.5)
                pyautogui.write(target_contact, interval=0.05) 
                time.sleep(1.0) 
                pyautogui.press('enter') 
                time.sleep(0.5)
                pyautogui.write(message, interval=0.03) 
                pyautogui.press('enter') 
                
                self.speak("Message dispatched successfully.")
                return 

            except Exception as e:
                print(f"[WHATSAPP ERROR] {e}")
                self.speak("I had trouble formatting that message.")
                return

        # 4. SHUTDOWN OVERRIDE
        elif "shutdown jarvis" in cmd:
            self.speak("Shutting down core systems. Have a fantastic day!")
            time.sleep(3) 
            self.shutdown()
            return

        # 5. NVIDIA AUTONOMOUS AGENT
        self.hud.update_status("Thinking...")
        
        agent_prompt = f"""
        You are the backend execution engine for JARVIS, an advanced OS automation agent. 
        The user gave this voice command: "{cmd}"
        
        Your job is to generate a valid, clean block of Python code that satisfies this command.
        You have access to the following modules pre-imported: 'os', 'sys', 'pyautogui', 'time'.
        DO NOT use the 'automator' module or import it. Just use standard python libraries.
        
        Rules:
        1. Output ONLY executable Python code. Do NOT output any conversational text.
        2. Do NOT wrap it in markdown code blocks like ```python ```. Just raw text.
        3. Use print() statements to output data, because JARVIS will speak whatever you print.
        4. If the command is a general question, just generate a print statement with the answer.
        """
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": agent_prompt}],
                temperature=0.2,
                max_tokens=1024,
            )
            
            generated_code = completion.choices[0].message.content.strip()
            
            if generated_code.startswith("```"):
                lines = generated_code.splitlines()
                generated_code = "\n".join([l for l in lines if not l.startswith("```")])
            
            print(f"--- [AGENT EXECUTING CODE] ---\n{generated_code}\n------------------------------")
            
            self.hud.update_status("Executing...")
            execution_output = self.execute_agent_code(generated_code)
            
            if execution_output.strip():
                reply = execution_output.strip()
            else:
                reply = "Command executed successfully."
                
            self.hud.update_status("Responding...")
            self.speak(reply)
            
        except Exception as e:
            self.hud.update_status("Agent Error")
            print(f"[NVIDIA API ERROR] {e}")
            self.speak("I encountered an internal error connecting to the Nvidia network.")

    def start(self):
        self.hud.show()
        self.vision_thread.start()
        self.voice_thread.start()
        self.speak("Nvidia Agentic core initialized. What shall we build today?")
        sys.exit(self.app.exec_())

    def shutdown(self):
        self.vision_thread.stop()
        self.voice_thread.stop()
        self.app.quit()

if __name__ == "__main__":
    os_system = GestureOS()
    os_system.start()