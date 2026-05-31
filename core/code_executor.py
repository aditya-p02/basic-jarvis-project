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
            "import os", "import sys", "import subprocess",
            "import shutil", "open(",
            "eval(", "compile(", "exec(",
            "os.system", "os.remove", "os.rmdir",
            "shutil.rmtree", "subprocess", "socket",
        ]
        for pattern in banned:
            if pattern in python_code:
                return f"Blocked: forbidden pattern '{pattern}' detected in generated code."

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
                exec(python_code, safe_globals)
            except Exception as e:
                print(f"Execution Error: {e}")
        return stdout_buffer.getvalue()