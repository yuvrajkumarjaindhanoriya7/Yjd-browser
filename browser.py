import sys
import cv2
import mediapipe as mp
import pyautogui
import threading
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QToolBar, QLineEdit,
    QAction, QMessageBox, QStatusBar
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtGui import QIcon

# ====================== HAND GESTURE CONTROLLER (CAMERA ONLY FOR THIS) ======================
class HandGestureController(threading.Thread):
    def __init__(self, enabled=True):
        super().__init__(daemon=True)
        self.enabled = enabled
        self.running = True
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
        self.screen_w, self.screen_h = pyautogui.size()
        self.cap = cv2.VideoCapture(0)
        self.prev_x = self.prev_y = 0

    def run(self):
        while self.running and self.cap.isOpened():
            if not self.enabled:
                continue
            ret, frame = self.cap.read()
            if not ret: continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb)

            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks[0].landmark
                idx = landmarks[8]
                x = int(idx.x * self.screen_w)
                y = int(idx.y * self.screen_h)

                sx = self.prev_x + (x - self.prev_x) / 6
                sy = self.prev_y + (y - self.prev_y) / 6
                pyautogui.moveTo(sx, sy, duration=0.01)
                self.prev_x, self.prev_y = sx, sy

                # Pinch to click
                thumb = landmarks[4]
                if abs(thumb.x - idx.x) < 0.06 and abs(thumb.y - idx.y) < 0.06:
                    pyautogui.click()
                    cv2.waitKey(150)

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

# ====================== CYGNUS AIRTUCH BROWSER ======================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cygnus AirTouch Browser - Secure")
        self.setWindowIcon(QIcon("cygnus_logo.ico"))
        self.setMinimumSize(1200, 800)

        # === STRONG SECURITY PROFILE ===
        self.profile = QWebEngineProfile("cygnus_secure", self)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)

        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.XSSAuditingEnabled, True)
        
        # BLOCK CAMERA/MICROPHONE/LOCATION FOR ALL WEBSITES
        self.profile.setUrlRequestInterceptor(self.block_permissions)

        self.hand_controller = HandGestureController(enabled=True)
        self.hand_controller.start()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.setup_ui()
        self.add_new_tab(QUrl("https://www.google.com"))

    def block_permissions(self, info):
        # Block all device access (camera, mic, etc.)
        if info.requestUrl().scheme() in ["http", "https"]:
            info.block(True)  # You can customize per feature if needed

    def setup_ui(self):
        toolbar = QToolBar("Navigation")
        self.addToolBar(toolbar)

        toolbar.addAction("←", lambda: self.current_browser().back())
        toolbar.addAction("→", lambda: self.current_browser().forward())
        toolbar.addAction("⟳", lambda: self.current_browser().reload())
        toolbar.addAction("🏠", lambda: self.current_browser().setUrl(QUrl("https://google.com")))

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        toolbar.addWidget(self.url_bar)

        toolbar.addAction("+ Tab", self.add_new_tab)
        toolbar.addAction("🔍 Inspect", self.inspect_page)

        hand_act = QAction("🤚 AirTouch", self)
        hand_act.setCheckable(True)
        hand_act.setChecked(True)
        hand_act.triggered.connect(self.toggle_hand)
        toolbar.addAction(hand_act)

    def add_new_tab(self, url=None):
        if not url or isinstance(url, bool):
            url = QUrl("https://www.google.com")
        tab = QWebEngineView()
        tab.setPage(QWebEnginePage(self.profile, tab))
        tab.setUrl(url)
        idx = self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentIndex(idx)
        tab.urlChanged.connect(lambda q: self.url_bar.setText(q.toString()))
        tab.titleChanged.connect(lambda t: self.set_tab_title(t))

    def current_browser(self):
        return self.tabs.currentWidget()

    def navigate_to_url(self):
        url = QUrl(self.url_bar.text())
        if url.scheme() == "": url.setScheme("https")
        self.current_browser().setUrl(url)

    def inspect_page(self):
        if self.current_browser():
            self.current_browser().page().triggerAction(QWebEnginePage.WebAction.InspectElement)

    def toggle_hand(self, checked):
        self.hand_controller.enabled = checked
        self.statusBar.showMessage(f"AirTouch Hand Control {'Enabled' if checked else 'Disabled'}", 3000)

    def set_tab_title(self, title):
        idx = self.tabs.currentIndex()
        self.tabs.setTabText(idx, title[:30] if title else "Tab")

    def closeEvent(self, event):
        self.hand_controller.stop()
        self.profile.clearAllVisitedLinks()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Cygnus AirTouch Browser")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())