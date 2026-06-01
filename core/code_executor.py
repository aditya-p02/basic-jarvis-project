import sys
import os
import pyautogui
import time
import io
import contextlib
import webbrowser

class CodeExecutor:
    def __init__(self, automator_instance):
        self.automator = automator_instance

    def execute(self, python_code):
        # Block dangerous patterns before exec runs
        banned = [
    "import os",
    "import sys",
    "import subprocess",
    "import shutil",
    "os.system",
    "os.remove",
    "os.rmdir",
    "os.unlink",
    "shutil.rmtree",
    "subprocess.run",
    "subprocess.call",
    "subprocess.Popen",
    "eval(",
    "compile(",
    "socket.socket",
]
        for pattern in banned:
            if pattern in python_code:
                return f"Blocked: forbidden pattern '{pattern}' detected in generated code."

        # Strip import lines — these modules are already injected via safe_globals
        cleaned_code = "\n".join(
            line for line in python_code.splitlines()
            if not line.strip().startswith("import ") and not line.strip().startswith("from ")
        )

        stdout_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer):
            try:
                safe_globals = {
                    "__builtins__": {
                        "print": print,
                        "range": range,
                        "len": len,
                        "int": int,
                        "str": str,
                        "float": float,
                        "bool": bool,
                        "list": list,
                        "dict": dict,
                        "True": True,
                        "False": False,
                        "None": None,
                    },
                    "pyautogui": pyautogui,
                    "time": time,
                    "automator": self.automator,
                    "webbrowser": webbrowser,
                }
                exec(cleaned_code, safe_globals)
            except Exception as e:
                print(f"Execution Error: {e}")
        return stdout_buffer.getvalue()