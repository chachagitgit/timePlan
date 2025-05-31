import sqlite3
import hashlib
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox
from tkcalendar import Calendar
from datetime import datetime
import babel.numbers


dbName = "timePlanDB.db"

def Connect():
    conn = sqlite3.connect(dbName)
    return conn

def CheckAndUpdateSchema():
    conn = Connect()
    cursor = conn.cursor()
    
    # Get current columns in the tasks table
    cursor.execute("PRAGMA table_info(tasks)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    # Check if recurrence_pattern column exists
    if 'recurrence_pattern' not in column_names:
        cursor.execute('ALTER TABLE tasks ADD COLUMN recurrence_pattern TEXT')
        conn.commit()
    
    conn.close()

def CreateTable():
    conn = Connect()
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            priority TEXT,
            due_date TEXT,
            is_recurring INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            time_spent INTEGER DEFAULT 0,
            last_completed_date TEXT,
            user_id INTEGER NOT NULL,
            recurrence_pattern TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

    # Check and update schema if needed
    CheckAndUpdateSchema()

def AddTask(title, description, category, priority, dueDate, isRecurring, user_id, recurrence_pattern=None):
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (
            title, description, category, priority, due_date, is_recurring, 
            last_completed_date, user_id, recurrence_pattern
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
    ''', (title, description, category, priority, dueDate, isRecurring, user_id, recurrence_pattern))
    conn.commit()
    conn.close()

def GetTasksFiltered(user_id, category_filter=None, priority_filter=None):
    conn = Connect()
    cursor = conn.cursor()
    query = """
        SELECT 
            id, 
            title, 
            due_date, 
            category, 
            priority,
            last_completed_date,
            date('now', 'localtime') as today
        FROM tasks 
        WHERE user_id = ?
    """
    params = [user_id]
    if category_filter and category_filter != "All":
        query += " AND category = ?"
        params.append(category_filter)
    if priority_filter and priority_filter != "All":
        query += " AND priority = ?"
        params.append(priority_filter)
    query += " ORDER BY due_date"
    cursor.execute(query, params)
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def DeleteTask(taskId, user_id):
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (taskId, user_id))
    conn.commit()
    conn.close()

def UpdateTask(taskId, **kwargs):
    conn = Connect()
    cursor = conn.cursor()
    fields = ', '.join([f"{key}=?" for key in kwargs])
    values = list(kwargs.values())
    values.append(taskId)
    cursor.execute(f'UPDATE tasks SET {fields} WHERE id = ?', values)
    conn.commit()
    conn.close()

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

def RegisterUser(username, password):
    conn = Connect()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                       (username, HashPassword(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists
    finally:
        conn.close()

def AuthenticateUser(username, password):
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                   (username, HashPassword(password)))
    user = cursor.fetchone()
    conn.close()
    return user

def UpdateTaskStatus(taskId, new_status):
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET category = ? WHERE id = ?', (new_status, taskId))
    conn.commit()
    conn.close()

def MarkRecurringTaskComplete(taskId):
    conn = Connect()
    cursor = conn.cursor()
    today = cursor.execute("SELECT date('now', 'localtime')").fetchone()[0]
    cursor.execute('UPDATE tasks SET last_completed_date = ? WHERE id = ?', (today, taskId))
    conn.commit()
    conn.close()

def UpdateMissedTasks(user_id):
    conn = Connect()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tasks 
        SET category = 'Missed'
        WHERE user_id = ?
        AND category NOT IN ('Recurring', 'Done', 'Missed')
        AND due_date < date('now', 'localtime')
        AND due_date IS NOT NULL
        AND due_date != ''
    ''', (user_id,))
    conn.commit()
    conn.close()

class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("TimePlan Login")
        self.geometry("350x200")
        self.resizable(False, False)

        # Center the window on the screen
        self.center_window()

        CreateUserTable()  # Ensure users table exists

        ttk.Label(self, text="Username:").pack(pady=(20, 5))
        self.username_entry = ttk.Entry(self)
        self.username_entry.pack(fill=tk.X, padx=20)

        ttk.Label(self, text="Password:").pack(pady=(10, 5))
        self.password_entry = ttk.Entry(self, show="*")
        self.password_entry.pack(fill=tk.X, padx=20)

        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(pady=20)

        ttk.Button(buttons_frame, text="Login", command=self.login).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Sign Up", command=self.open_signup).pack(side=tk.LEFT, padx=10)

        # Protocol for window close button
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Bind Enter key to login
        self.bind('<Return>', lambda e: self.login())

    def center_window(self):
        # Get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calculate position coordinates
        x = (screen_width/2) - (350/2)
        y = (screen_height/2) - (200/2)
        
        # Set the position
        self.geometry(f'350x200+{int(x)}+{int(y)}')

    def on_closing(self):
        if tkinter.messagebox.askyesno("Exit", "Are you sure you want to exit the application?"):
            self.destroy()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            tkinter.messagebox.showerror("Error", "Please enter username and password.")
            return

        user = AuthenticateUser(username, password)
        if user:
            tkinter.messagebox.showinfo("Success", f"Welcome {username}!")
            self.destroy()
            app = TimePlanApp(user[0], username)  # Pass user_id and username
            app.mainloop()
        else:
            tkinter.messagebox.showerror("Error", "Invalid username or password.")

    def open_signup(self):
        self.withdraw()
        signup_win = SignUpWindow(self)
        signup_win.grab_set()

class SignUpWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)

        self.title("Sign Up")
        self.geometry("400x350")  # Increased window size
        self.resizable(False, False)

        # Main container frame with padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Create a new account", font=("Helvetica", 14, "bold")).pack(pady=(0, 20))

        ttk.Label(main_frame, text="Username:").pack(anchor=tk.W, pady=(0, 5))
        self.username_entry = ttk.Entry(main_frame)
        self.username_entry.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(main_frame, text="Password:").pack(anchor=tk.W, pady=(0, 5))
        self.password_entry = ttk.Entry(main_frame, show="*")
        self.password_entry.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(main_frame, text="Confirm Password:").pack(anchor=tk.W, pady=(0, 5))
        self.confirm_password_entry = ttk.Entry(main_frame, show="*")
        self.confirm_password_entry.pack(fill=tk.X, pady=(0, 25))

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(buttons_frame, text="Register", command=self.register_user).pack(fill=tk.X, pady=(0, 10))
        ttk.Button(buttons_frame, text="Back to Login", command=self.back_to_login).pack(fill=tk.X)

    def register_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()

        if not username or not password or not confirm_password:
            tkinter.messagebox.showerror("Error", "All fields are required.")
            return

        if password != confirm_password:
            tkinter.messagebox.showerror("Error", "Passwords do not match.")
            return

        if RegisterUser(username, password):
            tkinter.messagebox.showinfo("Success", "Account created successfully!")
            self.destroy()
            self.master.deiconify()
        else:
            tkinter.messagebox.showerror("Error", "Username already exists.")

    def back_to_login(self):
        self.destroy()
        self.master.deiconify()

