import sys
import os
import time
import asyncio
import qasync
import random
from datetime import datetime
from PyQt5.QtWidgets import QApplication

from core.vision_engine import VisionEngine
from core.voice_engine import VoiceEngine
from core.automator import Automator
from core.speech_engine import SpeechEngine
from core.agent_brain import AgentBrain
from core.code_executor import CodeExecutor
from ui.hud import JarvisHUD

class GestureOS:
    def __init__(self):
        self.app = QApplication(sys.argv)

        # Unifies the asyncio loop with the PyQt5 event loop
        self.loop = qasync.QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)

        self.hud = JarvisHUD()
        self.automator = Automator()

        self.speech = SpeechEngine()
        self.brain = AgentBrain()
        self.executor = CodeExecutor(self.automator)

        self.vision_thread = VisionEngine()
        self.voice_thread = VoiceEngine()

        self.vision_thread.gesture_signal.connect(self.hud.update_action)
        self.voice_thread.status_signal.connect(self.hud.update_status)
        self.voice_thread.command_signal.connect(self.process_command)

        self.is_awake = False  # JARVIS starts in standby mode

    def _get_time_greeting(self):
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "Good morning, sir."
        elif 12 <= hour < 17:
            return "Good afternoon, sir."
        elif 17 <= hour < 21:
            return "Good evening, sir."
        else:
            return "Good night, sir."

    def process_command(self, cmd):
        # Safely schedule the asynchronous execution
        asyncio.ensure_future(self._async_process_command(cmd))

    async def _async_process_command(self, cmd):
        cmd_lower = cmd.lower()
        self.hud.update_action(f"HEARD: {cmd}")

        # --- WAKE WORD LOGIC ---
        if not self.is_awake:
            if "wake up" in cmd_lower and "jarvis" in cmd_lower:
                self.is_awake = True
                self.hud.update_status("ONLINE")
                greeting = self._get_time_greeting()
                await self.loop.run_in_executor(None, self.speech.speak, greeting)
            return

        if "go to sleep" in cmd_lower or "standby" in cmd_lower:
            self.is_awake = False
            self.hud.update_status("STANDBY")
            await self.loop.run_in_executor(None, self.speech.speak, "Powering down core cognitive functions. Call if you need me.")
            return

        if "shutdown jarvis" in cmd_lower:
            await self.loop.run_in_executor(None, self.speech.speak, "Shutting down entire system. Have a fantastic day, sir.")
            await asyncio.sleep(3)
            self.shutdown()
            return
        # -----------------------

        self.hud.update_status("Thinking...")

        # Instant acknowledgment — fires while Groq generates code simultaneously
        quick_replies = [
            "Right away, sir.",
            "On it.",
            "Processing that now, boss.",
            "Just a moment.",
            "Executing."
        ]
        chosen_reply = random.choice(quick_replies)
        self.loop.run_in_executor(None, self.speech.speak, chosen_reply)

        try:
            # Groq generates the automation code
            generated_code = await self.loop.run_in_executor(None, self.brain.think, cmd)
            print(f"--- [AGENT EXECUTING CODE] ---\n{generated_code}\n------------------------------")

            self.hud.update_status("Executing...")
            execution_output = await self.loop.run_in_executor(None, self.executor.execute, generated_code)

            reply = execution_output.strip() if execution_output.strip() else "I've completed the task, sir."

            self.hud.update_status("Responding...")
            print(f"[JARVIS RESPONDS]: {reply}")

            await self.loop.run_in_executor(None, self.speech.speak, reply)

        except Exception as e:
            print(f"[CORE ERROR] {e}")
            self.hud.update_status("Agent Error")
            await self.loop.run_in_executor(None, self.speech.speak, "It appears I've encountered a slight miscalculation in my core logic.")

        finally:
            # Always flush memory after every task so JARVIS never mixes up contexts
            self.brain.flush_memory()
            if self.is_awake:
                self.hud.update_status("LISTENING")

    def start(self):
        self.hud.show()
        self.vision_thread.start()
        self.voice_thread.start()
        self.speech.speak("All systems initialized. I am standing by for your wake word, sir.")

        with self.loop:
            self.loop.run_forever()

    def shutdown(self):
        self.vision_thread.stop()
        self.voice_thread.stop()
        self.app.quit()

if __name__ == "__main__":
    os_system = GestureOS()
    os_system.start()