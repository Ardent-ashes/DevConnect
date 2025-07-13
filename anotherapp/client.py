# gui_client_enhanced.py
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

# Modern Style Constants
class ModernStyle:
    BG_COLOR = "#1e1e1e"
    SIDEBAR_BG = "#ffffff"
    CHAT_BG = "#ffffff"
    ENTRY_BG = "#4a4a4a"
    BUTTON_BG = "#e5dc5b"
    ACCENT_COLOR = "#007acc"
    SUCCESS_COLOR = "#28a745"
    WARNING_COLOR = "#ffc107"
    DANGER_COLOR = "#dc3545"
    TEXT_COLOR = "#821414"
    SECONDARY_TEXT = "#800d0d"
    MY_MESSAGE_BG = "#408ec2"
    MESSAGE_BG = "#2d2d2d"

class LoginWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chat Client - Login")
        self.root.geometry("400x300")
        self.root.configure(bg=ModernStyle.BG_COLOR)
        self.root.resizable(False, False)
        
        self.center_window()
        
        self.username = None
        self.host = "127.0.0.1"
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
        self.create_sidebar_button(btn_frame, "📎 Share File", self.share_file)
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
                                   font=("Arial", 10),
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
                                    foreground="white", justify="right")
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
        file_btn = tk.Button(buttons_frame, text="📎",
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
        if chat_name not in self.active_chats:
            self.active_chats[chat_name] = []
            self.chat_listbox.insert(tk.END, chat_name)
            # Request message history
            self.send_to_server(f"GET_MESSAGES|PERSONAL|{user}")
        self.switch_to_chat(chat_name)
    
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
    
    def share_file(self):
        """Share a file"""
        file_path = filedialog.askopenfilename(title="Select file to share")
        if not file_path:
            return
        
        # Check file size (limit to 10MB)
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            messagebox.showerror("Error", "File size too large (max 10MB)")
            return
        
        # Ask for sharing target
        target_type = messagebox.askyesnocancel("Share File", 
                                               "Share with:\nYes = Current Chat\nNo = Select Recipient\nCancel = Everyone")
        
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            file_data = {
                'filename': os.path.basename(file_path),
                'content': base64.b64encode(file_content).decode('utf-8'),
                'size': file_size
            }
            
            if target_type is True:  # Current chat
                if self.current_chat.startswith("PM: "):
                    file_data['recipient'] = self.current_chat[4:]
                elif self.current_chat.startswith("Group: "):
                    file_data['group'] = self.current_chat[7:]
            elif target_type is False:  # Select recipient
                if self.users_list:
                    users_except_self = [u for u in self.users_list if u != self.username]
                    if users_except_self:
                        recipient = simpledialog.askstring("Share File", 
                                                          f"Enter recipient username:\nAvailable users: {', '.join(users_except_self)}")
                        if recipient and recipient in self.users_list:
                            file_data['recipient'] = recipient
                        elif recipient:
                            messagebox.showerror("Error", "Invalid recipient")
                            return
                        else:
                            return
                    else:
                        messagebox.showerror("Error", "No other users online")
                        return
                else:
                    messagebox.showerror("Error", "No users available")
                    return
            # target_type is None means share with everyone (no additional data needed)
            
            print(f"Sending file data: {file_data.get('filename')} to server")  # Debug
            self.send_to_server(f"FILE_SHARE|{json.dumps(file_data)}")
            self.add_message("System", f"File '{os.path.basename(file_path)}' upload initiated...", "system_message")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to share file: {str(e)}")
            print(f"File share error: {e}")  # Debug
    
    def attach_file(self):
        """Attach file to current chat"""
        self.share_file()
    
    def refresh_users(self):
        self.send_to_server("LIST_CLIENTS|")
    
    def on_chat_select(self, event):
        selection = self.chat_listbox.curselection()
        if selection:
            chat_name = self.chat_listbox.get(selection[0])
            self.switch_to_chat(chat_name)
    
    def switch_to_chat(self, chat_name):
        """Switch to a different chat"""
        self.current_chat = chat_name
        self.chat_title.config(text=f"{chat_name} Chat")
        
        # Clear messages area
        self.messages_text.config(state="normal")
        self.messages_text.delete(1.0, tk.END)
        
        # Load messages for this chat
        if chat_name in self.active_chats:
            for message in self.active_chats[chat_name]:
                self.display_message(message)
        
        # Request message history if not already loaded
        if chat_name != "General" and len(self.active_chats.get(chat_name, [])) == 0:
            if chat_name.startswith("PM: "):
                user = chat_name[4:]
                self.send_to_server(f"GET_MESSAGES|PERSONAL|{user}")
            elif chat_name.startswith("Group: "):
                group = chat_name[7:]
                self.send_to_server(f"GET_MESSAGES|GROUP|{group}")
        elif chat_name == "General" and len(self.active_chats.get(chat_name, [])) == 0:
            self.send_to_server(f"GET_MESSAGES|BROADCAST|")
        
        self.messages_text.config(state="disabled")
        self.messages_text.see(tk.END)
    
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
                
                # Request general chat history
                self.send_to_server("GET_MESSAGES|BROADCAST|")
                
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
                message = self.client_socket.recv(8192).decode('utf-8')  # Increased buffer
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
                
            elif message.startswith("USER_LIST|"):
                data = json.loads(message[10:])
                if data.get('type') == 'USER_LIST_UPDATE':
                    self.users_list = data.get('users', [])
                    self.update_users_list()
                    
            elif message.startswith("USER_GROUPS|"):
                data = json.loads(message[12:])
                if data.get('type') == 'USER_GROUPS':
                    groups = data.get('groups', [])
                    for group in groups:
                        chat_name = f"Group: {group}"
                        if chat_name not in self.active_chats:
                            self.active_chats[chat_name] = []
                            self.root.after(0, lambda g=chat_name: self.chat_listbox.insert(tk.END, g))
                            
            elif message.startswith("GROUP_CREATED|"):
                data = json.loads(message[14:])
                if data.get('type') == 'GROUP_CREATED':
                    group_name = data.get('group_name')
                    chat_name = f"Group: {group_name}"
                    if chat_name not in self.active_chats:
                        self.active_chats[chat_name] = []
                        self.root.after(0, lambda: self.chat_listbox.insert(tk.END, chat_name))
                        self.root.after(0, lambda: self.switch_to_chat(chat_name))
                        
            elif message.startswith("MESSAGE_HISTORY|"):
                data = json.loads(message[16:])
                self.handle_message_history(data)
                
            elif message.startswith("FILE_SHARED|"):
                file_data = json.loads(message[12:])
                self.handle_file_shared(file_data)
                
            elif message.startswith("FILE_DOWNLOAD|"):
                file_data = json.loads(message[14:])
                self.handle_file_download(file_data)
                
            elif message.startswith("CODE_SESSION|"):
                self.handle_code_session_message(json.loads(message[13:]))
                
            elif message.startswith("PM from "):
                # Private message received
                parts = message.split(": ", 1)
                sender = parts[0][8:]  # Remove "PM from "
                content = parts[1] if len(parts) > 1 else ""
                
                chat_name = f"PM: {sender}"
                if chat_name not in self.active_chats:
                    self.active_chats[chat_name] = []
                    self.root.after(0, lambda: self.chat_listbox.insert(tk.END, chat_name))
                
                self.add_message(sender, content, "other_message", chat_name)
                
            elif message.startswith("PM to "):
                # Private message sent confirmation
                parts = message.split(": ", 1)
                recipient = parts[0][6:]  # Remove "PM to "
                content = parts[1] if len(parts) > 1 else ""
                
                chat_name = f"PM: {recipient}"
                self.add_message("You", content, "my_message", chat_name)
                
            elif message.startswith("[") and "] " in message:
                # Group message
                end_bracket = message.index("] ")
                group_name = message[1:end_bracket]
                rest = message[end_bracket + 2:]
                
                if ": " in rest:
                    sender, content = rest.split(": ", 1)
                    chat_name = f"Group: {group_name}"
                    
                    if chat_name not in self.active_chats:
                        self.active_chats[chat_name] = []
                        self.root.after(0, lambda: self.chat_listbox.insert(tk.END, chat_name))
                    
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
            print(f"Error processing message: {e}")
    
    def handle_message_history(self, data):
        """Handle message history received from server"""
        msg_type = data.get('msg_type')
        target = data.get('target')
        messages = data.get('messages', [])
        
        chat_name = "General"
        if msg_type == "PERSONAL":
            chat_name = f"PM: {target}"
        elif msg_type == "GROUP":
            chat_name = f"Group: {target}"
        
        if chat_name not in self.active_chats:
            self.active_chats[chat_name] = []
        
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
    
    def handle_file_shared(self, file_data):
        """Handle file sharing notification"""
        sender = file_data.get('sender')
        filename = file_data.get('filename')
        file_id = file_data.get('file_id')
        file_size = file_data.get('file_size', 0)
        group = file_data.get('group')
        
        print(f"Received file share notification: {filename} from {sender}")  # Debug
        
        # Determine which chat this belongs to
        if group:
            chat_name = f"Group: {group}"
        elif sender != self.username:
            # This is a private file share TO us
            chat_name = f"PM: {sender}"
        else:
            # This is a broadcast or our own file share confirmation
            chat_name = "General"
        
        # Ensure chat exists
        if chat_name not in self.active_chats:
            self.active_chats[chat_name] = []
            if chat_name.startswith("PM: ") or chat_name.startswith("Group: "):
                self.root.after(0, lambda: self.chat_listbox.insert(tk.END, chat_name))
        
        # Add file sharing message with download button
        message_text = f"📎 Shared file: {filename} ({file_size} bytes) [Click to download]"
        self.add_message(sender, message_text, "file_message", chat_name)
        
        # Store file ID for download
        if not hasattr(self, 'pending_downloads'):
            self.pending_downloads = {}
        self.pending_downloads[file_id] = {'filename': filename, 'sender': sender}
        
        # Make file message clickable
        def on_file_click(event):
            # Get clicked line
            line_start = self.messages_text.index("@%s,%s linestart" % (event.x, event.y))
            line_end = self.messages_text.index("@%s,%s lineend" % (event.x, event.y))
            line_text = self.messages_text.get(line_start, line_end)
            
            # Check if this line contains a file
            if "📎" in line_text and "[Click to download]" in line_text:
                self.download_file(file_id)
        
        # Bind click event
        self.messages_text.bind("<Button-1>", on_file_click, add=True)
    
    def download_file(self, file_id):
        """Download a shared file"""
        print(f"Attempting to download file: {file_id}")  # Debug
        self.send_to_server(f"GET_FILE|{file_id}")
    
    def handle_file_download(self, file_data):
        """Handle file download response"""
        try:
            file_id = file_data.get('file_id')
            filename = file_data.get('filename')
            content = file_data.get('content')
            
            if not content:
                messagebox.showerror("Error", "File not found")
                return
            
            # Decode base64 content
            file_bytes = base64.b64decode(content)
            
            # Ask user where to save
            save_path = filedialog.asksaveasfilename(
                title="Save file",
                initialvalue=filename,
                defaultextension=os.path.splitext(filename)[1] if '.' in filename else ''
            )
            
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(file_bytes)
                messagebox.showinfo("Success", f"File saved to {save_path}")
                print(f"File downloaded successfully: {save_path}")  # Debug
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download file: {str(e)}")
            print(f"Download error: {e}")  # Debug
    
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
    
    def add_message(self, sender, content, tag, chat_name="General"):
        timestamp = datetime.now().strftime("%H:%M")
        
        if chat_name not in self.active_chats:
            self.active_chats[chat_name] = []
        
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