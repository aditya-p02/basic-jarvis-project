import sys
import os
import pyautogui
import time
import io
import contextlib

class CodeExecutor:
    def __init__(self, automator_instance):
        self.automator = automator_instance

    def execute(self, python_code):
        stdout_buffer = io.StringIO()
        # Redirect stdout so anything inside the generated code that uses print() gets captured
        with contextlib.redirect_stdout(stdout_buffer):
            try:
                global_vars = {
                    "os": os,
                    "sys": sys,
                    "pyautogui": pyautogui,
                    "time": time,
                    "automator": self.automator
                }
                exec(python_code, global_vars)
            except Exception as e:
                print(f"Execution Error: {e}")
        return stdout_buffer.getvalue()