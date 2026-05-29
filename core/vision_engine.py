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
        
        model_path = 'hand_landmarker.task'
        self.options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.VIDEO,
            num_hands=1, 
            min_hand_detection_confidence=0.85 
        )

    def run(self):
        cap = cv2.VideoCapture(0)
        
        with HandLandmarker.create_from_options(self.options) as landmarker:
            while self.running and cap.isOpened():
                success, frame = cap.read()
                if not success: 
                    continue
                    
                frame = cv2.flip(frame, 1)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                timestamp_ms = max(1, int(cap.get(cv2.CAP_PROP_POS_MSEC)))

                detection_result = landmarker.detect_for_video(mp_image, timestamp_ms)
                
                if detection_result.hand_landmarks:
                    for hand_landmarks in detection_result.hand_landmarks:
                        thumb_tip = hand_landmarks[4]
                        index_tip = hand_landmarks[8]
                        middle_tip = hand_landmarks[12]
                        ring_tip = hand_landmarks[16]
                        pinky_tip = hand_landmarks[20]
                        
                        # THE FIX: Extract the base knuckle of the index finger
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
                        # 1. THE KNUCKLE ANCHOR CURSOR
                        # ==========================================
                        # We now use the knuckle for X/Y coordinates to prevent "Click Drift"
                        cam_x, cam_y = index_knuckle.x, index_knuckle.y
                        
                        # Adjusted bounds slightly so you don't have to raise your hand as high
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

                        # --- BULLETPROOF DRAG & DROP ---
                        dist_thumb_index = math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y)
                        
                        if not self.drag_active:
                            # Loosened to 0.05 and REMOVED the middle finger rule. 
                            # If they are close, just grab it!
                            if dist_thumb_index < 0.05:
                                pyautogui.mouseDown(_pause=False)
                                self.drag_active = True
                                self.gesture_signal.emit("DRAG ENGAGED")
                        else:
                            # Tightened to 0.06. Just relaxing your fingers slightly will drop the item.
                            if dist_thumb_index > 0.06:
                                pyautogui.mouseUp(_pause=False)
                                self.drag_active = False
                                self.gesture_signal.emit("DRAG RELEASED")

                        # --- RIGHT CLICK ---
                        dist_thumb_middle = math.hypot(middle_tip.x - thumb_tip.x, middle_tip.y - thumb_tip.y)
                        if dist_thumb_middle < 0.04 and index_up and not self.drag_active:
                            pyautogui.rightClick(_pause=False)
                            self.gesture_signal.emit("RIGHT CLICK")
                            pyautogui.sleep(0.4)

                        # --- INDEPENDENT SCROLL ---
                        elif index_up and middle_up and not ring_up and not pinky_up:
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

                        # --- ACCUMULATIVE SWIPE ---
                        if index_up and middle_up and ring_up and pinky_up:
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
                            if pinky_up and not index_up and not middle_up and not ring_up:
                                pyautogui.hotkey('alt', 'tab')
                                self.gesture_signal.emit("SWITCH WINDOW")
                                pyautogui.sleep(0.6)

                            elif index_up and middle_up and ring_up and not pinky_up:
                                pyautogui.hotkey('win', 'd')
                                self.gesture_signal.emit("SHOW DESKTOP")
                                pyautogui.sleep(0.7)

                            elif index_up and pinky_up and not middle_up and not ring_up:
                                pyautogui.hotkey('ctrl', 'w')
                                self.gesture_signal.emit("CLOSE ACTIVE TAB")
                                pyautogui.sleep(0.7)
                        
        cap.release()

    def stop(self):
        self.running = False