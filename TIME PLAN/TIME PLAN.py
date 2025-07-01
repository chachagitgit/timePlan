import customtkinter as ctk 
from tkinter import messagebox
from PIL import Image
import requests
import io

# Appearance setup
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# App setup
app = ctk.CTk()
app.geometry("800x500")
app.title("Time Plan")

# ========== TEMPORARY USER DATABASE ==========
user_database = {
    "admin": "1234"
}

# ========== BACKGROUND IMAGE FROM URL (ROTATED TO LANDSCAPE) ==========
url = "https://i.pinimg.com/736x/d9/66/94/d96694754ba31c43937d19805ef6c17a.jpg"
response = requests.get(url)
image_data = io.BytesIO(response.content)

# Open and rotate the image 90 degrees clockwise
bg_image = Image.open(image_data).rotate(-90, expand=True)
bg_image = bg_image.resize((800, 500))  # Resize after rotation

# Set it as background
bg_ctk_image = ctk.CTkImage(light_image=bg_image, dark_image=bg_image, size=(800, 500))
bg_label = ctk.CTkLabel(app, image=bg_ctk_image, text="")
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

# ========== FUNCTIONS ==========
def login_user():
    username = login_username.get()
    password = login_password.get()
    if username in user_database and user_database[username] == password:
        login_frame.place_forget()
        show_dashboard()
    else:
        messagebox.showerror("Login", "Invalid username or password")

def register_user():
    name = entry_name.get()
    email = entry_email.get()
    username = entry_new_username.get()
    password = entry_new_password.get()
    if name and email and username and password:
        if username in user_database:
            messagebox.showwarning("Sign Up", "Username already exists.")
        else:
            user_database[username] = password
            messagebox.showinfo("Sign Up", "Account created successfully!")
            signup_frame.place_forget()
            show_login()
    else:
        messagebox.showerror("Sign Up", "Please fill in all fields.")

def show_login():
    signup_frame.place_forget()
    dashboard_frame.place_forget()
    login_frame.place(relx=0.5, rely=0.5, anchor="center")

def show_signup():
    login_frame.place_forget()
    signup_frame.place(relx=0.5, rely=0.5, anchor="center")

def show_dashboard():
    dashboard_frame.place(relx=0.5, rely=0.5, anchor="center")

# ========== LOGIN FRAME ==========
login_frame = ctk.CTkFrame(app, width=400, height=350, corner_radius=0, fg_color="#d194e5")
login_frame.place(relx=0.5, rely=0.5, anchor="center")

ctk.CTkLabel(login_frame, text="Time Plan", font=("Arial", 18, "bold"), text_color="#5B23A0").place(x=20, y=15)
ctk.CTkLabel(login_frame, text="LOGIN", font=("Poppins", 22, "bold"), text_color="#505050").place(relx=0.5, y=60, anchor="center")
ctk.CTkLabel(login_frame, text="Welcome back! Login to access the Time Plan.",
             font=("Arial", 12), text_color="white").place(relx=0.5, y=100, anchor="center")

login_username = ctk.CTkEntry(login_frame, placeholder_text="Username", width=300, height=35, corner_radius=0)
login_username.place(relx=0.5, y=150, anchor="center")

login_password = ctk.CTkEntry(login_frame, placeholder_text="Password", show="*", width=300, height=35, corner_radius=0)
login_password.place(relx=0.5, y=190, anchor="center")

ctk.CTkButton(login_frame, text="LOGIN", width=300, height=40, corner_radius=30, fg_color="#d9a7eb",
              hover_color="#c181d8", command=login_user, text_color="black").place(relx=0.5, y=250, anchor="center")

ctk.CTkButton(login_frame, text="Don't have an account? Sign up", fg_color="transparent", text_color="blue",
              hover=False, command=show_signup).place(relx=0.5, y=300, anchor="center")

# ========== SIGNUP FRAME ==========
signup_frame = ctk.CTkFrame(app, width=400, height=400, corner_radius=20, fg_color="#e7c6f5")

ctk.CTkLabel(signup_frame, text="🅣 Time Plan", font=("Arial", 18, "bold"), text_color="#2b2b2b").place(x=20, y=15)
ctk.CTkLabel(signup_frame, text="SIGN UP", font=("Arial", 22, "bold"), text_color="#2b2b2b").place(relx=0.5, y=60, anchor="center")

entry_name = ctk.CTkEntry(signup_frame, placeholder_text="Name", width=300, height=35, corner_radius=0)
entry_name.place(relx=0.5, y=120, anchor="center")

entry_email = ctk.CTkEntry(signup_frame, placeholder_text="Email", width=300, height=35, corner_radius=0)
entry_email.place(relx=0.5, y=160, anchor="center")

entry_new_username = ctk.CTkEntry(signup_frame, placeholder_text="Username", width=300, height=35, corner_radius=0)
entry_new_username.place(relx=0.5, y=200, anchor="center")

entry_new_password = ctk.CTkEntry(signup_frame, placeholder_text="Password", show="*", width=300, height=35, corner_radius=0)
entry_new_password.place(relx=0.5, y=240, anchor="center")

ctk.CTkButton(signup_frame, text="LOGIN", width=300, height=40, corner_radius=30, fg_color="#d9a7eb",
              hover_color="#c181d8", command=register_user, text_color="black").place(relx=0.5, y=300, anchor="center")

ctk.CTkButton(signup_frame, text="Already have an account? Login", fg_color="transparent", text_color="blue",
              hover=False, command=show_login).place(relx=0.5, y=350, anchor="center")

# ========== DASHBOARD FRAME ==========
dashboard_frame = ctk.CTkFrame(app, width=700, height=400, corner_radius=20, fg_color="#e7c6f5")

# Sidebar
sidebar = ctk.CTkFrame(dashboard_frame, width=200, fg_color="#d1a8e9", corner_radius=10)
sidebar.place(x=0, y=0, relheight=1)

ctk.CTkLabel(sidebar, text=" Time Plan", font=("Arial", 18, "bold")).place(x=20, y=20)
ctk.CTkButton(sidebar, text="DASHBOARD", width=150, fg_color="#c08de8", hover_color="#a25ed1").place(x=25, y=80)
ctk.CTkButton(sidebar, text="MY TASK", width=150, fg_color="transparent", text_color="#000", hover=False).place(x=25, y=130)
ctk.CTkButton(sidebar, text="MY PROFILE", width=150, fg_color="transparent", text_color="#000", hover=False).place(x=25, y=180)
ctk.CTkButton(sidebar, text="SETTINGS", width=150, fg_color="transparent", text_color="#000", hover=False).place(x=25, y=230)

# Main dashboard area
main_box = ctk.CTkFrame(dashboard_frame, width=460, height=340, fg_color="white", border_color="#8364b0", border_width=2, corner_radius=15)
main_box.place(x=220, y=30)

ctk.CTkLabel(main_box, text="Nothing planned for today", text_color="#5d3e98", font=("Arial", 16)).place(relx=0.5, rely=0.5, anchor="center")

# Start app
app.mainloop()
