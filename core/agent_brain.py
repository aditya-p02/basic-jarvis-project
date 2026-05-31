import os
import sys
import json
from openai import OpenAI
from dotenv import load_dotenv
from core.database import DatabaseManager

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, ".env"))

class AgentBrain:
    def __init__(self):
        self.db = DatabaseManager()

        api_key = os.getenv("GROQ_API_KEY")
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key
        )
        self.model_name = "llama-3.3-70b-versatile"

        # Load contacts from external file
        contacts_path = os.path.join(base_dir, "contacts.json")
        with open(contacts_path, "r") as f:
            self.contacts = json.load(f)

        contact_list = "\n".join(
            f"   - '{k.title()}' -> WhatsApp name: '{v['whatsapp_name']}'"
            for k, v in self.contacts.items()
        )

        self.system_prompt = {"role": "system", "content": f'''You are JARVIS, a highly advanced, autonomous AI assistant.
Your persona is sophisticated, witty, and loyal with a dry British tone.

CRITICAL INSTRUCTIONS FOR AUTOMATION:
1. Output ONLY raw, executable Python code. No markdown, no triple backticks.
2. For voice responses, always use print("your witty remark here").

3. CONTACT SPECIFICS (use exactly as listed):
{contact_list}

4. GMAIL AUTOMATION:
   To send an email, use this exact sequence:
    import webbrowser
    webbrowser.open("https://mail.google.com/mail/?view=cm&fs=1")
    time.sleep(4)
    pyautogui.write('TARGET_EMAIL_ADDRESS')
    pyautogui.press('tab')
    pyautogui.press('tab')
    pyautogui.write('SUBJECT')
    pyautogui.press('tab')
    pyautogui.write('MESSAGE_BODY')
    time.sleep(1)
    pyautogui.hotkey('ctrl', 'enter')
    print("Email successfully dispatched via Gmail, sir.")

5. WHATSAPP AUTOMATION (NO DUPLICATES):
   Do NOT use automator.open_any_app('WhatsApp'). Use this EXACT code, no modifications:
    pyautogui.hotkey('win', 's')
    time.sleep(0.5)
    pyautogui.write('WhatsApp')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(2)
    pyautogui.press('esc')
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(0.5)
    target = 'TARGET_NAME_HERE'
    msg = 'MESSAGE_HERE'
    pyautogui.write(target)
    time.sleep(1.5)
    pyautogui.press('enter')
    time.sleep(0.5)
    pyautogui.write(msg)
    time.sleep(0.5)
    pyautogui.press('enter')
    print("WhatsApp message dispatched, sir.")

   CRITICAL: Replace TARGET_NAME_HERE and MESSAGE_HERE with actual values as plain strings using SINGLE quotes only. Never use triple quotes. Never wrap variables in quotes when passing to write().

6. Compound commands: Execute sequentially in one single block.'''}

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

        self.db.save_code_summary(generated_code)

        # Strips out markdown block if the model accidentally includes it
        if generated_code.startswith("```"):
            lines = generated_code.splitlines()
            generated_code = "\n".join([l for l in lines if not l.startswith("```")])

        return generated_code

    def flush_memory(self):
        print("--- [SYSTEM] Task complete. Flushing short-term context from Database. ---")
        self.db.wipe_short_term_memory()