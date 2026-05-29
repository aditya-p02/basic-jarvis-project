import sys
import os
import time
from PyQt5.QtWidgets import QApplication

# Import your newly organized custom modules from the core package
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
        self.hud = JarvisHUD()
        self.automator = Automator()
        
        # Initialize the decoupled functional core engines
        self.speech = SpeechEngine()
        self.brain = AgentBrain()
        self.executor = CodeExecutor(self.automator)
        
        # Initialize thread engines
        self.vision_thread = VisionEngine()
        self.voice_thread = VoiceEngine()
        
        # Connect signals to the UI HUD and central processing block
        self.vision_thread.gesture_signal.connect(self.hud.update_action)
        self.voice_thread.status_signal.connect(self.hud.update_status)
        self.voice_thread.command_signal.connect(self.process_command)

    def process_command(self, cmd):
        self.hud.update_action(f"CMD: {cmd}")
        
        # Core system interrupt handled locally
        if "shutdown jarvis" in cmd:
            self.speech.speak("Shutting down core systems. Have a fantastic day!")
            time.sleep(3) 
            self.shutdown()
            return

        self.hud.update_status("Thinking...")
        
        try:
            # Let the brain process the command using database persistent history
            generated_code = self.brain.think(cmd)
            print(f"--- [AGENT EXECUTING CODE] ---\n{generated_code}\n------------------------------")
            
            self.hud.update_status("Executing...")
            # Execute the generated string sequence inside the custom sandbox environment
            execution_output = self.executor.execute(generated_code)
            
            # Formulate speech response from standard output
            reply = execution_output.strip() if execution_output.strip() else "Task executed."
                
            self.hud.update_status("Responding...")
            self.speech.speak(reply, error_callback=lambda: self.hud.update_status("SPEECH ERROR"))
            
            # Wipes session logs if a message sequence successfully finishes execution
            if "Message dispatched." in reply:
                self.brain.flush_memory()
            
        except Exception as e:
            self.hud.update_status("Agent Error")
            print(f"[CORE ERROR] {e}")
            self.speech.speak("I encountered an internal error processing that request.")

    def start(self):
        self.hud.show()
        self.vision_thread.start()
        self.voice_thread.start()
        self.speech.speak("Agentic core initialized. Awaiting your instructions.")
        sys.exit(self.app.exec_())

    def shutdown(self):
        self.vision_thread.stop()
        self.voice_thread.stop()
        self.app.quit()

if __name__ == "__main__":
    os_system = GestureOS()
    os_system.start()