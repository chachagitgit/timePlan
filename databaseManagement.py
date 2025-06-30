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

        # Create priority table
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS priority (
                priority_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                priority_name TEXT    NOT NULL UNIQUE,
                priority_level INTEGER NOT NULL
            );
        """)
        
        # Insert default priorities if they don't exist
        default_priorities = [
            ("Urgent", 1),
            ("Not urgent", 2)
        ]
        for priority_name, level in default_priorities:
            self._execute_query(
                "INSERT OR IGNORE INTO priority (priority_name, priority_level) VALUES (?, ?)",
                (priority_name, level)
            )

        # Create tasks table (STATUS COLUMN REMOVED IN PREVIOUS STEP, REMAINS GONE)
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                description TEXT,
                priority_id INTEGER REFERENCES priority (priority_id),
                due_date    DATE,
                user_id     INTEGER NOT NULL DEFAULT 1,
                category_id INTEGER REFERENCES task_category (category_id) NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
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
    def add_task(self, user_id, title, description=None, priority_name=None, due_date=None, category_id=1):
        """Add a new task and return the new task ID on success."""
        description = description if description else None
        due_date = due_date if due_date else None # due_date should be 'YYYY-MM-DD' format
        
        # Convert priority name to priority_id
        priority_id = None
        if priority_name:
            priority_id = self.get_priority_id_by_name(priority_name)
            if not priority_id:
                # Default to "Not urgent" if invalid priority name
                priority_id = self.get_priority_id_by_name("Not urgent")

        query = """
            INSERT INTO tasks (user_id, title, description, priority_id, due_date, category_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        success = self._execute_query(query, (user_id, title, description, priority_id, due_date, category_id))
        
        if success:
            # Get the ID of the last inserted row
            last_id = self._fetch_one("SELECT last_insert_rowid()")
            return last_id[0] if last_id else None
        return None
        
    def get_tasks(self, user_id, filter_type='All Tasks'):
        query = """
            SELECT t.id, t.title, t.description, p.priority_name, t.due_date, tc.category_name
            FROM tasks t 
            JOIN task_category tc ON t.category_id = tc.category_id 
            LEFT JOIN priority p ON t.priority_id = p.priority_id
        """ \
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
            # On-going: display all on-going tasks that are not past due
            if ongoing_category_id:
                query += """AND t.category_id = ? 
                    AND (t.due_date IS NULL 
                         OR DATE(t.due_date) >= DATE(?))"""
                params.extend([ongoing_category_id, current_local_date_str])
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
            query += "ORDER BY CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END, t.due_date ASC, p.priority_level ASC"
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
            priority_id = self.get_priority_id_by_name(priority)
            if priority_id:
                updates.append("priority_id = ?")
                params.append(priority_id)
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

    def update_task(self, task_id, title, description, priority_name, due_date, category_id):
        """Update all fields of a task at once."""
        # Convert priority name to priority_id
        priority_id = None
        if priority_name:
            priority_id = self.get_priority_id_by_name(priority_name)
            if not priority_id:
                priority_id = self.get_priority_id_by_name("Not urgent")

        # Parse the due date
        due_date_obj = self._parse_date(due_date)
        formatted_date = self._format_date(due_date_obj)

        query = """
            UPDATE tasks 
            SET title = ?, 
                description = ?, 
                priority_id = ?, 
                due_date = ?, 
                category_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        return self._execute_query(query, (title, description, priority_id, formatted_date, category_id, task_id))

    # --- Priority Management Methods ---
    def get_priority_id_by_name(self, priority_name):
        """Get priority ID from priority name."""
        query = "SELECT priority_id FROM priority WHERE priority_name = ?"
        result = self._fetch_one(query, (priority_name,))
        return result[0] if result else None

    def get_priority_name_by_id(self, priority_id):
        """Get priority name from priority ID."""
        query = "SELECT priority_name FROM priority WHERE priority_id = ?"
        result = self._fetch_one(query, (priority_id,))
        return result[0] if result else None

    def get_all_priorities(self):
        """Get all priority names ordered by priority level."""
        query = "SELECT priority_name FROM priority ORDER BY priority_level"
        results = self._fetch_all(query)
        return [row[0] for row in results] if results else ["Not urgent", "Urgent"]  # Fallback to defaults if query fails

    def _get_ph_timezone(self):
        """Get Philippines timezone"""
        return pytz.timezone('Asia/Manila')
    
    def _get_current_local_date(self):
        """Get current date in PH timezone"""
        ph_tz = self._get_ph_timezone()
        return datetime.now(ph_tz).date()
    
    def _parse_date(self, date_str):
        """Convert string date to datetime.date object"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            print(f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD")
            return None
            
    def _format_date(self, date_obj):
        """Convert datetime.date object to string"""
        if not date_obj:
            return None
        try:
            return date_obj.strftime('%Y-%m-%d')
        except AttributeError:
            print(f"Invalid date object: {date_obj}")
            return None

    def update_past_due_tasks(self):
        """Move all past due On-going tasks to the Missed category."""
        # Get the category IDs
        ongoing_cat_id_row = self._fetch_one("SELECT category_id FROM task_category WHERE category_name = ?", ("On-going",))
        missed_cat_id_row = self._fetch_one("SELECT category_id FROM task_category WHERE category_name = ?", ("Missed",))
        
        if not ongoing_cat_id_row or not missed_cat_id_row:
            print("Error: Could not find required categories.")
            return False
            
        ongoing_category_id = ongoing_cat_id_row[0]
        missed_category_id = missed_cat_id_row[0]
        
        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone).strftime('%Y-%m-%d')
        
        # Update all past due tasks from On-going to Missed
        query = """
            UPDATE tasks 
            SET category_id = ?
            WHERE category_id = ? 
            AND due_date < ?
            AND due_date IS NOT NULL
        """
        
        return self._execute_query(query, (missed_category_id, ongoing_category_id, current_local_date))

# For testing the DatabaseManager separately
if __name__ == '__main__':
    db_manager = DatabaseManager()
    print("Database initialized successfully.")
    db_manager._close()