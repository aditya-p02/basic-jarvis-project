import os
from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QApplication
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView

class JarvisHUD(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Transparent, frameless window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(600, 650)
        self.center_on_screen()
        
        self.drag_position = None

        # Frosted glass background panel
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(10, 15, 30, 210);
                border-radius: 20px;
                border: 1px solid rgba(0, 200, 255, 60);
            }
        """)
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignCenter)

        # UI Text Labels
        self.title_label = QLabel("J.A.R.V.I.S. CORE v8.0", self)
        self.title_label.setFont(QFont("Consolas", 16, QFont.Bold))
        self.title_label.setStyleSheet("color: rgba(0, 200, 255, 255); background: transparent; border: none;")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        self.status_label = QLabel("STANDBY", self)
        self.status_label.setFont(QFont("Consolas", 14))
        self.status_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.action_label = QLabel("", self)
        self.action_label.setFont(QFont("Consolas", 11, QFont.Bold))
        self.action_label.setStyleSheet("color: rgba(255, 255, 255, 150); background: transparent; border: none;")
        self.action_label.setAlignment(Qt.AlignCenter)

        # ==========================================
        # 3D WEB ENGINE INJECTION
        # ==========================================
        self.web_view = QWebEngineView()
        # Ensure the web view itself is fully transparent
        self.web_view.setStyleSheet("background: transparent; border: none;")
        self.web_view.setAttribute(Qt.WA_TranslucentBackground)
        self.web_view.page().setBackgroundColor(Qt.transparent)
        
        # Point it to the local 3D HTML file we just created
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(base_dir, "web", "index.html")
        self.web_view.setUrl(QUrl.fromLocalFile(html_path))
        
        # Add elements to layout
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.web_view, 1) # The '1' gives the 3D core max stretch space
        self.layout.addWidget(self.action_label)

    # Allow dragging the frameless window
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            
    def mouseReleaseEvent(self, event):
        self.drag_position = None

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = int((screen.width() - self.width()) / 2)
        y = int((screen.height() - self.height()) / 2)
        self.move(x, y)

    def update_status(self, text):
        self.status_label.setText(text)
        # CRITICAL: This is where Python talks to Javascript to trigger the 3D animations!
        js_code = f"window.setJarvisState('{text.upper()}');"
        self.web_view.page().runJavaScript(js_code)

    def update_action(self, text):
        self.action_label.setText(text)