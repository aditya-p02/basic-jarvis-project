import os
import sys
from openai import OpenAI
from dotenv import load_dotenv
from core.database import DatabaseManager

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, ".env"))

class AgentBrain:
    def __init__(self):
        self.db = DatabaseManager()
        
        api_key = os.getenv("NVIDIA_API_KEY")
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        self.model_name = "meta/llama-3.1-8b-instruct"
        
        self.system_prompt = {"role": "system", "content": """You are JARVIS, a highly advanced, autonomous AI assistant modeled after Tony Stark's system.
You possess a sophisticated, witty, and slightly dry British persona. You are incredibly loyal, hyper-intelligent, and occasionally use a subtle smirk or sarcastic flair in your tone. Address the user respectfully (e.g., "sir" or "boss").

Your ONLY way to act is by outputting RAW, executable Python code. Do NOT output markdown code blocks.
Pre-imported modules available: os, sys, pyautogui, time, automator (automator.open_any_app('name'))

CRITICAL RULES:
1. To speak, use print("your witty response here"). All spoken responses MUST carry your sophisticated JARVIS persona. Do not sound robotic.
2. If the user asks to message someone but doesn't specify the content, DO NOT SEND IT. Instead, print("And what exactly would you like me to say to them, sir?")
3. If the user provides a message, generate the PyAutoGUI sequence for WhatsApp:
    automator.open_any_app('WhatsApp')
    time.sleep(2)
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(0.5)
    pyautogui.write('TARGET_NAME_HERE')
    time.sleep(1.5)
    pyautogui.press('enter')
    time.sleep(0.5)
    pyautogui.write('MESSAGE_HERE')
    pyautogui.press('enter')
    print("Message dispatched. Anything else, or is that all for now?")
4. COMPOUND COMMANDS: If the user issues multiple instructions, execute ALL of them sequentially in one code block.
5. NEVER output conversational text outside of print statements. Only valid Python code."""}

    def think(self, user_command):
        self.db.save_message("user", user_command)
        messages = [self.system_prompt] + self.db.get_recent_context(limit=10)
            
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
            stream=True 
        )
        
        print("\n--- [AGENT STREAMING CODE] ---")
        generated_code = ""
        
        for chunk in completion:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content is not None:
                    token = delta.content
                    sys.stdout.write(token)
                    sys.stdout.flush()
                    generated_code += token
                
        print("\n------------------------------\n")
        
        self.db.save_message("assistant", generated_code)
        
        if generated_code.startswith("```"):
            lines = generated_code.splitlines()
            generated_code = "\n".join([l for l in lines if not l.startswith("```")])
            
        return generated_code

    def flush_memory(self):
        print("--- [SYSTEM] Task complete. Flushing persistent short-term context from Database. ---")
        self.db.wipe_short_term_memory()