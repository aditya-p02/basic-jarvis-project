"""
JARVIS Screen Vision Engine
Captures and analyzes the desktop state using Groq Vision.
"""
import os
import base64
import time
from datetime import datetime

try:
    import mss
    import mss.tools
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    print("[VISION] mss not installed. Run: pip install mss")

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ScreenVision:
    """
    Captures screenshots and analyzes them with a vision LLM.
    Provides JARVIS with awareness of the current desktop state.
    """
    
    def __init__(self, vision_client=None, vision_model: str = None):
        self.client = vision_client
        self.vision_model = vision_model or "meta-llama/llama-4-scout-17b-16e-instruct"
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.screenshot_dir = os.path.join(base_dir, "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        self.last_screenshot_path = None
        self.last_analysis = None
        self.last_analysis_time = 0
        self.ANALYSIS_CACHE_SECONDS = 5  # Don't re-analyze if asked again within 5s

    def capture(self, region: dict = None) -> str:
        """
        Capture a screenshot. Returns file path.
        region: optional dict with keys 'top', 'left', 'width', 'height'
        """
        if not MSS_AVAILABLE:
            return None
        
        timestamp = datetime.now().strftime("%H%M%S_%f")
        filename = f"screen_{timestamp}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        
        try:
            with mss.mss() as sct:
                if region:
                    shot = sct.grab(region)
                else:
                    # Capture primary monitor
                    monitor = sct.monitors[1]
                    shot = sct.grab(monitor)
                
                mss.tools.to_png(shot.rgb, shot.size, output=filepath)
            
            self.last_screenshot_path = filepath
            return filepath
            
        except Exception as e:
            print(f"[SCREEN VISION ERROR] Capture failed: {e}")
            return None

    def capture_and_compress(self, max_width: int = 1280) -> str:
        """Capture and compress screenshot for faster API upload."""
        filepath = self.capture()
        if not filepath or not PIL_AVAILABLE:
            return filepath
        
        try:
            with Image.open(filepath) as img:
                # Resize if too large
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.LANCZOS)
                
                # Save compressed
                compressed_path = filepath.replace(".png", "_compressed.jpg")
                img.save(compressed_path, "JPEG", quality=75)
                
                # Clean up original
                os.remove(filepath)
                self.last_screenshot_path = compressed_path
                return compressed_path
                
        except Exception as e:
            print(f"[SCREEN VISION] Compression failed, using original: {e}")
            return filepath

    def analyze(self, question: str = None) -> str:
        """
        Capture screen and analyze with vision LLM.
        question: specific question to ask about the screen (optional)
        """
        # Check cache
        if (self.last_analysis and 
            time.time() - self.last_analysis_time < self.ANALYSIS_CACHE_SECONDS and
            not question):
            return self.last_analysis
        
        if not self.client:
            return "Screen vision client not configured."
        
        filepath = self.capture_and_compress()
        if not filepath:
            return "Screenshot capture failed — mss library required."
        
        try:
            with open(filepath, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            ext = filepath.split(".")[-1].lower()
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
            
            prompt = question or (
                "Describe this screen comprehensively: "
                "What applications are open? What is the active window? "
                "What text, buttons, or UI elements are visible? "
                "What is the user currently doing? Be specific and detailed."
            )
            
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{image_data}"}
                        },
                        {"type": "text", "text": prompt}
                    ]
                }],
                max_tokens=600
            )
            
            analysis = response.choices[0].message.content
            self.last_analysis = analysis
            self.last_analysis_time = time.time()
            
            # Clean up screenshot
            try:
                os.remove(filepath)
            except Exception:
                pass
            
            return analysis
            
        except Exception as e:
            return f"Screen analysis error: {e}"

    def is_app_open(self, app_name: str) -> bool:
        """Check if a specific app appears to be open on screen."""
        analysis = self.analyze(f"Is '{app_name}' currently visible or open on this screen? Answer yes or no.")
        return "yes" in analysis.lower()

    def read_text_from_screen(self) -> str:
        """Extract all readable text from the current screen."""
        return self.analyze(
            "Extract and list ALL text visible on this screen, "
            "preserving the structure. Include window titles, "
            "menu items, body text, and any other readable content."
        )

    def describe_for_agent(self) -> str:
        """
        Get a concise screen description formatted for agent injection.
        Used to give JARVIS context about the current desktop state.
        """
        analysis = self.analyze()
        if analysis and len(analysis) > 500:
            # Truncate for token efficiency
            return analysis[:500] + "... [truncated]"
        return analysis or "Screen state unavailable."
