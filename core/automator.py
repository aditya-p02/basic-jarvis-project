import os
import pyautogui
import psutil
from datetime import datetime
from AppOpener import open as open_app, close as close_app

class Automator:
    def __init__(self):
        pyautogui.FAILSAFE = False

    def get_system_stats(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        plugged = "PLUGGED IN" if battery and battery.power_plugged else "ON BATTERY"
        batt_percent = battery.percent if battery else 100
        return f"CPU: {cpu}% | RAM: {ram}% | {plugged}: {batt_percent}%"

    def execute_command(self, cmd_type, value=None):
        if cmd_type == "screenshot":
            ts = datetime.now().strftime("%H%M%S")
            pyautogui.screenshot(f"capture_{ts}.png")

    def open_any_app(self, app_name):
        try:
            open_app(app_name, match_closest=True)
            print(f"[AUTOMATOR] Opened '{app_name}' successfully.")
            return True
        except Exception as e:
            print(f"[AUTOMATOR ERROR] Failed to open '{app_name}': {e}")
            return False

    def close_any_app(self, app_name):
        try:
            close_app(app_name, match_closest=True)
            print(f"[AUTOMATOR] Closed '{app_name}' successfully.")
            return True
        except Exception as e:
            print(f"[AUTOMATOR ERROR] Failed to close '{app_name}': {e}")
            return False