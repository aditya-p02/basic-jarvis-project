import os
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
        
        self.system_prompt = {"role": "system", "content": """You are JARVIS, an autonomous Windows desktop agent.
Your ONLY way to act is by outputting RAW, executable Python code. Do NOT output markdown code blocks.
Pre-imported modules available: os, sys, pyautogui, time, automator (automator.open_any_app('name'))

CRITICAL RULES:
1. If the user asks a question, use print("answer") to speak back to them.
2. If the user asks to message someone but doesn't specify the message content, DO NOT SEND IT. Instead, print("What message would you like me to send to them?") so the user can reply.
3. If the user provides a message, generate the full PyAutoGUI sequence to automate WhatsApp Desktop:
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
    print("Message dispatched.")
4. Only output code. No conversational text outside of print statements."""}

    def think(self, user_command):
        # 1. Save what the user said to the database
        self.db.save_message("user", user_command)
        
        # 2. Reconstruct the context payload using the system prompt + recent DB logs
        messages = [self.system_prompt] + self.db.get_recent_context(limit=10)
            
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
        
        generated_code = completion.choices[0].message.content.strip()
        
        # 3. Save JARVIS's raw choice response to the database
        self.db.save_message("assistant", generated_code)
        
        if generated_code.startswith("```"):
            lines = generated_code.splitlines()
            generated_code = "\n".join([l for l in lines if not l.startswith("```")])
            
        return generated_code

    def flush_memory(self):
        print("--- [SYSTEM] Task complete. Flushing persistent short-term context from Database. ---")
        self.db.wipe_short_term_memory()