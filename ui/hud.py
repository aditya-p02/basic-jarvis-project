import os
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QApplication
from PyQt5.QtCore import Qt, QUrl, QPoint
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Custom Web View subclass to route mouse drags back to the main window
class DragEngineView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_win = parent

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.main_win.drag_position = event.globalPos() - self.main_win.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.main_win.drag_position:
            self.main_win.move(event.globalPos() - self.main_win.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.main_win.drag_position = None
        super().mouseReleaseEvent(event)


class JarvisHUD(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # REMOVED Qt.WindowStaysOnTopHint so it doesn't aggressively block every active application window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(600, 600)
        self.center_on_screen()

        self.drag_position = None

        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("background: transparent; border: none;")
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Integrated our new click-through DragEngineView
        self.web_view = DragEngineView(self)
        self.web_view.setStyleSheet("background: transparent; border: none;")
        self.web_view.setAttribute(Qt.WA_TranslucentBackground)
        self.web_view.page().setBackgroundColor(Qt.transparent)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(base_dir, "web", "nervous_system.html")
        self.web_view.setUrl(QUrl.fromLocalFile(html_path))
        
        self.layout.addWidget(self.web_view, 1)

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = int((screen.width() - self.width()) / 2)
        y = int((screen.height() - self.height()) / 2)
        self.move(x, y)

    def set_visibility(self, visible: bool):
        if visible:
            self.show()
            self.raise_() # Brings it to front when requested
        else:
            self.hide()

    def update_status(self, text: str):
        js_code = f"window.setJarvisState('{text.upper().replace(chr(39), '')}');"
        self.web_view.page().runJavaScript(js_code)

    def update_action(self, text: str):
        safe_text = text.replace("'", "\\'").replace("\n", " ")[:80]
        js_code = f"document.getElementById('action-bar').textContent = '{safe_text}';"
        self.web_view.page().runJavaScript(js_code)