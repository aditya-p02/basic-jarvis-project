"""
JARVIS Agent Brain v2 — Multi-Agent Edition
- Routes to specialized agents
- Persistent long-term memory (no wipe after tasks)
- Preference learning
- Screen context injection
"""
import os
import sys
import json
import base64
from openai import OpenAI
from dotenv import load_dotenv
from core.database import DatabaseManager
from agents.router import AgentRouter, AGENTS

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, ".env"))


class AgentBrain:
    def __init__(self):
        self.db = DatabaseManager()
        self.router = AgentRouter()
        
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.model_name = "llama-3.3-70b-versatile"
        self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"  # Groq vision

        # Load contacts
        contacts_path = os.path.join(base_dir, "contacts.json")
        with open(contacts_path, "r") as f:
            self.contacts = json.load(f)

        contact_list = "\n".join(
            f"   - '{k.title()}' -> WhatsApp name: '{v['whatsapp_name']}'"
            for k, v in self.contacts.items()
        )

        # Load user preferences (persistent learning)
        self.prefs_path = os.path.join(base_dir, "user_preferences.json")
        self.preferences = self._load_preferences()
        
        # Shared context injected into every agent
        self.shared_context = f"""
CONTACT LIST:
{contact_list}

WHATSAPP AUTOMATION (use this EXACT sequence):
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

GMAIL AUTOMATION:
    import webbrowser
    webbrowser.open("https://mail.google.com/mail/?view=cm&fs=1")
    time.sleep(4)
    pyautogui.write('TARGET_EMAIL')
    pyautogui.press('tab')
    pyautogui.press('tab')
    pyautogui.write('SUBJECT')
    pyautogui.press('tab')
    pyautogui.write('MESSAGE')
    time.sleep(1)
    pyautogui.hotkey('ctrl', 'enter')
    print("Email dispatched, sir.")

RULES:
- Output ONLY raw executable Python. No markdown, no backticks.
- Use print() for voice responses.
- Use single quotes only in strings.
"""

        # Build per-agent system prompts
        self.agent_prompts = {}
        for agent_name, agent_info in AGENTS.items():
            self.agent_prompts[agent_name] = {
                "role": "system",
                "content": agent_info["system_prompt"] + "\n\n" + self.shared_context
            }

        # Active agent tracking (for HUD)
        self.active_agent = "automation"
        self.last_routing_result = {}

    def _load_preferences(self) -> dict:
        """Load persistent user preferences from disk."""
        if os.path.exists(self.prefs_path):
            with open(self.prefs_path, "r") as f:
                return json.load(f)
        return {
            "name": "sir",
            "tone": "formal",
            "frequent_apps": [],
            "frequent_contacts": [],
            "work_hours": "9-18",
            "learned_facts": []
        }

    def _save_preferences(self):
        """Persist preferences to disk."""
        with open(self.prefs_path, "w") as f:
            json.dump(self.preferences, f, indent=2)

    def analyze_screen(self, screenshot_path: str) -> str:
        """Use Groq vision to describe the current screen state."""
        try:
            with open(screenshot_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Describe what is visible on this screen in detail. List all visible windows, content, buttons, and text you can see. Be precise and comprehensive."
                        }
                    ]
                }],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Screen analysis unavailable: {e}"

    def think(self, user_command: str, screen_context: str = None) -> tuple[str, str]:
        """
        Main thinking function. Returns (generated_code, active_agent_name).
        Now routes to the best specialized agent.
        """
        # 1. Route to best agent
        routing = self.router.classify(user_command)
        self.active_agent = routing["agent"]
        self.last_routing_result = routing
        
        agent_info = AGENTS[self.active_agent]
        print(f"\n[ROUTER] → {agent_info['icon']} {self.active_agent.upper()} Agent "
              f"(confidence: {routing['confidence']:.0%}) — {routing['reasoning']}")
        
        # 2. Save user message to persistent memory
        self.db.save_message("user", user_command)
        
        # 3. Build context: semantic search for relevant past memories
        relevant_memories = self.db.search_relevant_memories(user_command, limit=5)
        
        # 4. Build message list with memory injection
        messages = [self.agent_prompts[self.active_agent]]
        
        # Inject relevant past memories as context
        if relevant_memories:
            memory_block = "RELEVANT PAST CONTEXT:\n" + "\n".join(
                f"  - {m['role'].upper()}: {m['content']}" 
                for m in relevant_memories
            )
            messages.append({"role": "system", "content": memory_block})
        
        # Inject user preferences
        if self.preferences.get("learned_facts"):
            facts = "\n".join(f"  - {f}" for f in self.preferences["learned_facts"][-10:])
            messages.append({"role": "system", "content": f"KNOWN USER PREFERENCES:\n{facts}"})
        
        # Inject screen context if provided
        if screen_context:
            messages.append({
                "role": "system",
                "content": f"CURRENT SCREEN STATE:\n{screen_context}"
            })
        
        # Add recent conversation context
        messages += self.db.get_recent_context(limit=6)
        
        # Add the user's command
        messages.append({"role": "user", "content": user_command})
        
        # 5. Stream the response
        print(f"\n--- [{self.active_agent.upper()} AGENT STREAMING] ---")
        generated_code = ""
        
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content is not None:
                    token = delta.content
                    sys.stdout.write(token)
                    sys.stdout.flush()
                    generated_code += token
        
        print("\n" + "-" * 40 + "\n")
        
        # 6. Save to persistent memory (NO WIPE)
        self.db.save_code_summary(generated_code)
        
        # 7. Strip accidental markdown
        if generated_code.strip().startswith("```"):
            lines = generated_code.splitlines()
            generated_code = "\n".join(l for l in lines if not l.strip().startswith("```"))
        
        # 8. Update preferences from this interaction (async-safe)
        self._learn_from_interaction(user_command)
        
        return generated_code, self.active_agent

    def _learn_from_interaction(self, command: str):
        """Lightweight preference learning — detects patterns in commands."""
        cmd_lower = command.lower()
        
        # Learn frequently contacted people
        for contact_name in self.contacts:
            if contact_name in cmd_lower:
                freq = self.preferences.get("frequent_contacts", [])
                if contact_name not in freq:
                    freq.append(contact_name)
                    self.preferences["frequent_contacts"] = freq[-10:]  # keep last 10
        
        self._save_preferences()

    def learn_fact(self, fact: str):
        """Explicitly teach JARVIS a new preference or fact."""
        facts = self.preferences.get("learned_facts", [])
        facts.append(fact)
        self.preferences["learned_facts"] = facts[-50:]  # keep last 50
        self._save_preferences()
        print(f"[MEMORY] Learned: {fact}")

    def flush_memory(self):
        """
        v2: Only flush SHORT-TERM context. Long-term memory persists.
        Call this only on explicit user request, not after every task.
        """
        print("--- [SYSTEM] Flushing short-term context only. Long-term memory preserved. ---")
        self.db.wipe_short_term_memory()

    def get_active_agent(self) -> str:
        return self.active_agent
    
    def get_routing_info(self) -> dict:
        return self.last_routing_result
