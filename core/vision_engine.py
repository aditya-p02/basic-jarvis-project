import cv2
import mediapipe as mp
import pyautogui
import math
import os
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

# Permanently disable the corner crash in the camera thread
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
        self.smooth_alpha = 0.25 
        
        model_path = 'hand_landmarker.task'
        self.options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.7
        )

    def run(self):
        cap = cv2.VideoCapture(0)
        
        with HandLandmarker.create_from_options(self.options) as landmarker:
            while self.running and cap.isOpened():
                success, frame = cap.read()
                if not success: continue
                    
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
                        
                        index_pip = hand_landmarks[6]
                        middle_pip = hand_landmarks[10]
                        ring_pip = hand_landmarks[14]
                        pinky_pip = hand_landmarks[18]
                        
                        cam_x, cam_y = index_tip.x, index_tip.y
                        scaled_x = np.interp(cam_x, [0.2, 0.8], [0, self.screen_w])
                        scaled_y = np.interp(cam_y, [0.2, 0.8], [0, self.screen_h])
                        
                        curr_x = self.prev_x + (scaled_x - self.prev_x) * self.smooth_alpha
                        curr_y = self.prev_y + (scaled_y - self.prev_y) * self.smooth_alpha
                        
                        pyautogui.moveTo(curr_x, curr_y, _pause=False)
                        self.prev_x, self.prev_y = curr_x, curr_y
                        
                        # --- GESTURES ---
                        if math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y) < 0.05:
                            pyautogui.click()
                            self.gesture_signal.emit("LEFT CLICK")
                            pyautogui.sleep(0.3) 
                            
                        elif math.hypot(middle_tip.x - thumb_tip.x, middle_tip.y - thumb_tip.y) < 0.05:
                            pyautogui.rightClick()
                            self.gesture_signal.emit("RIGHT CLICK")
                            pyautogui.sleep(0.3)

                        elif math.hypot(pinky_tip.x - thumb_tip.x, pinky_tip.y - thumb_tip.y) < 0.05:
                            pyautogui.hotkey('alt', 'tab')
                            self.gesture_signal.emit("SWITCH TAB")
                            pyautogui.sleep(0.5) 
                            
                        elif math.hypot(ring_tip.x - thumb_tip.x, ring_tip.y - thumb_tip.y) < 0.05:
                            pyautogui.press('volumemute')
                            self.gesture_signal.emit("MUTE AUDIO")
                            pyautogui.sleep(0.5)

                        elif (index_tip.y < index_pip.y and middle_tip.y < middle_pip.y and 
                              ring_tip.y > ring_pip.y and pinky_tip.y > pinky_pip.y):
                            y_movement = curr_y - self.prev_y
                            if y_movement < -3:
                                pyautogui.scroll(150)
                                self.gesture_signal.emit("SCROLLING UP")
                            elif y_movement > 3:
                                pyautogui.scroll(-150)
                                self.gesture_signal.emit("SCROLLING DOWN")
                                
                        elif (index_tip.y > index_pip.y and middle_tip.y > middle_pip.y and 
                              ring_tip.y > ring_pip.y and pinky_tip.y > pinky_pip.y):
                            pyautogui.press('playpause')
                            self.gesture_signal.emit("PLAY / PAUSE")
                            pyautogui.sleep(1.0)
                            
        cap.release()

    def stop(self):
        self.running = False