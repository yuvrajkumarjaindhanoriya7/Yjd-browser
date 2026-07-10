from PyQt6.QtWidgets import QInputDialog
import sys
from PyQt6.QtCore import QUrl, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QToolBar, QLineEdit,
    QAction, QMenu, QFileDialog, QMessageBox, QStatusBar
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineDownloadItem
from PyQt6.QtPrintSupport import QPrintPreviewDialog

class BrowserTab(QWebEngineView):
    def __init__(self, profile):
        super().__init__()
        self.setPage(QWebEnginePage(profile, self))
        self.setUrl(QUrl("https://www.google.com"))

    def contextMenuEvent(self, event):
        menu = self.page().createStandardContextMenu()
        menu.addAction("Inspect Element", self.show_dev_tools)
        menu.exec(event.globalPos())

    def show_dev_tools(self):
        self.page().triggerAction(QWebEnginePage.WebAction.InspectElement)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Grok Browser")
        self.setMinimumSize(1200, 800)

        # Profile with basic ad blocking
        self.profile = QWebEngineProfile("grok_profile", self)
        self.profile.setHttpUserAgent("Mozilla/5.0 (compatible; GrokBrowser)")
        
        # Simple ad blocker (common domains)
        self.ad_block_list = ["doubleclick.net", "googlesyndication.com", "ads.", "ad.", "tracking.", "analytics."]

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.add_new_tab)
        self.setCentralWidget(self.tabs)

        # Status bar for downloads
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.setup_ui()
        self.add_new_tab(QUrl("https://www.google.com"))

    def setup_ui(self):
        nav_bar = QToolBar("Navigation")
        self.addToolBar(nav_bar)

        nav_bar.addAction("←", lambda: self.current_browser().back())
        nav_bar.addAction("→", lambda: self.current_browser().forward())
        nav_bar.addAction("⟳", lambda: self.current_browser().reload())
        nav_bar.addAction("🏠", self.navigate_home)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        nav_bar.addWidget(self.url_bar)

        nav_bar.addAction("+", self.add_new_tab)
        nav_bar.addAction("🔍 Inspect", self.inspect_page)

        # Menu Bar
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Open Local File / HTML", self.open_local_file)
        file_menu.addAction("Print Page", self.print_page)
        file_menu.addAction("Exit", self.close)

        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Dev Tools", self.inspect_page)
        tools_menu.addAction("Inject Custom JS", self.inject_js)

        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("Toggle Dark Mode", self.toggle_dark_mode)
        settings_menu.addAction("Set Homepage", self.set_homepage)
        settings_menu.addAction("Clear Browsing Data", self.clear_data)

    def add_new_tab(self, url=None):
        if not url or isinstance(url, bool):
            url = QUrl("https://www.google.com")
        tab = BrowserTab(self.profile)
        index = self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentIndex(index)

        tab.urlChanged.connect(self.update_urlbar)
        tab.titleChanged.connect(self.update_title)
        tab.page().profile().downloadRequested.connect(self.handle_download)
        
        QTimer.singleShot(500, lambda: self.apply_dark_mode(tab))
        self.apply_ad_block(tab)

    def apply_dark_mode(self, tab):
        dark_script = """
        document.documentElement.style.setProperty('color-scheme', 'dark');
        if (document.body) {
            document.body.style.backgroundColor = '#0f0f0f';
            document.body.style.color = '#e0e0e0';
        }
        """
        tab.page().runJavaScript(dark_script)

    def apply_ad_block(self, tab):
        block_script = f"""
        const adDomains = {self.ad_block_list};
        const observer = new MutationObserver(() => {{
            document.querySelectorAll('iframe, img, script').forEach(el => {{
                if (adDomains.some(d => el.src && el.src.includes(d))) el.remove();
            }});
        }});
        observer.observe(document.documentElement, {{ childList: true, subtree: true }});
        """
        tab.page().runJavaScript(block_script)

    def current_browser(self):
        return self.tabs.currentWidget()

    def navigate_home(self):
        if self.current_browser():
            self.current_browser().setUrl(QUrl("https://www.google.com"))

    def navigate_to_url(self):
        url = QUrl(self.url_bar.text())
        if url.scheme() == "": url.setScheme("https")
        self.current_browser().setUrl(url)

    def update_urlbar(self, q):
        self.url_bar.setText(q.toString())

    def update_title(self, title):
        index = self.tabs.currentIndex()
        self.tabs.setTabText(index, title[:25] + "..." if len(title) > 25 else title)
        self.setWindowTitle(f"{title} - Grok Browser")

    def inspect_page(self):
        if self.current_browser():
            self.current_browser().page().triggerAction(QWebEnginePage.WebAction.InspectElement)

    def open_local_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open HTML / File", "", "HTML Files (*.html *.htm);;All Files (*)")
        if file:
            self.add_new_tab(QUrl.fromLocalFile(file))

    def print_page(self):
        if self.current_browser():
            dialog = QPrintPreviewDialog(self)
            dialog.paintRequested.connect(self.current_browser().print)
            dialog.exec()

    def handle_download(self, download: QWebEngineDownloadItem):
        download.setDownloadDirectory("Downloads")
        download.accept()
        self.statusBar.showMessage(f"Downloading: {download.downloadFileName()}", 5000)

    def inject_js(self):
        code, ok = QInputDialog.getMultiLineText(self, "Inject JavaScript", "Enter JS code:")
        if ok and code and self.current_browser():
            self.current_browser().page().runJavaScript(code)

    def toggle_dark_mode(self):
        if self.current_browser():
            self.apply_dark_mode(self.current_browser())

    def set_homepage(self):
        url, ok = QInputDialog.getText(self, "Set Homepage", "Enter URL:")
        if ok and url:
            # You can save this to settings in a real app (QSettings)
            print(f"Homepage set to: {url}")

    def clear_data(self):
        self.profile.clearAllVisitedLinks()
        QMessageBox.information(self, "Success", "Browsing data cleared!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Grok Browser")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())