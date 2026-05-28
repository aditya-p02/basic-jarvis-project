import math
import random
from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

class NervousSystemWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.num_nodes = 45 
        self.time = 0.0
        self.state_color = QColor(0, 255, 204) # Default Cyan
        
        for _ in range(self.num_nodes):
            x = random.uniform(50, 550)
            y = random.uniform(50, 550)
            phase = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.05, 0.12)
            self.nodes.append({'x': x, 'y': y, 'base_x': x, 'base_y': y, 'phase': phase, 'speed': speed})
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)

    def update_animation(self):
        self.time += 1.0
        for node in self.nodes:
            node['x'] = node['base_x'] + math.sin(self.time * node['speed'] + node['phase']) * 20
            node['y'] = node['base_y'] + math.cos(self.time * node['speed'] + node['phase']) * 20
        self.update() 

    def set_state(self, state_text):
        text = state_text.upper()
        if "LISTENING" in text:
            self.state_color = QColor(255, 0, 127) # Neon Pink
        elif "THINKING" in text or "EXECUTING" in text:
            self.state_color = QColor(255, 215, 0) # Gold
        elif "RESPONDING" in text:
            self.state_color = QColor(57, 255, 20) # Neon Green
        else:
            self.state_color = QColor(0, 255, 204) # Cyan

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen()
        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                n1 = self.nodes[i]
                n2 = self.nodes[j]
                
                dist = math.hypot(n1['x'] - n2['x'], n1['y'] - n2['y'])
                
                if dist < 120: 
                    opacity = int(255 * (1 - dist / 120))
                    c = QColor(self.state_color)
                    c.setAlpha(opacity)
                    pen.setColor(c)
                    pen.setWidthF(1.5)
                    painter.setPen(pen)
                    painter.drawLine(int(n1['x']), int(n1['y']), int(n2['x']), int(n2['y']))
                    
        painter.setPen(Qt.NoPen)
        for node in self.nodes:
            c = QColor(self.state_color)
            alpha = int(150 + 100 * math.sin(self.time * node['speed'] * 2 + node['phase']))
            c.setAlpha(max(0, min(255, alpha)))
            painter.setBrush(c)
            painter.drawEllipse(int(node['x'] - 4), int(node['y'] - 4), 8, 8)

class JarvisHUD(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(600, 600)
        self.center_on_screen()

        self.central_widget = NervousSystemWidget()
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel("GESTURE OS // JARVIS", self)
        self.title_label.setFont(QFont("Consolas", 18, QFont.Bold))
        self.title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        self.status_label = QLabel("STANDBY", self)
        self.status_label.setFont(QFont("Consolas", 14))
        self.status_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.action_label = QLabel("", self)
        self.action_label.setFont(QFont("Consolas", 12, QFont.Bold))
        self.action_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.action_label.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.action_label)

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = int((screen.width() - self.width()) / 2)
        y = int((screen.height() - self.height()) / 2)
        self.move(x, y)

    def update_status(self, text):
        self.status_label.setText(text)
        self.central_widget.set_state(text)

    def update_action(self, text):
        self.action_label.setText(text)