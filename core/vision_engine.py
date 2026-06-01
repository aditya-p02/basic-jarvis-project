import cv2
import mediapipe as mp
import pyautogui
import math
import numpy as np
import time
from PyQt5.QtCore import QThread, pyqtSignal

pyautogui.FAILSAFE = False

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

class VisionEngine(QThread):
    gesture_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.screen_w, self.screen_h = pyautogui.size()
        self.running = True

        self.prev_x, self.prev_y = 0, 0
        self.drag_active = False

        self.swipe_start_x = None
        self.swipe_start_time = 0
        self.last_swipe_time = 0
        self.scroll_prev_y = None
        self.drag_cooldown = 0
        self.prev_pinky_only = False
        self.prev_index_pinky = False
        
        # Cooldown for left click so it doesn't spam
        self.last_left_click_time = 0 

        # --- CLOSED FIST DRAG STATE ---
        self.fist_hold_start = None
        self.FIST_CONFIRM_SECONDS = 0.18   
        self.fist_release_frames = 0        
        self.FIST_RELEASE_DEBOUNCE = 6      

        # Palm unlock state
        self.gestures_active = False
        self.palm_hold_start = None
        self.hand_lost_time = None        
        self.HAND_TIMEOUT = 10.0          

        model_path = 'hand_landmarker.task'
        self.options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.85
        )

    def run(self):
        cap = cv2.VideoCapture(0)
        frame_count = 0
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        with HandLandmarker.create_from_options(self.options) as landmarker:
            while self.running and cap.isOpened():
                success, frame = cap.read()
                if not success:
                    continue

                frame = cv2.flip(frame, 1)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                frame_count += 1
                timestamp_ms = int(frame_count * (1000.0 / fps))

                detection_result = landmarker.detect_for_video(mp_image, timestamp_ms)

                hand_detected = bool(detection_result.hand_landmarks)

                # ==========================================
                # HAND PRESENCE LOGIC
                # ==========================================
                if hand_detected:
                    self.hand_lost_time = None
                else:
                    if self.gestures_active:
                        if self.hand_lost_time is None:
                            self.hand_lost_time = time.time()
                        else:
                            gone_for = time.time() - self.hand_lost_time
                            remaining = self.HAND_TIMEOUT - gone_for
                            if remaining > 0:
                                self.gesture_signal.emit(f"HAND AWAY: {int(remaining) + 1}s")
                            else:
                                self.gestures_active = False
                                self.hand_lost_time = None
                                self.palm_hold_start = None
                                self.gesture_signal.emit("GESTURES OFF")
                    continue

                for hand_landmarks in detection_result.hand_landmarks:
                    thumb_tip = hand_landmarks[4]
                    index_tip = hand_landmarks[8]
                    middle_tip = hand_landmarks[12]
                    ring_tip = hand_landmarks[16]
                    pinky_tip = hand_landmarks[20]

                    index_knuckle = hand_landmarks[5]

                    index_pip = hand_landmarks[6]
                    middle_pip = hand_landmarks[10]
                    ring_pip = hand_landmarks[14]
                    pinky_pip = hand_landmarks[18]
                    wrist = hand_landmarks[0]

                    index_up = index_tip.y < index_pip.y
                    middle_up = middle_tip.y < middle_pip.y
                    ring_up = ring_tip.y < ring_pip.y
                    pinky_up = pinky_tip.y < pinky_pip.y

                    # ==========================================
                    # PALM HOLD TO ACTIVATE (5 seconds)
                    # ==========================================
                    if not self.gestures_active:
                        all_up = index_up and middle_up and ring_up and pinky_up
                        if all_up:
                            if self.palm_hold_start is None:
                                self.palm_hold_start = time.time()
                            else:
                                held = time.time() - self.palm_hold_start
                                remaining = 5.0 - held
                                if remaining > 0:
                                    self.gesture_signal.emit(f"PALM HOLD: {int(remaining) + 1}s")
                                else:
                                    self.gestures_active = True
                                    self.palm_hold_start = None
                                    self.hand_lost_time = None
                                    self.gesture_signal.emit("GESTURES ON")
                        else:
                            self.palm_hold_start = None
                        continue

                    # ==========================================
                    # 1. THE KNUCKLE ANCHOR CURSOR
                    # ==========================================
                    cam_x, cam_y = index_knuckle.x, index_knuckle.y

                    scaled_x = np.interp(cam_x, [0.2, 0.8], [0, self.screen_w])
                    scaled_y = np.interp(cam_y, [0.25, 0.85], [0, self.screen_h])

                    smooth_factor = 0.15
                    target_x = self.prev_x + (scaled_x - self.prev_x) * smooth_factor
                    target_y = self.prev_y + (scaled_y - self.prev_y) * smooth_factor

                    if math.hypot(target_x - self.prev_x, target_y - self.prev_y) > 1.5:
                        curr_x, curr_y = target_x, target_y
                        pyautogui.moveTo(int(curr_x), int(curr_y), _pause=False)
                        self.prev_x, self.prev_y = curr_x, curr_y
                    else:
                        curr_x, curr_y = self.prev_x, self.prev_y

                    # ==========================================
                    # 2. UPGRADED MACROS & GESTURES
                    # ==========================================

                    # ==========================================
                    # CLOSED FIST DRAG & DROP
                    # ==========================================
                    index_mcp = hand_landmarks[5]
                    middle_mcp = hand_landmarks[9]
                    ring_mcp   = hand_landmarks[13]
                    pinky_mcp  = hand_landmarks[17]

                    index_curled  = index_tip.y  > index_mcp.y
                    middle_curled = middle_tip.y > middle_mcp.y
                    ring_curled   = ring_tip.y   > ring_mcp.y
                    pinky_curled  = pinky_tip.y  > pinky_mcp.y

                    is_fist = index_curled and middle_curled and ring_curled and pinky_curled

                    if not self.drag_active:
                        if is_fist:
                            if self.fist_hold_start is None:
                                self.fist_hold_start = time.time()
                            elif time.time() - self.fist_hold_start >= self.FIST_CONFIRM_SECONDS:
                                pyautogui.mouseDown(_pause=False)
                                self.drag_active = True
                                self.fist_hold_start = None
                                self.fist_release_frames = 0
                                self.gesture_signal.emit(" GRAB — DRAG ENGAGED")
                        else:
                            self.fist_hold_start = None
                    else:
                        if is_fist:
                            self.fist_release_frames = 0
                        else:
                            self.fist_release_frames += 1
                            if self.fist_release_frames >= self.FIST_RELEASE_DEBOUNCE:
                                pyautogui.mouseUp(_pause=False)
                                self.drag_active = False
                                self.fist_hold_start = None
                                self.fist_release_frames = 0
                                self.gesture_signal.emit(" RELEASE — DRAG DROPPED")

                    # --- LEFT CLICK (thumb + index pinch) ---
                    # Only fires when NOT dragging and hand is not in a fist
                    dist_thumb_index = math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y)
                    if dist_thumb_index < 0.04 and not self.drag_active and not is_fist:
                        current_time = time.time()
                        if current_time - self.last_left_click_time > 0.4:
                            pyautogui.click(_pause=False)
                            self.gesture_signal.emit("LEFT CLICK")
                            self.last_left_click_time = current_time

                    # --- RIGHT CLICK (thumb + middle pinch, index finger up) ---
                    dist_thumb_middle = math.hypot(middle_tip.x - thumb_tip.x, middle_tip.y - thumb_tip.y)
                    if dist_thumb_middle < 0.04 and index_up and not self.drag_active and not is_fist:
                        pyautogui.rightClick(_pause=False)
                        self.gesture_signal.emit("RIGHT CLICK")
                        pyautogui.sleep(0.4)

                    # --- INDEPENDENT SCROLL (2 fingers up, no fist, no drag) ---
                    elif index_up and middle_up and not ring_up and not pinky_up and not self.drag_active and not is_fist:
                        if self.scroll_prev_y is None:
                            self.scroll_prev_y = scaled_y
                        else:
                            delta_y = scaled_y - self.scroll_prev_y
                            if delta_y < -15:
                                pyautogui.scroll(120)
                                self.gesture_signal.emit("SCROLL UP")
                                self.scroll_prev_y = scaled_y
                            elif delta_y > 15:
                                pyautogui.scroll(-120)
                                self.gesture_signal.emit("SCROLL DOWN")
                                self.scroll_prev_y = scaled_y
                    else:
                        self.scroll_prev_y = None

                    # --- ACCUMULATIVE SWIPE (all 4 fingers up, open palm, no drag) ---
                    if index_up and middle_up and ring_up and pinky_up and not self.drag_active and not is_fist:
                        current_time = time.time()

                        if self.swipe_start_x is None:
                            self.swipe_start_x = wrist.x
                            self.swipe_start_time = current_time
                        else:
                            time_elapsed = current_time - self.swipe_start_time
                            if time_elapsed < 0.4:
                                delta_x = wrist.x - self.swipe_start_x
                                if current_time - self.last_swipe_time > 0.8:
                                    if delta_x > 0.12:
                                        pyautogui.hotkey('alt', 'right')
                                        self.gesture_signal.emit("SWIPE FORWARD")
                                        self.last_swipe_time = current_time
                                        self.swipe_start_x = None
                                    elif delta_x < -0.12:
                                        pyautogui.hotkey('alt', 'left')
                                        self.gesture_signal.emit("SWIPE BACK")
                                        self.last_swipe_time = current_time
                                        self.swipe_start_x = None
                            else:
                                self.swipe_start_x = wrist.x
                                self.swipe_start_time = current_time

                    else:
                        self.swipe_start_x = None

                        # --- MISC MACROS ---
                        pinky_only = pinky_up and not index_up and not middle_up and not ring_up
                        index_pinky = index_up and pinky_up and not middle_up and not ring_up

                        if pinky_only and not self.prev_pinky_only:
                            pyautogui.hotkey('alt', 'tab')
                            self.gesture_signal.emit("SWITCH WINDOW")

                        elif index_pinky and not self.prev_index_pinky:
                            pyautogui.hotkey('ctrl', 'w')
                            self.gesture_signal.emit("CLOSE ACTIVE TAB")

                        self.prev_pinky_only = pinky_only
                        self.prev_index_pinky = index_pinky

        cap.release()

    def stop(self):
        self.running = False