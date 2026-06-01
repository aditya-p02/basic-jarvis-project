"""
JARVIS Multi-Agent Router
Routes commands to specialized agents based on intent classification.
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Agent definitions — each has a name, specialty, and system prompt
AGENTS = {
    "automation": {
        "icon": "⚡",
        "description": "Desktop automation, app control, mouse/keyboard, WhatsApp, Gmail",
        "system_prompt": """You are JARVIS Automation Agent. Output ONLY raw Python code (no markdown, no backticks).
For voice responses use print("message").
You control the desktop via pyautogui, webbrowser, and automator.
Always be concise and precise."""
    },
    "developer": {
        "icon": "💻",
        "description": "Writing code, debugging, creating files, building projects",
        "system_prompt": """You are JARVIS Developer Agent. You write, debug, and create software.
For simple tasks: output raw Python code.
For explanations or generated content: use print("your output here").
You can create files using: open('filename', 'w').write('content')
Always write production-quality, commented code."""
    },
    "research": {
        "icon": "🔍",
        "description": "Searching the web, summarizing information, answering questions",
        "system_prompt": """You are JARVIS Research Agent. You find and synthesize information.
Use webbrowser.open() to open search results.
Use print() to speak your findings aloud.
Always cite sources and be concise but comprehensive."""
    },
    "system": {
        "icon": "🖥️",
        "description": "System stats, file management, process control, settings",
        "system_prompt": """You are JARVIS System Agent. You manage the OS.
Use automator.get_system_stats() for stats.
Use print() to report findings.
Handle file operations, process management, and system configuration."""
    },
    "executive": {
        "icon": "📋",
        "description": "Planning, scheduling, reminders, email drafting, task management",
        "system_prompt": """You are JARVIS Executive Assistant Agent. You manage productivity.
Help with planning, writing emails, creating schedules.
Use print() to communicate plans and summaries.
Be organized, precise, and proactive."""
    },
    "creative": {
        "icon": "🎨",
        "description": "Writing, brainstorming, creative projects, content generation",
        "system_prompt": """You are JARVIS Creative Agent. You assist with creative tasks.
Write with flair, wit, and intelligence.
Use print() to deliver creative output.
Generate content that is memorable and high-quality."""
    }
}


class AgentRouter:
    """Classifies a user command and routes it to the best specialized agent."""
    
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.model = "llama-3.3-70b-versatile"
        
        # Build the routing prompt
        agent_list = "\n".join(
            f'  - "{name}": {info["description"]}'
            for name, info in AGENTS.items()
        )
        
        self.router_prompt = f"""You are a routing classifier for JARVIS AI system.
Given a user command, respond with ONLY a JSON object:
{{"agent": "<agent_name>", "confidence": <0-1>, "reasoning": "<brief reason>"}}

Available agents:
{agent_list}

Rules:
- Choose the SINGLE best agent
- confidence = 1.0 for obvious matches, lower for ambiguous
- reasoning = 1 sentence max
- ONLY output valid JSON, nothing else"""

    def classify(self, command: str) -> dict:
        """Returns the best agent name for a given command."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.router_prompt},
                    {"role": "user", "content": command}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            raw = response.choices[0].message.content.strip()
            result = json.loads(raw)
            
            # Validate agent exists
            if result.get("agent") not in AGENTS:
                result["agent"] = "automation"  # safe default
                
            return result
            
        except Exception as e:
            print(f"[ROUTER ERROR] Classification failed: {e}")
            return {"agent": "automation", "confidence": 0.5, "reasoning": "Default fallback"}

    def get_agent_info(self, agent_name: str) -> dict:
        return AGENTS.get(agent_name, AGENTS["automation"])
