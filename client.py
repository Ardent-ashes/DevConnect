# gui_client_enhanced.py - FIXED VERSION
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog, simpledialog
import socket
import threading
import json
import os
import base64
from datetime import datetime
import uuid
from codeeditor import CodeEditorWindow
import requests
from tcp_logger import run_tcpdump_log

# Modern Style Constants
class ModernStyle:
    BG_COLOR = "#ffffff"
    SIDEBAR_BG = "#ffffff"
    CHAT_BG = "#ffffff"
    ENTRY_BG = "#ffffff"
    BUTTON_BG = "#e5dc5b"
    ACCENT_COLOR = "#007acc"
    SUCCESS_COLOR = "#28a745"
    WARNING_COLOR = "#ffc107"
    DANGER_COLOR = "#dc3545"
    TEXT_COLOR = "#000000"
    SECONDARY_TEXT = "#800d0d"
    MY_MESSAGE_BG = "#FFFFFF"
    MESSAGE_BG = "#ffffff"

class LoginWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chat Client - Login")
        self.root.geometry("400x300")
        self.root.configure(bg=ModernStyle.BG_COLOR)
        self.root.resizable(False, False)
        
        self.center_window()
        
        self.username = None
        self.host = "localhost"
        self.port = 5555
        
        self.create_widgets()
        
    def center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.root.winfo_screenheight() // 2) - (300 // 2)
        self.root.geometry(f"400x300+{x}+{y}")
    
    def create_widgets(self):
        # Title
        title_label = tk.Label(self.root, text="Chat Client", 
                              font=("Arial", 24, "bold"),
                              fg=ModernStyle.TEXT_COLOR,
                              bg=ModernStyle.BG_COLOR)
        title_label.pack(pady=30)
        
        # Login frame
        login_frame = tk.Frame(self.root, bg=ModernStyle.BG_COLOR)
        login_frame.pack(pady=20)
        
        # Username
        tk.Label(login_frame, text="Username:", 
                font=("Arial", 12),
                fg=ModernStyle.TEXT_COLOR,
                bg=ModernStyle.BG_COLOR).grid(row=0, column=0, sticky="w", pady=5)
        
        self.username_entry = tk.Entry(login_frame, 
                                     font=("Arial", 12),
                                     bg=ModernStyle.ENTRY_BG,
                                     fg=ModernStyle.TEXT_COLOR,
                                     insertbackground=ModernStyle.TEXT_COLOR,
                                     relief="flat",
                                     bd=5,
                                     width=20)
        self.username_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # Host
        tk.Label(login_frame, text="Host:", 
                font=("Arial", 12),
                fg=ModernStyle.TEXT_COLOR,
                bg=ModernStyle.BG_COLOR).grid(row=1, column=0, sticky="w", pady=5)
        
        self.host_entry = tk.Entry(login_frame, 
                                 font=("Arial", 12),
                                 bg=ModernStyle.ENTRY_BG,
                                 fg=ModernStyle.TEXT_COLOR,
                                 insertbackground=ModernStyle.TEXT_COLOR,
                                 relief="flat",
                                 bd=5,
                                 width=20)
        self.host_entry.insert(0, self.host)
        self.host_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # Port
        tk.Label(login_frame, text="Port:", 
                font=("Arial", 12),
                fg=ModernStyle.TEXT_COLOR,
                bg=ModernStyle.BG_COLOR).grid(row=2, column=0, sticky="w", pady=5)
        
        self.port_entry = tk.Entry(login_frame, 
                                 font=("Arial", 12),
                                 bg=ModernStyle.ENTRY_BG,
                                 fg=ModernStyle.TEXT_COLOR,
                                 insertbackground=ModernStyle.TEXT_COLOR,
                                 relief="flat",
                                 bd=5,
                                 width=20)
        self.port_entry.insert(0, str(self.port))
        self.port_entry.grid(row=2, column=1, padx=10, pady=5)
        
        # Connect button
        connect_btn = tk.Button(self.root, text="Connect",
                              font=("Arial", 12, "bold"),
                              bg=ModernStyle.BUTTON_BG,
                              fg=ModernStyle.TEXT_COLOR,
                              relief="flat",
                              bd=0,
                              padx=30,
                              pady=10,
                              cursor="hand2",
                              command=self.connect)
        connect_btn.pack(pady=20)
        
        self.root.bind('<Return>', lambda e: self.connect())
        self.username_entry.focus()
    
    def connect(self):
        username = self.username_entry.get().strip()
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return
        
        if not host:
            messagebox.showerror("Error", "Please enter a host")
            return
        
        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number")
            return
        
        self.username = username
        self.host = host
        self.port = port
        self.root.destroy()
    
    def show(self):
        self.root.mainloop()
        return self.username, self.host, self.port

