"""
JARVIS GestureOS v2 — Multi-Agent Edition
- Multi-agent routing (6 specialized agents)
- Persistent long-term memory
- Screen vision awareness
- Preference learning
- Enhanced wake word handling
"""
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
from core.screen_vision import ScreenVision
from ui.hud import JarvisHUD


class GestureOS:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.loop = qasync.QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)

        print("[SYSTEM] Initializing JARVIS v2...")
        
        self.hud = JarvisHUD()
        self.automator = Automator()
        self.speech = SpeechEngine()
        self.brain = AgentBrain()
        self.executor = CodeExecutor(self.automator)
        
        # Screen vision — shares Groq client with brain for efficiency
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv()
        vision_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.screen_vision = ScreenVision(
            vision_client=vision_client,
            vision_model="meta-llama/llama-4-scout-17b-16e-instruct"
        )

        # Vision & Voice threads
        self.vision_thread = VisionEngine()
        self.voice_thread = VoiceEngine()

        self.vision_thread.gesture_signal.connect(self.hud.update_action)
        self.voice_thread.status_signal.connect(self.hud.update_status)
        self.voice_thread.command_signal.connect(self.process_command)

        self.is_awake = False
        
        # Commands that trigger screen vision injection
        self.SCREEN_TRIGGER_WORDS = [
            "screen", "what's on", "what do you see", "look at", 
            "visible", "open", "showing", "display", "window"
        ]
        
        # Commands to learn user preferences
        self.LEARN_TRIGGERS = ["remember that", "my name is", "i prefer", "always", "never forget"]
        
        print("[SYSTEM] JARVIS v2 fully initialized.")

    def _get_time_greeting(self):
        hour = datetime.now().hour
        name = self.brain.preferences.get("name", "sir")
        if 5 <= hour < 12:
            return f"Good morning, {name}."
        elif 12 <= hour < 17:
            return f"Good afternoon, {name}."
        elif 17 <= hour < 21:
            return f"Good evening, {name}."
        else:
            return f"Working late again, {name}?"

    def _should_use_screen_vision(self, cmd: str) -> bool:
        """Determine if this command needs screen context."""
        cmd_lower = cmd.lower()
        return any(trigger in cmd_lower for trigger in self.SCREEN_TRIGGER_WORDS)

    def _check_for_learning(self, cmd: str):
        """Extract and save user preferences from natural language."""
        cmd_lower = cmd.lower()
        for trigger in self.LEARN_TRIGGERS:
            if trigger in cmd_lower:
                # Extract the fact after the trigger
                idx = cmd_lower.find(trigger) + len(trigger)
                fact = cmd[idx:].strip().rstrip(".")
                if fact:
                    self.brain.learn_fact(fact)
                    return True
        return False

    def process_command(self, cmd: str):
        asyncio.ensure_future(self._async_process_command(cmd))

    async def _async_process_command(self, cmd: str):
        cmd_lower = cmd.lower()
        self.hud.update_action(f"HEARD: {cmd}")

        # ══════════════════════════════════════════
        # WAKE WORD LOGIC
        # ══════════════════════════════════════════
        if not self.is_awake:
            if "wake up" in cmd_lower and "jarvis" in cmd_lower:
                self.is_awake = True
                self.hud.update_status("ONLINE")
                greeting = self._get_time_greeting()
                await self.loop.run_in_executor(None, self.speech.speak, greeting)
            return

        # ══════════════════════════════════════════
        # BUILT-IN COMMANDS (no LLM needed)
        # ══════════════════════════════════════════
        
        if "go to sleep" in cmd_lower or "standby" in cmd_lower:
            self.is_awake = False
            self.hud.update_status("STANDBY")
            await self.loop.run_in_executor(None, self.speech.speak,
                "Powering down. Call if you need me.")
            return

        if "shutdown jarvis" in cmd_lower:
            await self.loop.run_in_executor(None, self.speech.speak,
                "Shutting down. Have a fantastic day, sir.")
            await asyncio.sleep(3)
            self.shutdown()
            return
        
        if "clear memory" in cmd_lower or "forget everything" in cmd_lower:
            self.brain.flush_memory()
            await self.loop.run_in_executor(None, self.speech.speak,
                "Short-term context cleared, sir. Long-term memory preserved.")
            return
        
        if "memory stats" in cmd_lower or "how much do you remember" in cmd_lower:
            stats = self.brain.db.get_memory_stats()
            reply = (f"I have {stats['long_term']} long-term memories, "
                    f"{stats['tasks_completed']} completed tasks on record, "
                    f"and {stats['short_term']} items in active context.")
            await self.loop.run_in_executor(None, self.speech.speak, reply)
            return

        # Check for preference learning
        self._check_for_learning(cmd)

        # ══════════════════════════════════════════
        # MAIN AGENT PROCESSING
        # ══════════════════════════════════════════
        self.hud.update_status("THINKING")

        # Quick acknowledgment while processing
        quick_replies = [
            "Right away, sir.", "On it.", "Processing that.", 
            "Just a moment.", "Executing.", "Understood."
        ]
        self.loop.run_in_executor(None, self.speech.speak, random.choice(quick_replies))

        try:
            # Optionally inject screen context
            screen_context = None
            if self._should_use_screen_vision(cmd):
                print("[SYSTEM] Screen vision triggered — capturing desktop...")
                self.hud.update_action("📸 Analyzing screen...")
                screen_context = await self.loop.run_in_executor(
                    None, self.screen_vision.describe_for_agent
                )
                print(f"[SCREEN] {screen_context[:100]}...")

            # Route to best agent and generate code
            result = await self.loop.run_in_executor(
                None, self.brain.think, cmd, screen_context
            )
            generated_code, active_agent = result
            
            # Update HUD with active agent
            from agents.router import AGENTS
            agent_info = AGENTS.get(active_agent, {})
            agent_icon = agent_info.get("icon", "🤖")
            self.hud.update_action(f"{agent_icon} {active_agent.upper()} AGENT ACTIVE")
            
            print(f"[EXECUTING via {active_agent.upper()} agent]\n{generated_code}\n")

            self.hud.update_status("EXECUTING")
            execution_output = await self.loop.run_in_executor(
                None, self.executor.execute, generated_code
            )

            reply = execution_output.strip() if execution_output.strip() else "Task completed, sir."

            # Save task to history
            self.brain.db.save_task(cmd, active_agent, reply, success=True)

            self.hud.update_status("RESPONDING")
            print(f"[JARVIS → {active_agent.upper()}]: {reply}")
            await self.loop.run_in_executor(None, self.speech.speak, reply)

        except Exception as e:
            print(f"[CORE ERROR] {e}")
            self.hud.update_status("ERROR")
            self.brain.db.save_task(cmd, "unknown", str(e), success=False)
            await self.loop.run_in_executor(None, self.speech.speak,
                "I've encountered an error in my processing core.")
        finally:
            # v2: DO NOT wipe memory after every task
            # Memory accumulates for better context
            if self.is_awake:
                self.hud.update_status("LISTENING")
                self.hud.update_action("")

    def start(self):
        self.hud.show()
        self.vision_thread.start()
        self.voice_thread.start()
        
        # Startup sequence
        self.speech.speak("All systems online. JARVIS v2 multi-agent core is ready, sir.")
        
        with self.loop:
            self.loop.run_forever()

    def shutdown(self):
        self.vision_thread.stop()
        self.voice_thread.stop()
        self.app.quit()


if __name__ == "__main__":
    os_system = GestureOS()
    os_system.start()
