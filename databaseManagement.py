import sqlite3
from datetime import datetime, timedelta
import pytz # Make sure pytz is installed: pip install pytz

class DatabaseManager:
    def __init__(self, db_name='timePlanDB.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self._connect()
        self.create_tables()

    def _connect(self, retries=3):
        for i in range(retries):
            try:
                self.conn = sqlite3.connect(self.db_name)
                self.cursor = self.conn.cursor()
                print(f"Connected to database: {self.db_name}")
                return True
            except sqlite3.Error as e:
                print(f"Database connection error (attempt {i+1}/{retries}): {e}")
                if i < retries - 1:
                    import time
                    time.sleep(1) # Wait a bit before retrying
        self.conn = None
        self.cursor = None
        return False

    def _close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

    def _execute_query(self, query, params=()):
        if not self.conn:
            if not self._connect(): # Attempt to reconnect if not connected
                print("Failed to execute query: Not connected to database.")
                return False
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database query error: {e} for query: {query} with params: {params}")
            self.conn.rollback() # Rollback changes on error
            return False

    def _fetch_all(self, query, params=()):
        if not self.conn:
            if not self._connect():
                return []
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database fetch error: {e} for query: {query} with params: {params}")
            return []

    def _fetch_one(self, query, params=()):
        if not self.conn:
            if not self._connect():
                return None
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Database fetch error: {e} for query: {query} with params: {params}")
            return None

    def create_tables(self):
        # Create users table
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    UNIQUE NOT NULL,
                password    TEXT    NOT NULL
            );
        """)

        # Create task_category table
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS task_category (
                category_id   INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                category_name TEXT    NOT NULL UNIQUE
            );
        """)

        # Create tasks table (STATUS COLUMN REMOVED IN PREVIOUS STEP, REMAINS GONE)
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                description TEXT,
                priority    TEXT,
                due_date    TEXT,
                user_id     INTEGER NOT NULL DEFAULT 1,
                category_id INTEGER REFERENCES task_category (category_id) NOT NULL
            );
        """)

        # Create recurring_tasks table (No status column here either)
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS recurring_tasks (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                title                 TEXT    NOT NULL,
                description           TEXT,
                start_date            TEXT,
                recurrence_pattern    TEXT    NOT NULL,
                last_completed_date TEXT,
                user_id               INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        """)
        
        # Add a default user if none exists (for testing/initial setup)
        if not self._fetch_one("SELECT * FROM users WHERE id = 1"):
            self.add_user("default_user", "password123")
        
        # Add default categories: "On-going", "Missed", "Completed"
        default_categories = ["On-going", "Missed", "Completed"]
        existing_categories = [row[0] for row in self.get_task_categories()]
        for cat in default_categories:
            if cat not in existing_categories:
                self.add_category(cat)


    # --- CRUD operations for Tasks ---
    # add_task method remains unchanged as it never had a 'status' argument after previous removal
    def add_task(self, user_id, title, description=None, priority=None, due_date=None, category_id=1):
        """Add a new task and return the new task ID on success."""
        description = description if description else None
        priority = priority if priority else None
        due_date = due_date if due_date else None # due_date should be 'YYYY-MM-DD' format

        query = """
            INSERT INTO tasks (user_id, title, description, priority, due_date, category_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        success = self._execute_query(query, (user_id, title, description, priority, due_date, category_id))
        
        if success:
            # Get the ID of the last inserted row
            last_id = self._fetch_one("SELECT last_insert_rowid()")
            return last_id[0] if last_id else None
        return None
        
    def get_tasks(self, user_id, filter_type='All Tasks'):
        query = "SELECT t.id, t.title, t.description, t.priority, t.due_date, tc.category_name " \
                "FROM tasks t JOIN task_category tc ON t.category_id = tc.category_id " \
                "WHERE t.user_id = ? "
        params = [user_id]
        
        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone)
        current_local_date_str = current_local_date.strftime('%Y-%m-%d')
        
        # Get the IDs of important categories
        completed_cat_id_row = self._fetch_one("SELECT category_id FROM task_category WHERE category_name = ?", ("Completed",))
        completed_category_id = completed_cat_id_row[0] if completed_cat_id_row else None
        
        ongoing_cat_id_row = self._fetch_one("SELECT category_id FROM task_category WHERE category_name = ?", ("On-going",))
        ongoing_category_id = ongoing_cat_id_row[0] if ongoing_cat_id_row else None
        
        missed_cat_id_row = self._fetch_one("SELECT category_id FROM task_category WHERE category_name = ?", ("Missed",))
        missed_category_id = missed_cat_id_row[0] if missed_cat_id_row else None

        # Apply filters based on the filter type
        if filter_type == 'Today':
            # Today: display the on-going tasks for today
            query += "AND t.due_date = ? AND tc.category_name = 'On-going' "
            params.append(current_local_date_str)
        elif filter_type == 'Next 7 Days':
            # Next 7 days: display the on-going tasks for the next 7 days
            next_7_days_str = (current_local_date + timedelta(days=7)).strftime('%Y-%m-%d')
            query += "AND t.due_date BETWEEN ? AND ? AND tc.category_name = 'On-going' "
            params.extend([current_local_date_str, next_7_days_str])
        elif filter_type == 'All Tasks':
            # All tasks: display all tasks, regardless of category (no additional filter)
            pass
        elif filter_type == 'On-going':
            # On-going: display all on-going tasks
            if ongoing_category_id:
                query += "AND t.category_id = ? "
                params.append(ongoing_category_id)
        elif filter_type == 'Completed':
            # Completed: display all completed tasks
            if completed_category_id:
                query += "AND t.category_id = ? "
                params.append(completed_category_id)
        elif filter_type == 'Missed':
            # Missed: display all missed tasks
            if missed_category_id:
                query += "AND t.category_id = ? "
                params.append(missed_category_id)

        # Add ordering by date
        # For all filters, sort by due date (nearest first)
        # Tasks with NULL due_date will be at the end
        if filter_type in ['All Tasks', 'On-going', 'Today', 'Next 7 Days']:
            # For tasks that need closest due date first
            query += "ORDER BY CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END, t.due_date ASC, t.priority DESC"
        elif filter_type in ['Completed', 'Missed']:
            # For completed/missed tasks, sort by date (could be oldest first or newest first)
            query += "ORDER BY t.due_date DESC" # Most recently completed/missed first
        
        return self._fetch_all(query, params)

    def update_task_details(self, task_id, title=None, description=None, priority=None, due_date=None, category_id=None):
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description if description else None)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        if due_date is not None:
            updates.append("due_date = ?")
            params.append(due_date if due_date else None)
        if category_id is not None:
            updates.append("category_id = ?")
            params.append(category_id)
        
        if not updates:
            print("No details to update.")
            return False

        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        params.append(task_id)
        return self._execute_query(query, tuple(params))

    # New method to update a task's category (for "completing" or "uncompleting" tasks)
    def update_task_category(self, task_id, new_category_id):
        query = "UPDATE tasks SET category_id = ? WHERE id = ?"
        return self._execute_query(query, (new_category_id, task_id))

    def delete_task(self, task_id):
        query = "DELETE FROM tasks WHERE id = ?"
        return self._execute_query(query, (task_id,))

    # --- CRUD operations for Task Categories ---
    def get_task_categories(self):
        query = "SELECT category_name, category_id FROM task_category ORDER BY category_name"
        return self._fetch_all(query)

    def add_category(self, category_name):
        query = "INSERT INTO task_category (category_name) VALUES (?)"
        return self._execute_query(query, (category_name,))

    def get_category_id_by_name(self, category_name):
        query = "SELECT category_id FROM task_category WHERE category_name = ?"
        result = self._fetch_one(query, (category_name,))
        return result[0] if result else None

    # --- CRUD operations for Users ---
    def add_user(self, username, password):
        query = "INSERT INTO users (username, password) VALUES (?, ?)"
        return self._execute_query(query, (username, password))

    def get_user_by_username(self, username):
        query = "SELECT id, username, password FROM users WHERE username = ?"
        return self._fetch_one(query, (username,))

    def update_task(self, task_id, title, description, priority, due_date, category_id):
        """Update all fields of a task at once."""
        query = """
            UPDATE tasks 
            SET title = ?, description = ?, priority = ?, due_date = ?, category_id = ?
            WHERE id = ?
        """
        return self._execute_query(query, (title, description, priority, due_date, category_id, task_id))

# Example usage (for testing the DatabaseManager separately)
if __name__ == '__main__':
    db_manager = DatabaseManager()

    default_user_info = db_manager.get_user_by_username("default_user")
    user_id = default_user_info[0] if default_user_info else 1

    # Get category IDs by name
    # Ensure these category names match your database exactly
    on_going_cat_id = db_manager.get_category_id_by_name("On-going")
    missed_cat_id = db_manager.get_category_id_by_name("Missed")
    completed_cat_id = db_manager.get_category_id_by_name("Completed")

    print("\n--- Adding some sample tasks ---")
    # Assign tasks to 'On-going' or 'Missed' based on due date
    # For tasks without a specific category in mind, 'On-going' is a good default
    
    # Task for today or future (On-going)
    db_manager.add_task(user_id, "Buy groceries", "Milk, eggs, bread", "Urgent", "2025-06-21", on_going_cat_id)
    db_manager.add_task(user_id, "Call mom", "Check in on her", "Not urgent", "2025-06-20", on_going_cat_id)
    db_manager.add_task(user_id, "Read a book", "Chapter 5", "Not urgent", None, on_going_cat_id) # No due date

    # Task for a past date (Missed)
    db_manager.add_task(user_id, "Schedule dentist appointment", None, "Not urgent", "2025-06-18", missed_cat_id) 

    # Add a task that starts as "Completed"
    if completed_cat_id:
        db_manager.add_task(user_id, "Submit expense report", "Q2 expenses", "Not urgent", "2025-06-15", completed_cat_id)
        print("Added 'Submit expense report' directly to Completed category.")

    print("\n--- All Tasks ---")
    all_tasks = db_manager.get_tasks(user_id, 'All Tasks')
    for task in all_tasks:
        print(task)

    print("\n--- Today's Tasks (excluding completed) ---")
    today_tasks = db_manager.get_tasks(user_id, 'Today')
    for task in today_tasks:
        print(task)
    
    print("\n--- Next 7 Days Tasks (excluding completed) ---")
    next_7_tasks = db_manager.get_tasks(user_id, 'Next 7 Days')
    for task in next_7_tasks:
        print(task)

    print("\n--- On-going Tasks (excluding completed) ---")
    ongoing_tasks = db_manager.get_tasks(user_id, 'On-going')
    for task in ongoing_tasks:
        print(task)

    print("\n--- Completed Tasks (based on category) ---")
    completed_tasks = db_manager.get_tasks(user_id, 'Completed')
    for task in completed_tasks:
        print(task)

    print("\n--- Missed Tasks (excluding completed) ---")
    missed_tasks = db_manager.get_tasks(user_id, 'Missed')
    for task in missed_tasks:
        print(task)
    
    # --- Test updating category to mark as complete/incomplete ---
    print("\n--- Marking 'Buy groceries' as Completed ---")
    task_to_mark_id = None
    for task in all_tasks:
        if task[1] == "Buy groceries":
            task_to_mark_id = task[0]
            break
    
    if task_to_mark_id and completed_cat_id:
        db_manager.update_task_category(task_to_mark_id, completed_cat_id)
        print(f"Task ID {task_to_mark_id} ('Buy groceries') marked as Completed.")
        print("\n--- All Tasks (after marking 'Buy groceries' as completed) ---")
        for task in db_manager.get_tasks(user_id, 'All Tasks'):
            print(task)
        print("\n--- Completed Tasks (after marking 'Buy groceries' as completed) ---")
        for task in db_manager.get_tasks(user_id, 'Completed'):
            print(task)
    else:
        print("Could not find 'Buy groceries' task or 'Completed' category.")

    # --- Test marking 'Submit expense report' as Incomplete (moving to On-going) ---
    print("\n--- Marking 'Submit expense report' as Incomplete (moving to On-going) ---")
    task_to_unmark_id = None
    # Re-fetch all tasks to get current IDs
    current_all_tasks = db_manager.get_tasks(user_id, 'All Tasks')
    for task in current_all_tasks:
        if task[1] == "Submit expense report":
            task_to_unmark_id = task[0]
            break
    
    if task_to_unmark_id and on_going_cat_id:
        db_manager.update_task_category(task_to_unmark_id, on_going_cat_id)
        print(f"Task ID {task_to_unmark_id} ('Submit expense report') marked as Incomplete (moved to On-going).")
        print("\n--- All Tasks (after marking 'Submit expense report' as incomplete) ---")
        for task in db_manager.get_tasks(user_id, 'All Tasks'):
            print(task)
        print("\n--- Completed Tasks (after marking 'Submit expense report' as incomplete) ---")
        for task in db_manager.get_tasks(user_id, 'Completed'):
            print(task)
    else:
        print("Could not find 'Submit expense report' task or 'On-going' category.")

    db_manager._close()