def log_client(message, level="INFO", username=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_info = f"[{username}]" if username else "[CLIENT]"
    print(f"[CLIENT {level}] {timestamp} {user_info} {message}")

def log_client_networking(message, username=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    user_info = f"[{username}]" if username else "[CLIENT]"
    print(f"[CLIENT NET] {timestamp} {user_info} {message}")

def log_client_gui(message, username=None):
    timestamp = datetime.now().strftime("%H:%M:%S") 
    user_info = f"[{username}]" if username else "[CLIENT]"
    print(f"[CLIENT GUI] {timestamp} {user_info} {message}")

def log_client_file(message, username=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    user_info = f"[{username}]" if username else "[CLIENT]"
    print(f"[CLIENT FILE] {timestamp} {user_info} {message}")

threading.Thread(target=run_tcpdump_log, daemon=True).start()

class ChatClient:
    def __init__(self, username, host, port):
        self.username = username
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.supported_languages = []
        self.code_editor = None
        
        # Initialize GUI
        self.root = tk.Tk()
        self.root.title(f"Chat Client - {username}")
        self.root.geometry("1200x800")
        self.root.configure(bg=ModernStyle.BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Data storage
        self.active_chats = {"General": []}
        self.current_chat = "General"
        self.users_list = []
        self.groups_list = []
        self.pending_history_requests = set()  # Track pending history requests
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main container
        main_frame = tk.Frame(self.root, bg=ModernStyle.BG_COLOR)
        main_frame.pack(fill="both", expand=True)
        
        # Left sidebar
        self.create_sidebar(main_frame)
        
        # Chat area
        self.create_chat_area(main_frame)
        
        # Right sidebar (users list)
        self.create_users_sidebar(main_frame)
        
    def create_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=ModernStyle.SIDEBAR_BG, width=250)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # User info
        user_frame = tk.Frame(sidebar, bg=ModernStyle.SIDEBAR_BG)
        user_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(user_frame, text=f"Welcome, {self.username}!",
                font=("Arial", 12, "bold"),
                fg=ModernStyle.TEXT_COLOR,
                bg=ModernStyle.SIDEBAR_BG).pack()
        
        # Buttons frame
        btn_frame = tk.Frame(sidebar, bg=ModernStyle.SIDEBAR_BG)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        # Create buttons
        self.create_sidebar_button(btn_frame, "💬 Private Chat", self.start_private_chat)
        self.create_sidebar_button(btn_frame, "👥 Create Group", self.create_group)
        self.create_sidebar_button(btn_frame, "📝 Code Editor", self.open_code_editor, ModernStyle.SUCCESS_COLOR)
        self.create_sidebar_button(btn_frame, "🔄 Refresh", self.refresh_users)
        
        # Chat tabs
        tk.Label(sidebar, text="Active Chats",
                font=("Arial", 11, "bold"),
                fg=ModernStyle.TEXT_COLOR,
                bg=ModernStyle.SIDEBAR_BG).pack(pady=(20, 5))
        
        # Chat list frame
        chat_list_frame = tk.Frame(sidebar, bg=ModernStyle.SIDEBAR_BG)
        chat_list_frame.pack(fill="both", expand=True, padx=10)
        
        # Chat listbox with scrollbar
        listbox_frame = tk.Frame(chat_list_frame, bg=ModernStyle.SIDEBAR_BG)
        listbox_frame.pack(fill="both", expand=True)
        
        self.chat_listbox = tk.Listbox(listbox_frame,
                                     bg=ModernStyle.CHAT_BG,
                                     fg=ModernStyle.TEXT_COLOR,
                                     selectbackground=ModernStyle.ACCENT_COLOR,
                                     relief="flat",
                                     bd=0,
                                     font=("Arial", 10))
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
        
        self.chat_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.chat_listbox.yview)
        
        self.chat_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.chat_listbox.bind('<<ListboxSelect>>', self.on_chat_select)
        
        # Add default chat
        self.chat_listbox.insert(0, "General")
        self.chat_listbox.selection_set(0)
    
    def create_users_sidebar(self, parent):
        users_sidebar = tk.Frame(parent, bg=ModernStyle.SIDEBAR_BG, width=200)
        users_sidebar.pack(side="right", fill="y")
        users_sidebar.pack_propagate(False)
        
        # Users title
        tk.Label(users_sidebar, text="Online Users",
                font=("Arial", 11, "bold"),
                fg=ModernStyle.TEXT_COLOR,
                bg=ModernStyle.SIDEBAR_BG).pack(pady=(10, 5))
        
        # Users list frame
        users_list_frame = tk.Frame(users_sidebar, bg=ModernStyle.SIDEBAR_BG)
        users_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Users listbox with scrollbar
        users_listbox_frame = tk.Frame(users_list_frame, bg=ModernStyle.SIDEBAR_BG)
        users_listbox_frame.pack(fill="both", expand=True)
        
        self.users_listbox = tk.Listbox(users_listbox_frame,
                                       bg=ModernStyle.CHAT_BG,
                                       fg=ModernStyle.TEXT_COLOR,
                                       selectbackground=ModernStyle.ACCENT_COLOR,
                                       relief="flat",
                                       bd=0,
                                       font=("Arial", 10))
        users_scrollbar = tk.Scrollbar(users_listbox_frame, orient="vertical")
        
        self.users_listbox.config(yscrollcommand=users_scrollbar.set)
        users_scrollbar.config(command=self.users_listbox.yview)
        
        self.users_listbox.pack(side="left", fill="both", expand=True)
        users_scrollbar.pack(side="right", fill="y")
        
        # Double-click to start private chat
        self.users_listbox.bind('<Double-Button-1>', self.on_user_double_click)
        
        # User actions frame
        user_actions = tk.Frame(users_sidebar, bg=ModernStyle.SIDEBAR_BG)
        user_actions.pack(fill="x", padx=10, pady=5)
        
        tk.Button(user_actions, text="Start Private Chat",
                 font=("Arial", 9),
                 bg=ModernStyle.BUTTON_BG,
                 fg=ModernStyle.TEXT_COLOR,
                 relief="flat",
                 bd=0,
                 pady=5,
                 cursor="hand2",
                 command=self.start_private_chat_from_selection).pack(fill="x", pady=2)
    
    def create_sidebar_button(self, parent, text, command, color=None):
        btn = tk.Button(parent, text=text,
                       font=("Arial", 9),
                       bg=color or ModernStyle.BUTTON_BG,
                       fg=ModernStyle.TEXT_COLOR,
                       relief="flat",
                       bd=0,
                       pady=8,
                       cursor="hand2",
                       command=command)
        btn.pack(fill="x", pady=2)
        
        # Hover effects
        original_color = color or ModernStyle.BUTTON_BG
        def on_enter(e):
            btn.config(bg=self.darken_color(original_color))
        def on_leave(e):
            btn.config(bg=original_color)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def darken_color(self, color):
        """Darken a hex color for hover effect"""
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(max(0, c - 30) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"
        
    def create_chat_area(self, parent):
        chat_frame = tk.Frame(parent, bg=ModernStyle.BG_COLOR)
        chat_frame.pack(side="right", fill="both", expand=True)
        
        # Chat header
        header_frame = tk.Frame(chat_frame, bg=ModernStyle.CHAT_BG, height=50)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        self.chat_title = tk.Label(header_frame, text="General Chat",
                                  font=("Arial", 14, "bold"),
                                  fg=ModernStyle.TEXT_COLOR,
                                  bg=ModernStyle.CHAT_BG)
        self.chat_title.pack(pady=15)
        
        # Messages area
        messages_frame = tk.Frame(chat_frame, bg=ModernStyle.BG_COLOR)
        messages_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Messages text widget with scrollbar
        text_frame = tk.Frame(messages_frame, bg=ModernStyle.BG_COLOR)
        text_frame.pack(fill="both", expand=True)
        
        self.messages_text = tk.Text(text_frame,
                                   bg=ModernStyle.CHAT_BG,
                                   fg=ModernStyle.TEXT_COLOR,
                                   font=("Arial", 12),
                                   relief="flat",
                                   bd=0,
                                   state="disabled",
                                   wrap="word")
        
        msg_scrollbar = tk.Scrollbar(text_frame, orient="vertical")
        self.messages_text.config(yscrollcommand=msg_scrollbar.set)
        msg_scrollbar.config(command=self.messages_text.yview)
        
        self.messages_text.pack(side="left", fill="both", expand=True)
        msg_scrollbar.pack(side="right", fill="y")
        
        # Configure text tags for styling
        self.messages_text.tag_config("my_message", background=ModernStyle.MY_MESSAGE_BG, 
                                    foreground=ModernStyle.TEXT_COLOR, justify="right")
        self.messages_text.tag_config("other_message", background=ModernStyle.MESSAGE_BG,
                                    foreground=ModernStyle.TEXT_COLOR)
        self.messages_text.tag_config("system_message", foreground=ModernStyle.SECONDARY_TEXT,
                                    font=("Arial", 9, "italic"))
        self.messages_text.tag_config("file_message", foreground=ModernStyle.WARNING_COLOR,
                                    font=("Arial", 10, "bold"))
        
        # Input area
        input_frame = tk.Frame(chat_frame, bg=ModernStyle.BG_COLOR, height=80)
        input_frame.pack(fill="x", padx=10, pady=5)
        input_frame.pack_propagate(False)
        
        # Message entry
        entry_frame = tk.Frame(input_frame, bg=ModernStyle.BG_COLOR)
        entry_frame.pack(fill="x")
        
        self.message_entry = tk.Text(entry_frame,
                                   bg=ModernStyle.ENTRY_BG,
                                   fg=ModernStyle.TEXT_COLOR,
                                   font=("Arial", 10),
                                   relief="flat",
                                   bd=5,
                                   height=3,
                                   wrap="word",
                                   insertbackground=ModernStyle.TEXT_COLOR)
        self.message_entry.pack(side="left", fill="both", expand=True)
        
        # Buttons frame
        buttons_frame = tk.Frame(entry_frame, bg=ModernStyle.BG_COLOR)
        buttons_frame.pack(side="right", padx=(5, 0), fill="y")
        
        # File button
        file_btn = tk.Button(buttons_frame, text="File",
                           font=("Arial", 12),
                           bg=ModernStyle.WARNING_COLOR,
                           fg=ModernStyle.TEXT_COLOR,
                           relief="flat",
                           bd=0,
                           width=3,
                           cursor="hand2",
                           command=self.attach_file)
        file_btn.pack(pady=(0, 2))
        
        # Send button
        send_btn = tk.Button(buttons_frame, text="Send",
                           font=("Arial", 10, "bold"),
                           bg=ModernStyle.BUTTON_BG,
                           fg=ModernStyle.TEXT_COLOR,
                           relief="flat",
                           bd=0,
                           padx=15,
                           cursor="hand2",
                           command=self.send_message)
        send_btn.pack()
        
        # Bind Enter key (Shift+Enter for new line)
        self.message_entry.bind('<Return>', self.on_enter_key)
        self.message_entry.bind('<Shift-Return>', lambda e: None)
    
    def on_enter_key(self, event):
        if not event.state & 0x1:  # Not Shift+Enter
            self.send_message()
            return "break"
    
    def on_user_double_click(self, event):
        """Handle double-click on user in users list"""
        selection = self.users_listbox.curselection()
        if selection:
            user = self.users_listbox.get(selection[0])
            if user != self.username:
                self.start_private_chat_with_user(user)
    
    def start_private_chat_from_selection(self):
        """Start private chat with selected user"""
        selection = self.users_listbox.curselection()
        if selection:
            user = self.users_listbox.get(selection[0])
            if user != self.username:
                self.start_private_chat_with_user(user)
        else:
            messagebox.showwarning("Warning", "Please select a user first")
    
    def start_private_chat_with_user(self, user):
        """Start private chat with specific user"""
        chat_name = f"PM: {user}"
        self.ensure_chat_exists(chat_name)
        self.switch_to_chat(chat_name)

    def ensure_chat_exists(self, chat_name):
        """Ensure chat exists in both data and UI"""
        if chat_name not in self.active_chats:
            log_client_gui(f"Creating new chat: {chat_name}", self.username)
            self.active_chats[chat_name] = []
            
            # Add to UI in main thread
            self.root.after(0, lambda: self.add_chat_to_ui(chat_name))
    
    def add_chat_to_ui(self, chat_name):
        """Add chat to UI listbox if not already present"""
        # Check if chat already exists in listbox
        current_items = [self.chat_listbox.get(i) for i in range(self.chat_listbox.size())]
        if chat_name not in current_items:
            self.chat_listbox.insert(tk.END, chat_name)
            log_client_gui(f"Added chat to UI: {chat_name}", self.username)

    def upload_file(self, file_path, recipient=None, group_name=None):
        server_url = "localhost:8080"  # Adjust as needed
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'sender': self.username,
                    'recipient': recipient or '',
                    'group_name': group_name or ''
                }
                response = requests.post(f"{server_url}/upload", files=files, data=data)
                if response.status_code == 200:
                    result = response.json()
                    self.add_message("System", f"📎 Sent file '{os.path.basename(file_path)}' [Click to download]", "file_message", self.current_chat)
                    return result
                else:
                    messagebox.showerror("Upload Failed", response.text)
                    return None
        except Exception as e:
            messagebox.showerror("Upload Error", str(e))
            return None

    def download_file(self, file_id):
        server_url = "localhost:8080"
        try:
            response = requests.get(f"{server_url}/download/{file_id}")
            if response.status_code == 200:
                content_disposition = response.headers.get('Content-Disposition', '')
                filename = content_disposition.split('filename=')[1].strip('"') if 'filename=' in content_disposition else file_id
                save_path = filedialog.asksaveasfilename(defaultextension="", initialfile=filename)
                if save_path:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    messagebox.showinfo("Download Complete", f"File saved to {save_path}")
            else:
                messagebox.showerror("Download Failed", f"Status code: {response.status_code}")
        except Exception as e:
            messagebox.showerror("Download Error", str(e))

    def attach_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
    
        # Determine recipient or group
        if self.current_chat.startswith("PM: "):
            recipient = self.current_chat[4:]
            self.upload_file(file_path, recipient=recipient)
        elif self.current_chat.startswith("Group: "):
            group_name = self.current_chat[7:]
            self.upload_file(file_path, group_name=group_name)
        else:
            # Uploading to general chat
            self.upload_file(file_path)

    def open_code_editor(self):
        """Open the collaborative code editor"""
        if self.code_editor:
            self.code_editor.window.lift()
            return
        
        language = simpledialog.askstring("Code Editor", 
                                        f"Select language ({', '.join(self.supported_languages or ['python', 'javascript', 'java'])}):",
                                        initialvalue="python")
        
        if language:
            self.code_editor = CodeEditorWindow(self, self, language=language)
            self.send_to_server(f"CREATE_CODE_SESSION|{language}")
    
    def start_private_chat(self):
        """Start a private chat with a user"""
        if not self.users_list:
            messagebox.showwarning("Warning", "No other users online")
            return
        
        # Create a selection dialog
        users_except_self = [u for u in self.users_list if u != self.username]
        if not users_except_self:
            messagebox.showwarning("Warning", "No other users online")
            return
        
        user = simpledialog.askstring("Private Chat", 
                                    f"Enter username to chat with:\nAvailable users: {', '.join(users_except_self)}")
        if user and user != self.username and user in self.users_list:
            self.start_private_chat_with_user(user)
        elif user:
            messagebox.showerror("Error", f"User '{user}' not found or not online")
    
    def create_group(self):
        """Create a new group"""
        group_name = simpledialog.askstring("Create Group", "Enter group name:")
        if not group_name:
            return
        
        if not self.users_list:
            messagebox.showwarning("Warning", "No other users online to add to group")
            return
        
        users_except_self = [u for u in self.users_list if u != self.username]
        if not users_except_self:
            messagebox.showwarning("Warning", "No other users online to add to group")
            return
        
        members = simpledialog.askstring("Create Group", 
                                       f"Enter member usernames (comma-separated):\nAvailable users: {', '.join(users_except_self)}")
        if members:
            self.send_to_server(f"CREATE_GROUP|{group_name}|{members}")
    
    def refresh_users(self):
        self.send_to_server("LIST_CLIENTS|")
    
    def on_chat_select(self, event):
        selection = self.chat_listbox.curselection()
        if selection:
            chat_name = self.chat_listbox.get(selection[0])
            self.switch_to_chat(chat_name)
    
    def switch_to_chat(self, chat_name):
        """Switch to a different chat with improved history loading"""
        log_client_gui(f"Switching to chat: {chat_name}", self.username)
        self.current_chat = chat_name
        self.chat_title.config(text=f"{chat_name} Chat")
        
        # Ensure chat exists
        self.ensure_chat_exists(chat_name)
        
        # Clear messages area
        self.messages_text.config(state="normal")
        self.messages_text.delete(1.0, tk.END)
        
        # Load existing messages for this chat
        if chat_name in self.active_chats:
            for message in self.active_chats[chat_name]:
                self.display_message(message)
        
        # Request message history if not already loaded and not already pending
        history_key = f"{chat_name}_{self.username}"
        if (len(self.active_chats.get(chat_name, [])) == 0 and 
            history_key not in self.pending_history_requests):
            
            self.pending_history_requests.add(history_key)
            log_client_gui(f"Requesting history for {chat_name}", self.username)
            
            if chat_name.startswith("PM: "):
                user = chat_name[4:]
                self.send_to_server(f"GET_MESSAGES|PERSONAL|{user}")
            elif chat_name.startswith("Group: "):
                group = chat_name[7:]
                self.send_to_server(f"GET_MESSAGES|GROUP|{group}")
            elif chat_name == "General":
                self.send_to_server(f"GET_MESSAGES|BROADCAST|")
        
        self.messages_text.config(state="disabled")
        self.messages_text.see(tk.END)
        
        # Select the chat in the listbox
        self.root.after(0, lambda: self.select_chat_in_listbox(chat_name))
    
    def select_chat_in_listbox(self, chat_name):
        """Select the chat in the listbox"""
        try:
            for i in range(self.chat_listbox.size()):
                if self.chat_listbox.get(i) == chat_name:
                    self.chat_listbox.selection_clear(0, tk.END)
                    self.chat_listbox.selection_set(i)
                    self.chat_listbox.see(i)
                    break
        except Exception as e:
            log_client_gui(f"Error selecting chat in listbox: {e}", self.username)
    
    def send_message(self):
        message = self.message_entry.get(1.0, tk.END).strip()
        if not message:
            return
        
        self.message_entry.delete(1.0, tk.END)
        
        if self.current_chat == "General":
            self.send_to_server(f"BROADCAST|{message}")
        elif self.current_chat.startswith("PM: "):
            recipient = self.current_chat[4:]
            self.send_to_server(f"PERSONAL|{recipient}|{message}")
        elif self.current_chat.startswith("Group: "):
            group_name = self.current_chat[7:]
            self.send_to_server(f"GROUP|{group_name}|{message}")
    
    def send_to_server(self, message):
        try:
            self.client_socket.send(message.encode('utf-8'))
        except:
            messagebox.showerror("Error", "Connection lost")
            self.on_closing()
    
    def connect(self):
        try:
            self.client_socket.connect((self.host, self.port))
            self.client_socket.send(self.username.encode('utf-8'))
            
            response = self.client_socket.recv(1024).decode('utf-8')
            if response == "NAME_TAKEN":
                messagebox.showerror("Error", "Username already taken")
                return False
            elif response == "CONNECTED":
                self.connected = True
                self.add_message("System", f"Connected as {self.username}", "system_message")
                
                # Start receiving messages
                receive_thread = threading.Thread(target=self.receive_messages)
                receive_thread.daemon = True
                receive_thread.start()
                
                return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")
            return False
    
    def receive_messages(self):
        try:
            while self.connected:
                message = self.client_socket.recv(8192).decode('utf-8')
                if not message:
                    break
                
                self.process_received_message(message)
                
        except Exception as e:
            if self.connected:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Connection error: {str(e)}"))
                self.connected = False
    
    def process_received_message(self, message):
        try:
            if message.startswith("SERVER_INFO|"):
                data = json.loads(message[12:])
                self.supported_languages = data.get('supported_languages', [])
                self.users_list = data.get('active_users', [])
                self.update_users_list()
                log_client_networking(f"Received server info, {len(self.users_list)} users online", self.username)
                
            elif message.startswith("USER_LIST|"):
                data = json.loads(message[10:])
                if data.get('type') == 'USER_LIST_UPDATE':
                    self.users_list = data.get('users', [])
                    self.update_users_list()
                    log_client_networking(f"Updated user list: {len(self.users_list)} users", self.username)
                    
            elif message.startswith("USER_GROUPS|"):
                data = json.loads(message[12:])
                if data.get('type') == 'USER_GROUPS':
                    groups = data.get('groups', [])
                    log_client_networking(f"Received user groups: {groups}", self.username)
                    self.root.after(0, lambda: self.handle_user_groups(groups))
                            
            elif message.startswith("GROUP_CREATED|"):
                data = json.loads(message[14:])
                if data.get('type') == 'GROUP_CREATED':
                    group_name = data.get('group_name')
                    chat_name = f"Group: {group_name}"
                    log_client_networking(f"Group created: {group_name}", self.username)
                    self.root.after(0, lambda: self.handle_group_created(chat_name))

            elif message.startswith("FILE_NOTIFICATION|"):
                file_info = json.loads(message.split("|", 1)[1])
                self.handle_file_message(file_info)
                        
            elif message.startswith("MESSAGE_HISTORY|"):
                data = json.loads(message[16:])
                self.handle_message_history(data)
                
            elif message.startswith("CODE_SESSION|"):
                self.handle_code_session_message(json.loads(message[13:]))
                
            elif message.startswith("PM from "):
                # Private message received
                parts = message.split(": ", 1)
                sender = parts[0][8:]  # Remove "PM from "
                content = parts[1] if len(parts) > 1 else ""
                
                chat_name = f"PM: {sender}"
                self.ensure_chat_exists(chat_name)
                self.add_message(sender, content, "other_message", chat_name)
                
            elif message.startswith("PM to "):
                # Private message sent confirmation
                parts = message.split(": ", 1)
                recipient = parts[0][6:]  # Remove "PM to "
                content = parts[1] if len(parts) > 1 else ""
                
                chat_name = f"PM: {recipient}"
                self.ensure_chat_exists(chat_name)
                self.add_message("You", content, "my_message", chat_name)
                
            elif message.startswith("[") and "] " in message:
                # Group message
                end_bracket = message.index("] ")
                group_name = message[1:end_bracket]
                rest = message[end_bracket + 2:]
                
                if ": " in rest:
                    sender, content = rest.split(": ", 1)
                    chat_name = f"Group: {group_name}"
                    
                    self.ensure_chat_exists(chat_name)
                    self.add_message(sender, content, "other_message", chat_name)
                
            else:
                # General message or system message
                if ": " in message and not message.startswith("SERVER:"):
                    sender, content = message.split(": ", 1)
                    if sender == self.username:
                        self.add_message("You", content, "my_message")
                    else:
                        self.add_message(sender, content, "other_message")
                else:
                    self.add_message("System", message, "system_message")
                    
        except Exception as e:
            log_client_networking(f"Error processing message: {e}", self.username)
    
    def handle_user_groups(self, groups):
        """Handle user groups received from server"""
        for group in groups:
            chat_name = f"Group: {group}"
            self.ensure_chat_exists(chat_name)
        log_client_gui(f"Added {len(groups)} user groups to UI", self.username)
    
    def handle_group_created(self, chat_name):
        """Handle group creation notification"""
        self.ensure_chat_exists(chat_name)
        self.switch_to_chat(chat_name)
        log_client_gui(f"Switched to newly created group: {chat_name}", self.username)
    
    def handle_message_history(self, data):
        """Handle message history received from server with improved processing"""
        msg_type = data.get('msg_type')
        target = data.get('target')
        messages = data.get('messages', [])
        
        chat_name = "General"
        if msg_type == "PERSONAL":
            chat_name = f"PM: {target}"
        elif msg_type == "GROUP":
            chat_name = f"Group: {target}"
        
        # Remove from pending requests
        history_key = f"{chat_name}_{self.username}"
        self.pending_history_requests.discard(history_key)
        
        log_client_gui(f"Processing {len(messages)} history messages for {chat_name}", self.username)
        
        self.ensure_chat_exists(chat_name)
        
        # Clear existing messages for this chat
        self.active_chats[chat_name] = []
        
        # Add historical messages
        for msg in messages:
            sender = msg['sender']
            content = msg['content']
            timestamp = msg['timestamp']
            file_data = msg.get('file_data')
            
            tag = "my_message" if sender == self.username else "other_message"
            if sender == "System":
                tag = "system_message"
            
            # Check if this is a file message
            if file_data:
                try:
                    file_info = json.loads(file_data)
                    file_id = file_info.get('file_id')
                    filename = file_info.get('filename')
                    if file_id and filename:
                        # Store file for potential download
                        if not hasattr(self, 'pending_downloads'):
                            self.pending_downloads = {}
                        self.pending_downloads[file_id] = {'filename': filename, 'sender': sender}
                        tag = "file_message"
                except:
                    pass
            
            message_data = {
                'sender': sender,
                'content': content,
                'timestamp': timestamp,
                'tag': tag,
                'file_data': file_data
            }
            
            self.active_chats[chat_name].append(message_data)
        
        # Refresh display if this is the current chat
        if chat_name == self.current_chat:
            self.root.after(0, lambda: self.refresh_current_chat())
    
    def refresh_current_chat(self):
        """Refresh the current chat display"""
        self.messages_text.config(state="normal")
        self.messages_text.delete(1.0, tk.END)
        
        if self.current_chat in self.active_chats:
            for message in self.active_chats[self.current_chat]:
                self.display_message(message)
        
        self.messages_text.config(state="disabled")
        self.messages_text.see(tk.END)
    
    def update_users_list(self):
        """Update the users list display"""
        self.root.after(0, self._update_users_list_ui)
    
    def _update_users_list_ui(self):
        """Update users list UI in main thread"""
        self.users_listbox.delete(0, tk.END)
        for user in sorted(self.users_list):
            self.users_listbox.insert(tk.END, user)
    
    def handle_code_session_message(self, data):
        """Handle code editor related messages"""
        msg_type = data.get('type')
        
        if msg_type == 'session_created':
            if self.code_editor:
                self.code_editor.session_id = data['session_id']
                self.code_editor.session_label.config(text=f"Session: {data['session_id']}")
                self.code_editor.window.title(f"Code Editor - {data['language'].title()} - {data['session_id']}")
                
        elif msg_type == 'session_joined':
            if self.code_editor:
                self.code_editor.session_id = data['session_id']
                self.code_editor.update_code(data['code'])
                self.code_editor.update_participants(data['participants'])
                self.code_editor.session_label.config(text=f"Session: {data['session_id']}")
                
        elif msg_type == 'code_update':
            if self.code_editor and self.code_editor.session_id == data['session_id']:
                self.code_editor.update_code(data['code'], data.get('user'))
                
        elif msg_type == 'execution_result':
            if self.code_editor and self.code_editor.session_id == data['session_id']:
                self.code_editor.handle_execution_result(data['result'], data['executed_by'])
                
        elif msg_type == 'user_joined':
            if self.code_editor:
                self.code_editor.update_participants(data['participants'])
                self.code_editor.add_output(f"👤 {data['user']} joined the session\n", "info")
                
        elif msg_type == 'user_left':
            if self.code_editor and 'participants' in data:
                self.code_editor.update_participants(data['participants'])
                self.code_editor.add_output(f"👤 {data['user']} left the session\n", "info")
                
        elif msg_type == 'code_invitation':
            # Handle code session invitation
            result = messagebox.askyesno("Code Editor Invitation", 
                                       f"{data['from']} invited you to collaborate on a {data['language']} code session. Join?")
            if result:
                self.code_editor = CodeEditorWindow(self, self, data['session_id'], data['language'])
                self.send_to_server(f"JOIN_CODE_SESSION|{data['session_id']}")
                
        elif msg_type == 'error':
            messagebox.showerror("Code Editor Error", data['message'])
    
    def handle_file_message(self, file_info):
        sender = file_info['sender']
        recipient = file_info.get('recipient')
        group_name = file_info.get('group_name')
        filename = file_info['filename']
        file_id = file_info['file_id']
        timestamp = file_info.get('timestamp', datetime.now().strftime("%H:%M"))

        if group_name:
            chat_key = f"Group: {group_name}"
        else:
            chat_key = f"PM: {sender}" if sender != self.username else f"PM: {recipient}"

        file_data = json.dumps({
            'file_id': file_id,
            'filename': filename
        })

        message_data = {
            'sender': sender,
            'content': f"📎 {filename} [Click to download]",
            'timestamp': timestamp,
            'tag': "file_message",
            'file_data': file_data
        }

        self.ensure_chat_exists(chat_key)
        self.active_chats[chat_key].append(message_data)

        if self.current_chat == chat_key:
            self.root.after(0, lambda: self.display_message(message_data))

        if not hasattr(self, 'pending_downloads'):
            self.pending_downloads = {}
        self.pending_downloads[file_id] = {
            'filename': filename,
            'sender': sender
        }

    def on_message_click(self, event):
        """Handle clicks on messages to download files"""
        try:
            # Get the line that was clicked
            clicked_index = self.messages_text.index(f"@{event.x},{event.y}")
            line_start = self.messages_text.index(f"{clicked_index} linestart")
            
            # Check if this line has a file
            if hasattr(self, 'file_links') and line_start in self.file_links:
                file_id = self.file_links[line_start]
                self.download_file(file_id)
            else:
                # Check if line contains file marker and try to extract file_id
                line_end = self.messages_text.index(f"{clicked_index} lineend")
                line_text = self.messages_text.get(line_start, line_end)
                if "📎" in line_text and "[Click to download]" in line_text:
                    # Try to find file_id from pending downloads
                    for file_id, info in getattr(self, 'pending_downloads', {}).items():
                        if info['filename'] in line_text:
                            self.download_file(file_id)
                            break
        except Exception as e:
            print(f"Click handler error: {e}")  # Debug
    
    def add_message(self, sender, content, tag, chat_name="General"):
        timestamp = datetime.now().strftime("%H:%M")
        
        self.ensure_chat_exists(chat_name)
        
        message_data = {
            'sender': sender,
            'content': content,
            'timestamp': timestamp,
            'tag': tag
        }
        
        self.active_chats[chat_name].append(message_data)
        
        # Display message if it's the current chat
        if chat_name == self.current_chat:
            self.root.after(0, lambda: self.display_message(message_data))
    
    def display_message(self, message_data):
        self.messages_text.config(state="normal")
        
        sender = message_data['sender']
        content = message_data['content']
        timestamp = message_data['timestamp']
        tag = message_data['tag']
        file_data = message_data.get('file_data')
        
        if tag == "system_message":
            self.messages_text.insert(tk.END, f"[{timestamp}] {content}\n", tag)
        elif tag == "file_message":
            # Special handling for file messages
            if file_data:
                try:
                    file_info = json.loads(file_data)
                    file_id = file_info.get('file_id')
                    if file_id:
                        # Create clickable file link
                        line_start = self.messages_text.index(tk.END)
                        self.messages_text.insert(tk.END, f"[{timestamp}] {sender}: {content}\n", tag)
                        line_end = self.messages_text.index(tk.END)
                        
                        # Store file info for this line
                        if not hasattr(self, 'file_links'):
                            self.file_links = {}
                        self.file_links[line_start] = file_id
                        
                        # Make it look clickable
                        self.messages_text.tag_add("clickable_file", line_start, line_end)
                        self.messages_text.tag_config("clickable_file", underline=True, foreground="#4a9eff")
                    else:
                        self.messages_text.insert(tk.END, f"[{timestamp}] {sender}: {content}\n", tag)
                except:
                    self.messages_text.insert(tk.END, f"[{timestamp}] {sender}: {content}\n", tag)
            else:
                self.messages_text.insert(tk.END, f"[{timestamp}] {sender}: {content}\n", tag)
        else:
            self.messages_text.insert(tk.END, f"[{timestamp}] {sender}: {content}\n", tag)
        
        self.messages_text.config(state="disabled")
        self.messages_text.see(tk.END)
        
        # Bind click for file downloads
        if not hasattr(self, 'file_click_bound'):
            self.messages_text.bind("<Button-1>", self.on_message_click)
            self.file_click_bound = True
    
    def on_closing(self):
        self.connected = False
        if self.code_editor:
            try:
                self.code_editor.window.destroy()
            except:
                pass
            self.code_editor = None
        try:
            self.client_socket.close()
        except:
            pass
        self.root.destroy()
    
    def run(self):
        if self.connect():
            self.root.mainloop()

def main():
    # Show login window
    login_window = LoginWindow()
    username, host, port = login_window.show()
    
    if username:
        # Create and run chat client
        client = ChatClient(username, host, port)
        client.run()

if __name__ == "__main__":
    main()