class TimePlanApp(tk.Tk):
    def __init__(self, user_id, username):
        super().__init__()

        self.user_id = user_id
        self.username = username
        self.title(f"TimePlan Productivity System - {username}")
        self.geometry("1200x600")

        CreateTable()
        UpdateMissedTasks(self.user_id)
        
        # Add menu bar
        self.create_menu_bar()
        
        # Main container with scrollbar
        self.main_canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.main_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )

        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the main scrollable elements
        self.main_canvas.pack(side="left", fill="both", expand=True, padx=(10,0), pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)

        # Enable mousewheel scrolling
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Main container
        main_container = ttk.Frame(self.scrollable_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10)

        # Left frame: Calendar and Task creation form
        self.left_frame = ttk.Frame(main_container, width=400, relief=tk.SUNKEN)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Create and pack the calendar frame
        self.create_calendar_frame()
        
        # Create and pack the task form
        self.create_task_form()

        # Right frame: Task list and filters
        self.right_frame = ttk.Frame(main_container, width=600, relief=tk.SUNKEN)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.create_task_list()
        
        # Initial calendar update
        self.update_calendar_tasks()

        # Protocol for window close button
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_menu_bar(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # User menu
        user_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=f"User: {self.username}", menu=user_menu)
        user_menu.add_command(label="Sign Out", command=self.sign_out)
        user_menu.add_separator()
        user_menu.add_command(label="Exit", command=self.on_closing)

    def sign_out(self):
        if tkinter.messagebox.askyesno("Sign Out", "Are you sure you want to sign out?"):
            self.destroy()
            login_window = LoginWindow()
            login_window.mainloop()

    def on_closing(self):
        if tkinter.messagebox.askyesno("Exit", "Are you sure you want to exit the application?"):
            self.destroy()

    def _on_mousewheel(self, event):
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def create_calendar_frame(self):
        calendar_frame = ttk.Frame(self.left_frame)
        calendar_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Create the calendar widget
        self.calendar = Calendar(calendar_frame, 
                               selectmode='day',
                               date_pattern='yyyy-mm-dd',
                               showweeknumbers=False)
        self.calendar.pack(fill=tk.X)
        
        # Bind the calendar selection event
        self.calendar.bind('<<CalendarSelected>>', self.on_date_selected)
        
        # Create a frame for task preview with scrollbar
        self.preview_frame = ttk.Frame(calendar_frame)
        self.preview_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(self.preview_frame, text="Tasks for selected date:", 
                 font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        # Create a frame for the preview text and scrollbar
        preview_container = ttk.Frame(self.preview_frame)
        preview_container.pack(fill=tk.X)
        
        # Add scrollbar for preview
        preview_scroll = ttk.Scrollbar(preview_container)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create a text widget for task preview
        self.task_preview = tk.Text(preview_container, height=4, wrap=tk.WORD,
                                  yscrollcommand=preview_scroll.set)
        self.task_preview.pack(side=tk.LEFT, fill=tk.X, expand=True)
        preview_scroll.config(command=self.task_preview.yview)
        self.task_preview.config(state=tk.DISABLED)

    def update_calendar_tasks(self):
        conn = Connect()
        cursor = conn.cursor()
        
        # Get all tasks including recurring ones
        cursor.execute('''
            SELECT due_date, title, category, recurrence_pattern, last_completed_date 
            FROM tasks 
            WHERE user_id = ? 
            AND due_date IS NOT NULL 
            AND due_date != ''
        ''', (self.user_id,))
        tasks = cursor.fetchall()
        conn.close()

        # Reset calendar colors
        self.calendar.calevent_remove('all')

        from datetime import datetime, timedelta
        current_date = datetime.now().date()
        
        # Process each task
        for due_date, title, category, recurrence_pattern, last_completed in tasks:
            try:
                task_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                
                # For recurring tasks, add multiple instances
                if category == "Recurring" and recurrence_pattern:
                    # Calculate next occurrences
                    dates_to_add = []
                    temp_date = task_date
                    
                    # Calculate for the next 6 months
                    end_date = current_date + timedelta(days=180)  # 6 months ahead
                    
                    while temp_date <= end_date:
                        if temp_date >= current_date:
                            # Check if this occurrence is completed
                            is_completed = False
                            if last_completed:
                                last_completed_date = datetime.strptime(last_completed, '%Y-%m-%d').date()
                                is_completed = (temp_date == last_completed_date)
                            
                            dates_to_add.append((temp_date, is_completed))
                        
                        # Calculate next occurrence based on pattern
                        if recurrence_pattern == "Daily":
                            temp_date += timedelta(days=1)
                        elif recurrence_pattern == "Weekly":
                            temp_date += timedelta(days=7)
                        elif recurrence_pattern == "Monthly":
                            # Handle month rollover
                            year = temp_date.year + (temp_date.month // 12)
                            month = (temp_date.month % 12) + 1
                            # Try to maintain the same day, but handle month length differences
                            try:
                                temp_date = temp_date.replace(year=year, month=month)
                            except ValueError:
                                # If the day doesn't exist in the target month, use the last day
                                if month == 2 and temp_date.day > 28:
                                    temp_date = temp_date.replace(year=year, month=month, day=28)
                                else:
                                    # Get the last day of the target month
                                    if month == 12:
                                        next_month = datetime(year + 1, 1, 1)
                                    else:
                                        next_month = datetime(year, month + 1, 1)
                                    last_day = (next_month - timedelta(days=1)).day
                                    temp_date = temp_date.replace(year=year, month=month, day=last_day)
                        elif recurrence_pattern == "Annually":
                            # Handle leap year for February 29
                            try:
                                temp_date = temp_date.replace(year=temp_date.year + 1)
                            except ValueError:
                                # If it's February 29 and next year is not a leap year
                                temp_date = temp_date.replace(year=temp_date.year + 1, month=2, day=28)
                    
                    # Add all calculated dates to calendar with appropriate status
                    for date, is_completed in dates_to_add:
                        status_symbol = "✓ " if is_completed else "🔄 "
                        self.calendar.calevent_create(
                            date,
                            f"{status_symbol}{title}",
                            "recurring_completed" if is_completed else "recurring"
                        )
                else:
                    # For non-recurring tasks
                    if task_date >= current_date:
                        self.calendar.calevent_create(
                            task_date,
                            title,
                            "task"
                        )
            except (ValueError, TypeError) as e:
                print(f"Error processing task date: {e}")
                continue

        # Configure tags with colors
        self.calendar.tag_config("task", background="lightblue")
        self.calendar.tag_config("recurring", background="lightgreen")
        self.calendar.tag_config("recurring_completed", background="darkseagreen")

    def on_date_selected(self, event):
        selected_date = self.calendar.get_date()
        
        conn = Connect()
        cursor = conn.cursor()
        
        # First get all tasks for the selected date
        cursor.execute('''
            SELECT title, category, priority, recurrence_pattern, due_date, last_completed_date 
            FROM tasks 
            WHERE user_id = ?
            ORDER BY category, priority
        ''', (self.user_id,))
        tasks = cursor.fetchall()
        conn.close()

        self.task_preview.config(state=tk.NORMAL)
        self.task_preview.delete(1.0, tk.END)
        
        from datetime import datetime, timedelta
        
        # Convert selected date to datetime for comparison
        selected_datetime = datetime.strptime(selected_date, '%Y-%m-%d').date()
        tasks_for_date = []

        for title, category, priority, recurrence_pattern, due_date, last_completed in tasks:
            try:
                task_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                
                # Handle recurring tasks
                if category == "Recurring" and recurrence_pattern:
                    # Calculate if this task occurs on selected date
                    temp_date = task_date
                    is_on_date = False
                    is_completed = False
                    
                    # Check up to the selected date
                    while temp_date <= selected_datetime:
                        if temp_date == selected_datetime:
                            is_on_date = True
                            # Check if it was completed on this date
                            if last_completed:
                                last_completed_date = datetime.strptime(last_completed, '%Y-%m-%d').date()
                                is_completed = (selected_datetime == last_completed_date)
                            break
                            
                        # Move to next occurrence
                        if recurrence_pattern == "Daily":
                            temp_date += timedelta(days=1)
                        elif recurrence_pattern == "Weekly":
                            temp_date += timedelta(days=7)
                        elif recurrence_pattern == "Monthly":
                            # Handle month rollover
                            year = temp_date.year + (temp_date.month // 12)
                            month = (temp_date.month % 12) + 1
                            try:
                                temp_date = temp_date.replace(year=year, month=month)
                            except ValueError:
                                # Handle month length differences
                                if month == 2 and temp_date.day > 28:
                                    temp_date = temp_date.replace(year=year, month=month, day=28)
                                else:
                                    # Get last day of target month
                                    if month == 12:
                                        next_month = datetime(year + 1, 1, 1)
                                    else:
                                        next_month = datetime(year, month + 1, 1)
                                    last_day = (next_month - timedelta(days=1)).day
                                    temp_date = temp_date.replace(year=year, month=month, day=last_day)
                        elif recurrence_pattern == "Annually":
                            try:
                                temp_date = temp_date.replace(year=temp_date.year + 1)
                            except ValueError:
                                # Handle February 29 in non-leap years
                                temp_date = temp_date.replace(year=temp_date.year + 1, month=2, day=28)
                    
                    if is_on_date:
                        status = "✓ Done Today" if is_completed else "⏳ Not Done Today"
                        tasks_for_date.append((title, category, priority, status, recurrence_pattern))
                
                # Handle non-recurring tasks
                elif task_date == selected_datetime:
                    status = ""
                    if category == "Done":
                        status = "✓ Completed"
                    elif category == "Missed":
                        status = "❌ Missed"
                    elif category == "On-going":
                        status = "⏳ Pending"
                    tasks_for_date.append((title, category, priority, status, None))
                    
            except (ValueError, TypeError) as e:
                print(f"Error processing task date: {e}")
                continue

        if tasks_for_date:
            for title, category, priority, status, recurrence_pattern in tasks_for_date:
                priority_text = f" ({priority})" if priority else ""
                recurrence_text = f" [{recurrence_pattern}]" if recurrence_pattern else ""
                status_text = f" - {status}" if status else ""
                self.task_preview.insert(tk.END, f"• {title}{priority_text}{recurrence_text}{status_text}\n")
        else:
            self.task_preview.insert(tk.END, "No tasks scheduled for this date.")
        
        self.task_preview.config(state=tk.DISABLED)

    def create_task_form(self):
        form_frame = ttk.LabelFrame(self.left_frame, text="Task Creation Form", padding=10)
        form_frame.pack(fill=tk.X, pady=(0, 10))

        # Task Name
        ttk.Label(form_frame, text="Task Name:").pack(anchor=tk.W, pady=(5,0))
        self.task_name_entry = ttk.Entry(form_frame)
        self.task_name_entry.pack(fill=tk.X)

        # Description
        ttk.Label(form_frame, text="Description:").pack(anchor=tk.W, pady=(10,0))
        self.description_text = tk.Text(form_frame, height=3)
        self.description_text.pack(fill=tk.X)

        # Category dropdown (placed before date for dynamic label update)
        ttk.Label(form_frame, text="Category:").pack(anchor=tk.W, pady=(10,0))
        self.category_var = tk.StringVar()
        self.category_dropdown = ttk.Combobox(
            form_frame,
            textvariable=self.category_var,
            values=["Recurring", "On-going"],
            state="readonly"
        )
        self.category_dropdown.pack(fill=tk.X)
        self.category_dropdown.bind("<<ComboboxSelected>>", self.on_category_change)

        # Date frame with dynamic label
        self.date_frame = ttk.Frame(form_frame)
        self.date_frame.pack(fill=tk.X, pady=(10,0))
        
        self.date_label = ttk.Label(self.date_frame, text="Due Date (YYYY-MM-DD):")
        self.date_label.pack(anchor=tk.W)
        
        date_entry_frame = ttk.Frame(self.date_frame)
        date_entry_frame.pack(fill=tk.X)
        
        self.date_entry = ttk.Entry(date_entry_frame)
        self.date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(date_entry_frame, text="📅", width=3,
                  command=lambda: self.date_entry.insert(0, self.calendar.get_date())
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Priority dropdown (only for On-going)
        self.priority_label = ttk.Label(form_frame, text="Priority:")
        self.priority_var = tk.StringVar()
        self.priority_dropdown = ttk.Combobox(
            form_frame,
            textvariable=self.priority_var,
            values=["Urgent", "Not Urgent"],
            state="readonly"
        )

        # Recurrence Pattern frame (initially hidden)
        self.recurrence_frame = ttk.Frame(form_frame)
        ttk.Label(self.recurrence_frame, text="Recurrence Pattern:").pack(anchor=tk.W, pady=(10,0))
        self.recurrence_var = tk.StringVar()
        self.recurrence_dropdown = ttk.Combobox(
            self.recurrence_frame,
            textvariable=self.recurrence_var,
            values=["Daily", "Weekly", "Monthly", "Annually"],
            state="readonly"
        )
        self.recurrence_dropdown.pack(fill=tk.X)

        # Buttons frame (at the very bottom)
        self.buttons_frame = ttk.Frame(form_frame)
        
        self.save_button = ttk.Button(self.buttons_frame, text="Save Task", command=self.save_task)
        self.save_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))

        self.clear_button = ttk.Button(self.buttons_frame, text="Clear Form", command=self.clear_form)
        self.clear_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5,0))

    def on_category_change(self, event):
        category = self.category_var.get()
        
        # First, unpack everything that might be shown
        self.priority_label.pack_forget()
        self.priority_dropdown.pack_forget()
        self.recurrence_frame.pack_forget()
        self.buttons_frame.pack_forget()
        
        if category == "Recurring":
            self.priority_var.set("")
            self.recurrence_frame.pack(fill=tk.X, pady=(10,0))
            self.date_label.config(text="Starting Date (YYYY-MM-DD):")
        elif category == "On-going":
            self.recurrence_var.set("")
            self.priority_label.pack(anchor=tk.W, pady=(10,0))
            self.priority_dropdown.pack(fill=tk.X)
            self.date_label.config(text="Due Date (YYYY-MM-DD):")
        else:
            self.priority_var.set("")
            self.recurrence_var.set("")
            self.date_label.config(text="Due Date (YYYY-MM-DD):")
            
        # Always show buttons at the bottom
        self.buttons_frame.pack(pady=(20,10), fill=tk.X)

    def save_task(self):
        title = self.task_name_entry.get().strip()
        description = self.description_text.get("1.0", tk.END).strip()
        date = self.date_entry.get().strip()
        category = self.category_var.get()
        priority = self.priority_var.get() if category == "On-going" else ""
        is_recurring = 1 if category == "Recurring" else 0
        recurrence_pattern = self.recurrence_var.get() if category == "Recurring" else None

        if not title:
            tkinter.messagebox.showerror("Error", "Task Name is required.")
            return

        if not date:
            error_msg = "Starting Date is required." if category == "Recurring" else "Due Date is required."
            tkinter.messagebox.showerror("Error", error_msg)
            return

        if category == "Recurring" and not recurrence_pattern:
            tkinter.messagebox.showerror("Error", "Please select a recurrence pattern for recurring tasks.")
            return

        try:
            AddTask(title, description, category, priority, date, is_recurring, 
                   self.user_id, recurrence_pattern)
            tkinter.messagebox.showinfo("Success", "Task saved successfully!")
            self.clear_form()
            UpdateMissedTasks(self.user_id)
            self.load_tasks()
            self.update_calendar_tasks()
        except Exception as e:
            tkinter.messagebox.showerror("Error", f"Failed to save task: {str(e)}")

    def clear_form(self):
        self.task_name_entry.delete(0, tk.END)
        self.description_text.delete("1.0", tk.END)
        self.date_entry.delete(0, tk.END)
        self.category_var.set("")
        self.priority_var.set("")
        self.recurrence_var.set("")
        
        # Hide optional elements
        self.priority_label.pack_forget()
        self.priority_dropdown.pack_forget()
        self.recurrence_frame.pack_forget()
        
        # Reset date label
        self.date_label.config(text="Due Date (YYYY-MM-DD):")
        
        # Ensure buttons are at the bottom
        self.buttons_frame.pack_forget()
        self.buttons_frame.pack(pady=(20,10), fill=tk.X)

    # --------------- Task List & Filtering -------------------

    def create_task_list(self):
        # Create a frame for filters with scrollbar
        list_container = ttk.Frame(self.right_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        filter_frame = ttk.Frame(list_container)
        filter_frame.pack(fill=tk.X, pady=(0,10))

        ttk.Label(filter_frame, text="Filter by Category:").pack(side=tk.LEFT, padx=(0,5))
        self.filter_category_var = tk.StringVar(value="All")
        self.filter_category_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_category_var,
            values=["All", "Recurring", "On-going"],
            state="readonly"
        )
        self.filter_category_dropdown.pack(side=tk.LEFT, padx=(0,15))
        self.filter_category_dropdown.bind("<<ComboboxSelected>>", lambda e: self.load_tasks())

        ttk.Label(filter_frame, text="Filter by Status:").pack(side=tk.LEFT, padx=(0,5))
        self.filter_status_var = tk.StringVar(value="All")
        self.filter_status_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_status_var,
            values=["All", "Pending", "Missed", "Done"],
            state="readonly"
        )
        self.filter_status_dropdown.pack(side=tk.LEFT, padx=(0,15))
        self.filter_status_dropdown.bind("<<ComboboxSelected>>", lambda e: self.load_tasks())

        ttk.Label(filter_frame, text="Filter by Priority:").pack(side=tk.LEFT, padx=(0,5))
        self.filter_priority_var = tk.StringVar(value="All")
        self.filter_priority_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_priority_var,
            values=["All", "Urgent", "Not Urgent"],
            state="readonly"
        )
        self.filter_priority_dropdown.pack(side=tk.LEFT, padx=(0,15))
        self.filter_priority_dropdown.bind("<<ComboboxSelected>>", lambda e: self.load_tasks())

        # Add action buttons frame
        action_frame = ttk.Frame(list_container)
        action_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Button for regular tasks
        self.mark_done_button = ttk.Button(action_frame, text="Mark as Done", command=self.mark_task_as_done)
        self.mark_done_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Button for recurring tasks
        self.mark_done_today_button = ttk.Button(action_frame, text="Done for Today", command=self.mark_recurring_done_today)
        self.mark_done_today_button.pack(side=tk.LEFT, padx=(0, 5))
        self.mark_done_today_button.configure(state="disabled")  # Initially disabled

        # Delete button
        self.delete_button = ttk.Button(action_frame, text="Delete Task", command=self.delete_task, style="Delete.TButton")
        self.delete_button.pack(side=tk.LEFT, padx=(0, 5))
        self.delete_button.configure(state="disabled")  # Initially disabled

        # Configure delete button style
        style = ttk.Style()
        style.configure("Delete.TButton", foreground="red")

        # Create a frame for the treeview and its scrollbar
        tree_frame = ttk.Frame(list_container)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Create the treeview scrollbar
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Store task IDs separately but don't show them
        self.task_ids = {}  # Dictionary to store task IDs
        
        columns = ("title", "date", "category", "priority", "status")
        self.task_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                     yscrollcommand=tree_scroll.set)
        
        # Configure the scrollbar
        tree_scroll.config(command=self.task_tree.yview)
        
        self.task_tree.heading("title", text="Task Name")
        self.task_tree.column("title", width=200)
        self.task_tree.heading("date", text="Due/Start Date")
        self.task_tree.column("date", width=100)
        self.task_tree.heading("category", text="Category")
        self.task_tree.column("category", width=100)
        self.task_tree.heading("priority", text="Priority")
        self.task_tree.column("priority", width=100)
        self.task_tree.heading("status", text="Status")
        self.task_tree.column("status", width=100)

        self.task_tree.pack(fill=tk.BOTH, expand=True)
        self.task_tree.bind('<<TreeviewSelect>>', self.on_task_select)

        self.load_tasks()

    def load_tasks(self):
        UpdateMissedTasks(self.user_id)
        for row in self.task_tree.get_children():
            self.task_tree.delete(row)
        
        self.task_ids.clear()  # Clear stored IDs

        category_filter = self.filter_category_var.get()
        status_filter = self.filter_status_var.get()
        priority_filter = self.filter_priority_var.get()

        try:
            tasks = GetTasksFiltered(self.user_id, category_filter, priority_filter)

            for task in tasks:
                task_id, title, date, category, priority, last_completed, today = task
                
                # Update the date label based on category
                date_label = date
                if category == "Recurring":
                    date_label = f"Started: {date}"

                # Determine the display status with icons
                if category == "Recurring":
                    if last_completed == today:
                        display_status = "✅ Completed Today"
                    else:
                        display_status = "⏳ Pending Today"
                elif category == "Done":
                    display_status = "✅ Completed"
                elif category == "Missed":
                    display_status = "❌ Overdue"
                    category = "On-going"  # Convert Missed category to On-going with Missed status
                else:
                    if priority == "Urgent":
                        display_status = "🔔 Active"
                    else:
                        display_status = "📝 Active"

                # Apply status filter
                if status_filter != "All":
                    if status_filter == "Done" and "Completed" not in display_status:
                        continue
                    elif status_filter == "Pending" and ("Active" not in display_status and "Pending" not in display_status):
                        continue
                    elif status_filter == "Missed" and "Overdue" not in display_status:
                        continue

                # Format priority display
                if priority:
                    if priority == "Urgent":
                        display_priority = "⚡ Urgent"
                    else:
                        display_priority = "🕒 Not Urgent"
                else:
                    display_priority = ""

                # Format category display
                if category == "Recurring":
                    display_category = "🔄 Recurring"
                else:
                    display_category = "📋 One-time"

                values = [title, date_label, display_category, display_priority, display_status]
                item_id = self.task_tree.insert("", tk.END, values=values)
                self.task_ids[item_id] = task_id

                # Add tags for row coloring based on status
                if "Completed" in display_status:
                    self.task_tree.item(item_id, tags=('completed',))
                elif "Overdue" in display_status:
                    self.task_tree.item(item_id, tags=('overdue',))
                elif "Urgent" in display_priority:
                    self.task_tree.item(item_id, tags=('urgent',))

        except Exception as e:
            tkinter.messagebox.showerror("Error", f"Failed to load tasks: {str(e)}")

    def on_task_select(self, event):
        selected_items = self.task_tree.selection()
        if selected_items:
            item = self.task_tree.item(selected_items[0])
            category = item['values'][2].replace("🔄 ", "").replace("📋 ", "")  # Remove icons for comparison
            status = item['values'][4]
            
            # Enable delete button when a task is selected
            self.delete_button.configure(state="normal")
            
            # Enable/disable appropriate buttons based on task type and status
            if "Recurring" in category:
                self.mark_done_button.configure(state="disabled")
                if "Completed Today" in status:
                    self.mark_done_today_button.configure(state="disabled")
                else:
                    self.mark_done_today_button.configure(state="normal")
            elif "One-time" in category:
                if "Completed" not in status:
                    self.mark_done_button.configure(state="normal")
                    self.mark_done_today_button.configure(state="disabled")
                else:
                    self.mark_done_button.configure(state="disabled")
                    self.mark_done_today_button.configure(state="disabled")
            else:
                self.mark_done_button.configure(state="disabled")
                self.mark_done_today_button.configure(state="disabled")
        else:
            self.mark_done_button.configure(state="disabled")
            self.mark_done_today_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")

    def mark_recurring_done_today(self):
        selected_items = self.task_tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        task_id = self.task_ids[item_id]  # Get the actual task ID
        category = self.task_tree.item(item_id)['values'][2]  # category is now at index 2
        
        if category == "Recurring":
            MarkRecurringTaskComplete(task_id)
            self.load_tasks()
            self.update_calendar_tasks()
            tkinter.messagebox.showinfo("Success", "Task marked as done for today!")

    def mark_task_as_done(self):
        selected_items = self.task_tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        task_id = self.task_ids[item_id]  # Get the actual task ID
        category = self.task_tree.item(item_id)['values'][2]  # category is now at index 2
        
        if category == "Recurring":
            MarkRecurringTaskComplete(task_id)
            self.load_tasks()
            tkinter.messagebox.showinfo("Success", "Recurring task marked as done for today!")
        elif category in ["On-going", "Missed"]:
            UpdateTaskStatus(task_id, "Done")
            self.load_tasks()
            tkinter.messagebox.showinfo("Success", "Task marked as done!")

    def delete_task(self):
        selected_items = self.task_tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        task_id = self.task_ids[item_id]  # Get the actual task ID
        task_title = self.task_tree.item(item_id)['values'][0]  # title is now at index 0
        
        # Show confirmation dialog with task title
        if tkinter.messagebox.askyesno("Delete Task", 
                                     f"Are you sure you want to delete the task:\n\n{task_title}?",
                                     icon='warning'):
            try:
                DeleteTask(task_id, self.user_id)
                self.load_tasks()
                self.update_calendar_tasks()
                tkinter.messagebox.showinfo("Success", "Task deleted successfully!")
            except Exception as e:
                tkinter.messagebox.showerror("Error", f"Failed to delete task: {str(e)}")

if __name__ == "__main__":
    login_win = LoginWindow()
    login_win.mainloop()