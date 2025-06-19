import customtkinter as ctk
import os
from PIL import Image
from databaseManagement import DatabaseManager
from datetime import datetime, timedelta
import pytz

# Optional: For CTkCalendar, if you have it installed. If not, tkcalendar will be used.
try:
    from CTkCalendar import CTkCalendar
    CTKCALENDAR_AVAILABLE = True
except ImportError:
    from tkcalendar import Calendar
    CTKCALENDAR_AVAILABLE = False
    print("CTkCalendar not found, falling back to tkcalendar. Install CTkCalendar for better integration.")


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class TimePlanApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TimePlan")
        self.geometry("1200x700")
        self.configure(bg="#F8F3FB")

        self.sidebar_expanded = True
        self.sidebar_width = 240
        self.sidebar_collapsed_width = 64

        self.db_manager = DatabaseManager()
        self.current_user_id = 1 

        # Pre-fetch category IDs
        self.completed_category_id = self.db_manager.get_category_id_by_name("Completed")
        self.on_going_category_id = self.db_manager.get_category_id_by_name("On-going") # For un-completing tasks
        
        if not self.completed_category_id:
            print("ERROR: 'Completed' category not found. Please ensure databaseManagement.py initializes it.")
        if not self.on_going_category_id:
            print("ERROR: 'On-going' category not found. Please ensure databaseManagement.py initializes it.")

        # Load sidebar icons (rest of the icon loading code)
        self.icons = {}
        icon_folder = os.path.join(os.path.dirname(__file__), "icons")
        icon_files = {
            "Tasks": "tasks.png", "Calendar": "calendar.png", "Habit": "habit2.png",
            "Add Task": "addTask.png", "Search Task": "search.png", "Profile": "profile.png",
            "Sign Out": "signOut.png"
        }
        for key, filename in icon_files.items():
            path = os.path.join(icon_folder, filename)
            if os.path.exists(path):
                img = Image.open(path)
                w, h = img.size
                side = min(w, h)
                left = (w - side) // 2
                top = (h - side) // 2
                right = left + side
                bottom = top + side
                img = img.crop((left, top, right, bottom)).resize((56, 56), Image.LANCZOS)
                self.icons[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(56, 56))
            else:
                print(f"Warning: Sidebar icon not found: {path}")
                self.icons[key] = None

        self.nav_icons = {}
        nav_icon_files = {
            "Today": "today.png", "Next 7 Days": "next7Days.png", "All Tasks": "allTasks.png",
            "On-going": "onGoing.png", "Completed": "completed.png", "Missed": "missing.png"
        }
        icon_size_nav = (40, 40)
        for key, filename in nav_icon_files.items():
            path = os.path.join(icon_folder, filename)
            if os.path.exists(path):
                img = Image.open(path)
                w, h = img.size
                side = min(w, h)
                left = (w - side) // 2
                top = (h - side) // 2
                right = left + side
                bottom = top + side
                img = img.crop((left, top, right, bottom))
                img = img.resize(icon_size_nav, Image.LANCZOS)
                self.nav_icons[key] = ctk.CTkImage(light_image=img, dark_image=img, size=icon_size_nav)
            else:
                print(f"Warning: Navigation icon not found: {path}")
                self.nav_icons[key] = None

        logo_path = os.path.join(icon_folder, "logoKuno.png")
        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path)
            w, h = logo_img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            right = left + side
            bottom = top + side
            logo_img = logo_img.crop((left, top, right, bottom)).resize((40, 40), Image.LANCZOS)
            self.logo_image = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(40, 40))
        else:
            self.logo_image = None

        self.sidebar = ctk.CTkFrame(self, width=self.sidebar_width, corner_radius=0, fg_color="#C576E0")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        sidebar_logo_frame = ctk.CTkFrame(self.sidebar, fg_color="#C576E0")
        sidebar_logo_frame.pack(fill="x", pady=(8, 0), padx=8)
        if self.logo_image:
            ctk.CTkLabel(sidebar_logo_frame, image=self.logo_image, text="", width=40, height=40).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            sidebar_logo_frame,
            text="TimePlan",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white",
            bg_color="#C576E0"
        ).pack(side="left", pady=0)

        self.navbar = ctk.CTkFrame(self, width=300, fg_color="#F3E6F8")
        self.navbar_nav_items = []
        nav_items_data = [
            "Today", "Next 7 Days", "All Tasks",
            "On-going", "Completed", "Missed"
        ]
        for name in nav_items_data:
            btn = ctk.CTkButton(
                self.navbar,
                text=name,
                image=self.nav_icons.get(name),
                compound="left",
                width=180,
                height=40,
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color="transparent",
                text_color="#A85BC2",
                hover_color="#E5C6F2",
                anchor="w" 
            )
            btn.pack(pady=6, anchor="w") 
            self.navbar_nav_items.append(btn)

            if name == "Today":
                btn.configure(command=lambda: self.show_tasks_page('Today'))
            elif name == "Next 7 Days":
                btn.configure(command=lambda: self.show_tasks_page('Next 7 Days'))
            elif name == "All Tasks":
                btn.configure(command=lambda: self.show_tasks_page('All Tasks'))
            elif name == "On-going":
                btn.configure(command=lambda: self.show_tasks_page('On-going'))
            elif name == "Completed":
                btn.configure(command=lambda: self.show_tasks_page('Completed'))
            elif name == "Missed":
                btn.configure(command=lambda: self.show_tasks_page('Missed'))

        self.content = ctk.CTkFrame(self, fg_color="#F8F3FB")
        self.content.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        self.sidebar_buttons = []
        sidebar_buttons = [
            ("Tasks", lambda: self.show_tasks_page('All Tasks')),
            ("Calendar", self.show_calendar_page),
            ("Habit", None),
            ("Add Task", self.show_add_task_page),
            ("Search Task", None),
            ("Profile", None),
            ("Sign Out", None)
        ]
        for btn_text, btn_cmd in sidebar_buttons:
            b = ctk.CTkButton(
                self.sidebar,
                text=btn_text,
                image=self.icons.get(btn_text),
                compound="left",
                width=200,
                height=60,
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color="#C576E0",
                hover_color="#A85BC2",
                text_color="white",
                anchor="w",
                command=btn_cmd
            )
            b.pack(pady=2, padx=8, fill="none")
            b.pack_propagate(False)
            self.sidebar_buttons.append(b)

        self.collapse_btn = ctk.CTkButton(
            self,
            text="◀",
            width=24,
            height=48,
            fg_color="#C576E0",
            hover_color="#A85BC2",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=0,
            border_width=0,
            command=self.toggle_sidebar
        )
        
        self.position_collapse_button()
        self.bind("<Configure>", self.on_window_configure)

        self.show_tasks_page('All Tasks')

    def position_collapse_button(self):
        self.update_idletasks()
        current_width = self.sidebar_width if self.sidebar_expanded else self.sidebar_collapsed_width
        x_pos = current_width
        self.collapse_btn.place(x=x_pos, rely=0.5, anchor="w")

    def on_window_configure(self, event):
        if event.widget == self:
            self.position_collapse_button()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_tasks_page(self, filter_type='All Tasks'):
        self.navbar.pack_forget()
        self.navbar.pack(side="left", fill="y", padx=(40, 0))

        self.content.pack_forget()
        self.content.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        
        self.clear_content()

        ctk.CTkLabel(
            self.content,
            text=f"{filter_type} Tasks",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#A85BC2"
        ).pack(anchor="nw", pady=(10, 0), padx=10)

        self.task_scroll_frame = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.task_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        tasks = self.db_manager.get_tasks(user_id=self.current_user_id, filter_type=filter_type)

        if not tasks:
            ctk.CTkLabel(self.task_scroll_frame, text="No tasks found for this filter.",
                         font=ctk.CTkFont(size=16), text_color="#6A057F").pack(pady=20)
            return

        # Define colors based on new status interpretation
        MISSED_BG_COLOR = "#FFCDD2" # Light Red
        COMPLETED_BG_COLOR = "#C8E6C9" # Light Green
        ONGOING_BG_COLOR = "white" # Default for uncompleted, non-missed tasks

        philippines_timezone = pytz.timezone('Asia/Manila')
        current_local_date = datetime.now(philippines_timezone).date()

        for i, task in enumerate(tasks):
            # Unpack task data: (id, title, description, priority, due_date, category_name)
            if len(task) != 6: # Ensure correct unpacking for 6 elements
                print(f"Error: Task {i} has unexpected number of elements: {len(task)}. Expected 6. Task data: {task}")
                continue
            
            task_id, title, description, priority, due_date, category_name = task

            frame_bg_color = ONGOING_BG_COLOR
            title_color = "#333333" # Default text color

            is_completed_by_category = (category_name == "Completed")
            is_missed = False

            if not is_completed_by_category and due_date: # Only check for missed if not already completed
                try:
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                    if due_date_obj < current_local_date:
                        is_missed = True
                except ValueError:
                    pass

            # Determine colors based on priority: Completed > Missed > On-going
            if is_completed_by_category:
                frame_bg_color = COMPLETED_BG_COLOR
                title_color = "gray" # Grey out completed tasks
            elif is_missed:
                frame_bg_color = MISSED_BG_COLOR
                title_color = "red" 
            # Else, it remains ONGOING_BG_COLOR and default title_color

            task_frame = ctk.CTkFrame(self.task_scroll_frame, fg_color=frame_bg_color, corner_radius=10,
                                      border_width=1, border_color="#E5C6F2")
            task_frame.pack(fill="x", pady=5, padx=5)

            task_frame.grid_columnconfigure(0, weight=0) # Checkbox
            task_frame.grid_columnconfigure(1, weight=1) # Title, desc, priority
            task_frame.grid_columnconfigure(2, weight=0) # Category, Due Date
            task_frame.grid_rowconfigure(0, weight=0)
            task_frame.grid_rowconfigure(1, weight=0)
            task_frame.grid_rowconfigure(2, weight=1)

            # Re-introduce checkbox for completion
            status_var = ctk.StringVar(value="on" if is_completed_by_category else "off")
            status_checkbox = ctk.CTkCheckBox(task_frame, text="", variable=status_var,
                                              onvalue="on", offvalue="off",
                                              command=lambda tid=task_id, svar=status_var, current_cat_name=category_name: self.toggle_task_completion(tid, svar, current_cat_name, filter_type))
            status_checkbox.grid(row=0, column=0, rowspan=3, padx=(10,0), pady=10, sticky="nsew")

            ctk.CTkLabel(task_frame, text=title, font=ctk.CTkFont(size=18, weight="bold"),
                         text_color=title_color, anchor="w", wraplength=400
                         ).grid(row=0, column=1, padx=(10, 5), pady=(10,0), sticky="ew")

            if priority:
                display_priority_text = "⚠️ Urgent" if priority == "Urgent" else "Not urgent"
                ctk.CTkLabel(task_frame, text=display_priority_text, font=ctk.CTkFont(size=14),
                             text_color=title_color, anchor="w"
                             ).grid(row=1, column=1, padx=(10, 5), pady=(0, 5), sticky="ew")

            if description:
                ctk.CTkLabel(task_frame, text=description, font=ctk.CTkFont(size=14),
                             text_color=title_color, anchor="nw", wraplength=400
                             ).grid(row=2, column=1, padx=(10, 5), pady=(0, 10), sticky="new")
            else:
                ctk.CTkLabel(task_frame, text="", font=ctk.CTkFont(size=1),
                             text_color=title_color, anchor="w").grid(row=2, column=1, padx=(10, 5), pady=(0, 0), sticky="ew")

            if category_name:
                ctk.CTkLabel(task_frame, text=category_name, font=ctk.CTkFont(size=12, weight="bold"),
                             text_color="#666666", anchor="ne", justify="right"
                             ).grid(row=0, column=2, padx=10, pady=(10,0), sticky="ne")

            if due_date:
                try:
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                    if due_date_obj == current_local_date:
                        formatted_date_str = "Due: Today"
                    elif due_date_obj == (current_local_date + timedelta(days=1)):
                        formatted_date_str = "Due: Tomorrow"
                    else:
                        formatted_date_str = f"Due: {due_date_obj.strftime('%b %d, %Y')}"
                except ValueError:
                    formatted_date_str = "Due: Invalid Date"

                ctk.CTkLabel(task_frame, text=formatted_date_str, font=ctk.CTkFont(size=12),
                             text_color="#666666", anchor="ne", justify="right"
                             ).grid(row=1, column=2, padx=10, pady=(0,10), sticky="ne")

    def toggle_task_completion(self, task_id, status_var, current_category_name, current_filter_type):
        new_category_id = None
        if status_var.get() == "on": # Task is being marked as Completed
            if self.completed_category_id:
                new_category_id = self.completed_category_id
            else:
                ctk.CTkMessageBox(title="Error", message="Could not find 'Completed' category. Task not updated.", icon="warning").show()
                status_var.set("off") # Revert checkbox state
                return
        else: # Task is being marked as Incomplete
            if self.on_going_category_id: # Revert to "On-going"
                new_category_id = self.on_going_category_id
            else:
                ctk.CTkMessageBox(title="Error", message="Could not find 'On-going' category. Task not updated.", icon="warning").show()
                status_var.set("on") # Revert checkbox state
                return

        if self.db_manager.update_task_category(task_id, new_category_id):
            self.show_tasks_page(current_filter_type) # Refresh the current task view to reflect changes
        else:
            ctk.CTkMessageBox(title="Error", message="Failed to update task status in database.", icon="cancel").show()
            status_var.set("off" if status_var.get() == "on" else "on") # Revert checkbox on failure

    def show_calendar_page(self):
        self.navbar.pack_forget()
        self.content.pack_forget()
        self.content.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.clear_content()

        ctk.CTkLabel(self.content, text="Calendar View", font=ctk.CTkFont(size=24, weight="bold"), text_color="#A85BC2").pack(pady=20)
        
        if CTKCALENDAR_AVAILABLE:
            cal = ctk.CTkCalendar(self.content, width=900, height=600, border_width=0,
                                  fg_color="white", button_color="#A85BC2", button_hover_color="#C576E0",
                                  header_light_text_color="black", week_header_light_text_color="black")
            cal.pack(fill="both", expand=True, padx=10, pady=10)
        else:
            cal = Calendar(self.content, selectmode='day', date_pattern='yyyy-mm-dd',
                           background="white", selectbackground="#C576E0",
                           othermonthforeground="gray", normalforeground="black",
                           weekendbackground="white", weekendforeground="#A85BC2")
            cal.pack(fill="both", expand=True, padx=10, pady=10)

    def show_add_task_page(self):
        self.navbar.pack_forget()
        self.content.pack_forget()
        self.content.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.clear_content()

        ctk.CTkLabel(
            self.content,
            text="Add New Task",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#A85BC2"
        ).pack(anchor="nw", pady=(10, 0), padx=10)

        form_frame = ctk.CTkFrame(self.content, fg_color="white", corner_radius=10, padx=20, pady=20)
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)
        form_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Title:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.task_title_entry = ctk.CTkEntry(form_frame, placeholder_text="Task title", width=300)
        self.task_title_entry.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(form_frame, text="Description:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.task_description_entry = ctk.CTkEntry(form_frame, placeholder_text="Optional description", width=300)
        self.task_description_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Priority:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.task_priority_optionmenu = ctk.CTkOptionMenu(form_frame, values=["Urgent", "Not urgent"])
        self.task_priority_optionmenu.set("Not urgent")
        self.task_priority_optionmenu.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Due Date:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.task_due_date_entry = ctk.CTkEntry(form_frame, placeholder_text="YYYY-MM-DD (optional)", width=300)
        self.task_due_date_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Category:", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        
        # Get all categories and filter out 'Completed' for new task entry default
        # Assuming new tasks will start as "On-going" or "Missed"
        self.category_names = [cat[0] for cat in self.db_manager.get_task_categories() if cat[0] not in ["Completed", "Missed"]]
        self.task_category_optionmenu = ctk.CTkOptionMenu(form_frame, values=self.category_names)
        
        if "On-going" in self.category_names: # Set 'On-going' as default if available
            self.task_category_optionmenu.set("On-going")
        elif self.category_names: # Otherwise, set the first available category
            self.task_category_optionmenu.set(self.category_names[0])
        else: # No categories available
            self.task_category_optionmenu.set("No Categories")
            self.task_category_optionmenu.configure(state="disabled")

        self.task_category_optionmenu.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(form_frame, text="Add Task", command=self.add_new_task,
                      font=ctk.CTkFont(size=16, weight="bold"),
                      fg_color="#A85BC2", hover_color="#C576E0").grid(row=5, column=0, columnspan=2, pady=20)

    def add_new_task(self):
        title = self.task_title_entry.get()
        description = self.task_description_entry.get()
        priority = self.task_priority_optionmenu.get()
        due_date = self.task_due_date_entry.get()
        category_name = self.task_category_optionmenu.get()

        if not title:
            ctk.CTkMessageBox(title="Error", message="Task title cannot be empty.", icon="warning").show()
            return
        
        if due_date:
            try:
                datetime.strptime(due_date, '%Y-%m-%d')
            except ValueError:
                ctk.CTkMessageBox(title="Error", message="Due date must be in YYYY-MM-DD format (e.g., 2025-06-30).", icon="warning").show()
                return
        
        description = description if description else None
        due_date = due_date if due_date else None

        category_id = self.db_manager.get_category_id_by_name(category_name)

        if category_id is None: 
            # Fallback if selected category wasn't found (shouldn't happen if list is populated correctly)
            # or if "No Categories" was selected and no categories exist.
            default_category_id = self.db_manager.get_category_id_by_name("On-going")
            if default_category_id is not None:
                category_id = default_category_id
            else:
                ctk.CTkMessageBox(title="Error", message="No valid categories available. Please add a category first.", icon="warning").show()
                return

        if self.db_manager.add_task(self.current_user_id, title, description, priority, due_date, category_id):
            ctk.CTkMessageBox(title="Success", message="Task added successfully!", icon="info").show()
            
            # Clear input fields and reset dropdowns
            self.task_title_entry.delete(0, ctk.END)
            self.task_description_entry.delete(0, ctk.END)
            self.task_priority_optionmenu.set("Not urgent")
            self.task_due_date_entry.delete(0, ctk.END)
            if "On-going" in self.category_names: # Reset to 'On-going' if available
                self.task_category_optionmenu.set("On-going")
            elif self.category_names:
                self.task_category_optionmenu.set(self.category_names[0])
            
            self.show_tasks_page('All Tasks') # Refresh the task list
        else:
            ctk.CTkMessageBox(title="Error", message="Failed to add task. Check console for database errors.", icon="cancel").show()

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar.configure(width=self.sidebar_collapsed_width)
            for b in self.sidebar_buttons:
                b.configure(text="")
            self.sidebar_expanded = False
            self.collapse_btn.configure(text="▶")
        else:
            self.sidebar.configure(width=self.sidebar_width)
            for b, text in zip(self.sidebar_buttons, ["Tasks", "Calendar", "Habit", "Add Task", "Search Task", "Profile", "Sign Out"]):
                b.configure(text=text)
            self.sidebar_expanded = True
            self.collapse_btn.configure(text="◀")
        
        self.after(10, self.position_collapse_button)

if __name__ == "__main__":
    app = TimePlanApp()
    app.mainloop()