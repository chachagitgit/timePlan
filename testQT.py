import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                            QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
                            QMessageBox, QFrame, QTreeWidget, QTreeWidgetItem,
                            QStackedWidget)
from PyQt6.QtCore import Qt
import sqlite3
import hashlib

# Reuse database functions from original code
def Connect():
    conn = sqlite3.connect("timePlanDB.db")
    return conn

def CreateUserTable():
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def HashPassword(password):
    return hashlib.sha256(password.encode()).hexdigest()

def AuthenticateUser(username, password):
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                   (username, HashPassword(password)))
    user = cursor.fetchone()
    conn.close()
    return user

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TimePlan Login")
        self.setFixedSize(350, 200)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Create user table
        CreateUserTable()
        
        # Username field
        username_label = QLabel("Username:")
        self.username_entry = QLineEdit()
        layout.addWidget(username_label)
        layout.addWidget(self.username_entry)
        
        # Password field
        password_label = QLabel("Password:")
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(password_label)
        layout.addWidget(self.password_entry)
        
        # Buttons frame
        buttons_frame = QFrame()
        buttons_layout = QHBoxLayout(buttons_frame)
        
        # Login button
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.login)
        buttons_layout.addWidget(login_btn)
        
        # Sign up button
        signup_btn = QPushButton("Sign Up")
        signup_btn.clicked.connect(self.open_signup)
        buttons_layout.addWidget(signup_btn)
        
        layout.addWidget(buttons_frame)
        
        # Center window
        self.center_window()
        
        # Connect return key to login
        self.username_entry.returnPressed.connect(self.login)
        self.password_entry.returnPressed.connect(self.login)

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def login(self):
        username = self.username_entry.text().strip()
        password = self.password_entry.text().strip()

        if not username or not password:
            QMessageBox.critical(self, "Error", "Please enter username and password.")
            return

        user = AuthenticateUser(username, password)
        if user:
            self.main_window = TimePlanMainWindow(user[0], username)  # Store as instance variable
            self.main_window.show()
            self.hide()  # Hide instead of close
        else:
            QMessageBox.critical(self, "Error", "Invalid username or password.")

    def open_signup(self):
        self.signup_window = SignUpWindow(self)
        self.signup_window.show()
        self.hide()

class SignUpWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Sign Up")
        self.setFixedSize(400, 350)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("Create a new account")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Username field
        username_label = QLabel("Username:")
        self.username_entry = QLineEdit()
        layout.addWidget(username_label)
        layout.addWidget(self.username_entry)
        
        # Password field
        password_label = QLabel("Password:")
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(password_label)
        layout.addWidget(self.password_entry)
        
        # Confirm password field
        confirm_label = QLabel("Confirm Password:")
        self.confirm_entry = QLineEdit()
        self.confirm_entry.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(confirm_label)
        layout.addWidget(self.confirm_entry)
        
        # Register button
        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self.register_user)
        layout.addWidget(register_btn)
        
        # Back button
        back_btn = QPushButton("Back to Login")
        back_btn.clicked.connect(self.back_to_login)
        layout.addWidget(back_btn)
        
        # Center window
        self.center_window()

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def register_user(self):
        # TODO: Implement user registration
        pass

    def back_to_login(self):
        self.parent.show()
        self.close()

class CollapsibleSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = True
        self.setFixedWidth(200)  # Default expanded width
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App name label
        self.app_name = QLabel("TimePlan")
        self.app_name.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                padding: 20px;
                background-color: #2c3e50;
                color: white;
            }
        """)
        layout.addWidget(self.app_name)

        # Navigation buttons
        self.nav_buttons = []
        nav_items = [
            ("Tasks", "📋"),
            ("Calendar", "📅"),
            ("Habit", "🔄"),
            ("Add Task", "➕"),
            ("Search Task", "🔍"),
            ("Profile", "👤"),
            ("Sign Out", "🚪")
        ]

        for text, icon in nav_items:
            btn = QPushButton(f"{icon} {text}")
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    border: none;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #34495e;
                    color: white;
                }
            """)
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # Toggle button
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                padding: 5px;
                border: none;
                background-color: #2c3e50;
                color: white;
            }
        """)
        layout.addWidget(self.toggle_btn)

        self.setStyleSheet("""
            CollapsibleSidebar {
                background-color: #ecf0f1;
                border-right: 1px solid #bdc3c7;
            }
        """)

    def toggle_sidebar(self):
        if self.is_expanded:
            self.setFixedWidth(50)
            self.toggle_btn.setText("▶")
            self.app_name.hide()
            for btn in self.nav_buttons:
                text = btn.text().split(" ")[0]  # Keep only the emoji
                btn.setText(text)
        else:
            self.setFixedWidth(200)
            self.toggle_btn.setText("◀")
            self.app_name.show()
            for i, btn in enumerate(self.nav_buttons):
                text = ["Tasks", "Calendar", "Habit", "Add Task", "Search Task", "Profile", "Sign Out"][i]
                emoji = btn.text()
                btn.setText(f"{emoji} {text}")
        
        self.is_expanded = not self.is_expanded

class TimePlanMainWindow(QMainWindow):
    def __init__(self, user_id, username):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.setWindowTitle("TimePlan")
        self.setMinimumSize(1000, 600)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add collapsible sidebar
        self.sidebar = CollapsibleSidebar()
        main_layout.addWidget(self.sidebar)

        # Create stacked widget for different views
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create and add different views
        self.tasks_view = self.create_tasks_view()
        self.stacked_widget.addWidget(self.tasks_view)

        # Connect sidebar buttons
        self.sidebar.nav_buttons[0].clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.tasks_view))
        # TODO: Add other views and connect their buttons

        self.center_window()

    def create_tasks_view(self):
        tasks_widget = QWidget()
        layout = QHBoxLayout(tasks_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create categories sidebar
        categories_sidebar = QWidget()
        categories_sidebar.setFixedWidth(250)
        categories_sidebar.setStyleSheet("""
            QWidget {
                background-color: #f5f6fa;
                border-right: 1px solid #dcdde1;
            }
            QTreeWidget {
                border: none;
                background-color: transparent;
            }
            QTreeWidget::item {
                padding: 10px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #dcdde1;
            }
        """)
        
        categories_layout = QVBoxLayout(categories_sidebar)
        categories_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add categories tree widget
        categories = QTreeWidget()
        categories.setHeaderHidden(True)
        
        # Task Categories
        task_categories = [
            ("📅 Today", "today"),
            ("📆 Next 7 Days", "next7"),
            ("📋 All Tasks", "all"),
            ("🔄 On-going", "ongoing"),
            ("✅ Completed", "completed"),
            ("❗ Missed", "missed")
        ]
        
        for label, category_id in task_categories:
            category_item = QTreeWidgetItem(categories, [label])
            category_item.setData(0, Qt.ItemDataRole.UserRole, category_id)
        
        categories.itemClicked.connect(self.on_category_selected)
        categories_layout.addWidget(categories)
        
        # Create main content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        self.category_title = QLabel("📅 Today")
        self.category_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2d3436;
        """)
        header_layout.addWidget(self.category_title)
        
        # Add task count
        self.task_count = QLabel("0 tasks")
        self.task_count.setStyleSheet("color: #636e72;")
        header_layout.addWidget(self.task_count)
        header_layout.addStretch()
        
        content_layout.addWidget(header)
        
        # Add task list
        self.task_list = QTreeWidget()
        self.task_list.setHeaderLabels(["Task", "Due Date", "Status"])
        self.task_list.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 8px;
            }
        """)
        content_layout.addWidget(self.task_list)
        
        # Add widgets to main layout
        layout.addWidget(categories_sidebar)
        layout.addWidget(content, stretch=1)
        
        return tasks_widget

    def on_category_selected(self, item):
        category_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.category_title.setText(item.text(0))
        self.load_tasks(category_id)
        
    def load_tasks(self, category):
        self.task_list.clear()
        conn = Connect()
        cursor = conn.cursor()
        
        query_map = {
            "today": """
                SELECT id, title, due_date, status 
                FROM tasks 
                WHERE user_id = ? 
                AND date(due_date) = date('now')
            """,
            "next7": """
                SELECT id, title, due_date, status 
                FROM tasks 
                WHERE user_id = ? 
                AND date(due_date) BETWEEN date('now') 
                AND date('now', '+7 days')
            """,
            "all": """
                SELECT id, title, due_date, status 
                FROM tasks 
                WHERE user_id = ?
            """,
            "ongoing": """
                SELECT id, title, due_date, status 
                FROM tasks 
                WHERE user_id = ? 
                AND status = 'On-going'
            """,
            "completed": """
                SELECT id, title, due_date, status 
                FROM tasks 
                WHERE user_id = ? 
                AND status = 'Completed'
            """,
            "missed": """
                SELECT id, title, due_date, status 
                FROM tasks 
                WHERE user_id = ? 
                AND date(due_date) < date('now')
                AND status != 'Completed'
            """
        }
        
        cursor.execute(query_map[category], (self.user_id,))
        tasks = cursor.fetchall()
        conn.close()
        
        for task in tasks:
            item = QTreeWidgetItem(self.task_list)
            item.setText(0, task[1])  # Title
            item.setText(1, task[2])  # Due Date
            item.setText(2, task[3])  # Status
            item.setData(0, Qt.ItemDataRole.UserRole, task[0])  # Store task ID
        
        self.task_count.setText(f"{len(tasks)} tasks")

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

def main():
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()