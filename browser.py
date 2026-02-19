import sys
import re
import traceback
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit, QPushButton,
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

# ----------------------------
# CONFIG
# ----------------------------
GITHUB_BASE = "https://datlittladucky.github.io/Websites/"
START_PAGE = f"{GITHUB_BASE}start/index.html"

# ----------------------------
# VALIDATION
# ----------------------------
def validate_input(user_input):
    pattern = r"^(https?://)?([a-zA-Z0-9-]+\.)+(com|co\.uk|org)(/[a-zA-Z0-9\-_/]*)?$"
    return re.match(pattern, user_input)

def parse_input(user_input):
    user_input = user_input.replace("http://", "").replace("https://", "")
    user_input = user_input.strip("/")

    parts = user_input.split("/", 1)
    domain = parts[0]
    subpath = parts[1] if len(parts) > 1 else ""
    return domain, subpath

# ----------------------------
# CUSTOM PAGE: blocks external browsing
# ----------------------------
class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, browser_instance):
        super().__init__()
        self.browser_instance = browser_instance

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        url_str = url.toString()

        # Allow internal GitHub pages
        if url_str.startswith(GITHUB_BASE):
            return True

        # Catch ANY https://example.com style navigation
        match = re.match(r"https?://(.+)", url_str)
        if match:
            user_input = match.group(1)

            if validate_input(user_input):
                domain, subpath = parse_input(user_input)

                if subpath:
                    new_url = f"{GITHUB_BASE}{domain}/{subpath}.html"
                    virtual_url = f"{domain}/{subpath}"
                else:
                    new_url = f"{GITHUB_BASE}{domain}/index.html"
                    virtual_url = domain

                self.browser_instance.virtual_url = virtual_url
                self.browser_instance.setUrl(QUrl(new_url))
                return False

        return False

# ----------------------------
# BROWSER TAB
# ----------------------------
class BrowserTab(QWidget):
    def __init__(self, parent_tabs):
        super().__init__()
        self.parent_tabs = parent_tabs

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QWebEngineView()
        QApplication.processEvents()  # ensure engine is initialized
        self.browser.setPage(CustomWebEnginePage(self.browser))

        # Virtual URL storage
        self.browser.virtual_url = ""

        # Signals
        self.browser.titleChanged.connect(self.update_tab_title)
        self.browser.urlChanged.connect(self.sync_virtual_url)
        self.browser.loadFinished.connect(self.check_load_success)

        self.layout.addWidget(self.browser)
        self.setLayout(self.layout)

    def update_tab_title(self, title):
        index = self.parent_tabs.indexOf(self)
        if title and title.strip():
            self.parent_tabs.setTabText(index, title[:40])
        else:
            self.parent_tabs.setTabText(index, "Untitled")

    def sync_virtual_url(self, qurl):
        url = qurl.toString()
        if url.startswith(GITHUB_BASE):
            stripped = url.replace(GITHUB_BASE, "")
            stripped = stripped.replace(".html", "")
            stripped = stripped.strip("/")
            self.browser.virtual_url = stripped

    def check_load_success(self, success):
        if not success:
            self.show_custom_404("Page failed to load")
            return
        # Detect GitHub Pages 404 by title
        self.browser.page().runJavaScript(
            "document.title", self.check_title_for_404
        )

    def check_title_for_404(self, title):
        if title and "404" in title:
            self.show_custom_404("Page not found")

    def show_custom_404(self, message):
        html = f"""
        <html>
            <head>
                <style>
                    body {{
                        background-color: #111;
                        color: white;
                        font-family: Arial;
                        text-align: center;
                        margin-top: 15%;
                    }}
                    h1 {{
                        font-size: 60px;
                        color: red;
                    }}
                    p {{
                        font-size: 20px;
                        color: #ccc;
                    }}
                </style>
            </head>
            <body>
                <h1>404</h1>
                <p>{message}</p>
                <p>The requested site does not exist.</p>
            </body>
        </html>
        """
        self.browser.setHtml(html)

# ----------------------------
# MAIN WINDOW
# ----------------------------
class MiniBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini Browser")
        self.setGeometry(100, 100, 1400, 900)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_url_bar)
        self.setCentralWidget(self.tabs)

        # Toolbar
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Back / Forward / Refresh
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedWidth(40)
        self.back_btn.clicked.connect(lambda: self.current_browser().back())
        toolbar.addWidget(self.back_btn)

        self.forward_btn = QPushButton("→")
        self.forward_btn.setFixedWidth(40)
        self.forward_btn.clicked.connect(lambda: self.current_browser().forward())
        toolbar.addWidget(self.forward_btn)

        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setFixedWidth(40)
        self.refresh_btn.clicked.connect(lambda: self.current_browser().reload())
        toolbar.addWidget(self.refresh_btn)

        # URL bar with fake HTTPS lock
        self.url_container = QWidget()
        url_layout = QHBoxLayout()
        url_layout.setContentsMargins(0, 0, 0, 0)
        self.url_container.setLayout(url_layout)

        self.lock_icon = QLabel("🔒")
        self.lock_icon.setStyleSheet("color: green; font-weight: bold;")
        self.lock_icon.setFixedWidth(25)
        url_layout.addWidget(self.lock_icon)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.load_page)
        url_layout.addWidget(self.url_bar, 1)
        toolbar.addWidget(self.url_container)

        # New tab button
        self.new_tab_btn = QPushButton("+")
        self.new_tab_btn.setFixedWidth(30)
        self.new_tab_btn.clicked.connect(lambda: self.add_tab(start_url=START_PAGE))
        toolbar.addWidget(self.new_tab_btn)

        # Start with one tab and load start page
        self.add_tab(start_url=START_PAGE)

    # ----------------------------
    def current_browser(self):
        return self.tabs.currentWidget().browser

    def add_tab(self, start_url=None):
        new_tab = BrowserTab(self.tabs)
        index = self.tabs.addTab(new_tab, "New Tab")
        self.tabs.setCurrentIndex(index)
        if start_url:
            new_tab.browser.setUrl(QUrl(start_url))

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)

    # ----------------------------
    def load_page(self):
        user_input = self.url_bar.text().strip()

        # Special case for start page
        if user_input.lower() in ["start", "websites/start"]:
            self.current_browser().setUrl(QUrl(START_PAGE))
            return

        if not validate_input(user_input):
            self.current_tab().show_custom_404("Invalid domain format")
            return

        domain, subpath = parse_input(user_input)

        if subpath:
            target_url = f"{GITHUB_BASE}{domain}/{subpath}.html"
            virtual_url = f"{domain}/{subpath}"
        else:
            target_url = f"{GITHUB_BASE}{domain}/index.html"
            virtual_url = domain

        browser = self.current_browser()
        browser.virtual_url = virtual_url
        browser.setUrl(QUrl(target_url))
        self.tabs.setTabText(self.tabs.currentIndex(), domain)

    def update_url_bar(self, index):
        browser = self.current_browser()
        if hasattr(browser, "virtual_url"):
            self.url_bar.setText(browser.virtual_url)
        else:
            self.url_bar.setText("")

    def current_tab(self):
        return self.tabs.currentWidget()

# ----------------------------
# GLOBAL EXCEPTION HOOK
# ----------------------------
def handle_exceptions(exctype, value, tb):
    print("ERROR:", ''.join(traceback.format_exception(exctype, value, tb)))

sys.excepthook = handle_exceptions

# ----------------------------
# RUN
# ----------------------------
app = QApplication(sys.argv)
window = MiniBrowser()
window.show()
sys.exit(app.exec())