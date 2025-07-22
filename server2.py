# enhanced_server_with_database.py - FIXED VERSION
import socket
import threading
import json
import time
import os
import subprocess
import tempfile
import uuid
import sqlite3
import base64
from datetime import datetime
from codeexecutor import CodeExecutor
from file_transfer import FileTransferServer, FileTransferDatabase

# Enhanced logging function
def log_server(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SERVER {level}] {timestamp} - {message}")

def log_networking(message, client_name=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    client_info = f"[{client_name}]" if client_name else "[SYSTEM]"
    print(f"[NETWORK] {timestamp} {client_info} {message}")

def log_database(message, operation="QUERY"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[DATABASE {operation}] {timestamp} - {message}")

def log_file_transfer(message, operation="TRANSFER"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[FILE {operation}] {timestamp} - {message}")

def log_code_session(message, session_id=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    session_info = f"[{session_id}]" if session_id else "[NO_SESSION]"
    print(f"[CODE] {timestamp} {session_info} {message}")

class ChatDatabase(FileTransferDatabase):
    def __init__(self, db_file="chat_history.db"):
        self.db_file = db_file
        log_database(f"Initializing database: {db_file}")
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        log_database("Creating database tables if not exist")
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                recipient TEXT,
                group_name TEXT,
                content TEXT NOT NULL,
                message_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_data TEXT
            )
        ''')
        log_database("Messages table ready")
        
        # Groups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT UNIQUE NOT NULL,
                creator TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        log_database("Groups table ready")
        
        # Group members table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                member TEXT NOT NULL,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_name) REFERENCES groups (group_name)
            )
        ''')
        log_database("Group members table ready")
        
        # Files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                file_data BLOB NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                sender TEXT NOT NULL,
                recipient TEXT,
                group_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        log_database("Files table ready")
        
        conn.commit()
        conn.close()

        # Initialize file transfer tables
        log_database("Initializing file transfer tables")
        self.init_file_tables() 
    
    def save_message(self, sender, content, message_type, recipient=None, group_name=None, file_data=None):
        """Save a message to the database"""
        target = recipient or group_name or "BROADCAST"
        log_database(f"Saving {message_type} message from {sender} to {target}: {content[:50]}...")
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (sender, recipient, group_name, content, message_type, file_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sender, recipient, group_name, content, message_type, file_data))
        
        conn.commit()
        conn.close()
        log_database(f"Message saved successfully (ID: {cursor.lastrowid})")
    
    def get_messages(self, message_type, user1=None, user2_or_group=None, limit=50):
        """Retrieve messages from the database"""
        if message_type == "BROADCAST":
            log_database(f"Retrieving {limit} broadcast messages")
        elif message_type == "PERSONAL":
            log_database(f"Retrieving {limit} personal messages between {user1} and {user2_or_group}")
        elif message_type == "GROUP":
            log_database(f"Retrieving {limit} group messages for {user2_or_group}")
            
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        if message_type == "BROADCAST":
            cursor.execute('''
                SELECT sender, content, timestamp, file_data
                FROM messages 
                WHERE message_type = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (message_type, limit))
        elif message_type == "PERSONAL":
            cursor.execute('''
                SELECT sender, content, timestamp, file_data
                FROM messages 
                WHERE message_type = ? AND 
                      ((sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?))
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (message_type, user1, user2_or_group, user2_or_group, user1, limit))
        elif message_type == "GROUP":
            cursor.execute('''
                SELECT sender, content, timestamp, file_data
                FROM messages 
                WHERE message_type = ? AND group_name = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (message_type, user2_or_group, limit))
        
        messages = cursor.fetchall()
        conn.close()
        log_database(f"Retrieved {len(messages)} messages from database")
        return list(reversed(messages))
    
    def create_group(self, group_name, creator):
        """Create a new group"""
        log_database(f"Creating group '{group_name}' by {creator}")
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO groups (group_name, creator) VALUES (?, ?)', 
                          (group_name, creator))
            conn.commit()
            log_database(f"Group '{group_name}' created successfully")
            return True
        except sqlite3.IntegrityError:
            log_database(f"Group '{group_name}' already exists", "ERROR")
            return False
        finally:
            conn.close()
    
    def add_group_member(self, group_name, member):
        """Add a member to a group"""
        log_database(f"Adding {member} to group '{group_name}'")
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO group_members (group_name, member) 
            VALUES (?, ?)
        ''', (group_name, member))
        
        conn.commit()
        conn.close()
        log_database(f"{member} added to group '{group_name}'")
    
    def get_group_members(self, group_name):
        """Get all members of a group"""
        log_database(f"Retrieving members for group '{group_name}'")
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT member FROM group_members WHERE group_name = ?
        ''', (group_name,))
        
        members = [row[0] for row in cursor.fetchall()]
        conn.close()
        log_database(f"Group '{group_name}' has {len(members)} members: {members}")
        return members
    
    def get_user_groups(self, username):
        """Get all groups a user is a member of"""
        log_database(f"Retrieving groups for user {username}")
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT group_name FROM group_members WHERE member = ?
        ''', (username,))
        
        groups = [row[0] for row in cursor.fetchall()]
        conn.close()
        log_database(f"User {username} is member of {len(groups)} groups: {groups}")
        return groups
    
    def remove_group_member(self, group_name, member):
        """Remove a member from a group"""
        log_database(f"Removing {member} from group '{group_name}'")
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM group_members WHERE group_name = ? AND member = ?
        ''', (group_name, member))
        
        conn.commit()
        conn.close()
        log_database(f"{member} removed from group '{group_name}'")

class ChatServer:
    def __init__(self, host='localhost', port=5555):
        self.host = host
        self.port = port
        self.http_port = 8080
        
        log_server(f"Initializing ChatServer on {host}:{port}")
        log_server(f"HTTP file server will run on port {self.http_port}")
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        
        self.clients = {}  # {client_name: (client_socket, client_address)}
        self.db = ChatDatabase()
        
        # Code editor sessions
        self.code_sessions = {}  # {session_id: {code, language, participants, owner}}
        log_server("Code sessions dictionary initialized")

        # Add file transfer server
        log_server("Initializing file transfer server")
        self.file_server = FileTransferServer(
            host=self.host,
            port=self.http_port,
            database=self.db,
            clients=self.clients
        )
        log_server("ChatServer initialization complete")
        
    def start(self):
        """Start both chat and HTTP servers"""
        self.server_socket.listen(5)
        log_server(f" Chat server LISTENING on {self.host}:{self.port}")
        log_server(f" Supported programming languages: {list(CodeExecutor.SUPPORTED_LANGUAGES.keys())}")
        
        # Start file transfer server
        file_server_url = self.file_server.start()
        log_server(f" File transfer server started at {file_server_url}")
        
        log_server(" Server is ready to accept connections!")
        log_server("=" * 60)
        
        try:
            while True:
                log_networking("Waiting for client connections...")
                client_socket, client_address = self.server_socket.accept()
                log_networking(f"New connection attempt from {client_address}")
                
                client_thread = threading.Thread(target=self.handle_client, 
                                               args=(client_socket, client_address))
                client_thread.daemon = True
                client_thread.start()
                log_networking(f"Started new thread for {client_address}")
        except KeyboardInterrupt:
            log_server(" Keyboard interrupt received, shutting down...")
        finally:
            log_server("Cleaning up server resources...")
            self.server_socket.close()
            self.file_server.stop()
            log_server(" Server shutdown complete")

    def handle_client(self, client_socket, client_address):
        client_name = None
        try:
            log_networking(f"Handling new client from {client_address}")
            
            # Get client name
            client_name = client_socket.recv(1024).decode('utf-8')
            log_networking(f"Client wants username: '{client_name}'", client_name)
            
            # Check if name already exists
            if client_name in self.clients:
                log_networking(f"Username '{client_name}' already taken!", client_name)
                client_socket.send("NAME_TAKEN".encode('utf-8'))
                client_socket.close()
                return
            
            # Add client to clients dictionary
            self.clients[client_name] = (client_socket, client_address)
            client_socket.send("CONNECTED".encode('utf-8'))
            log_networking(f" Client '{client_name}' successfully connected", client_name)
            
            # Send server info including active users
            server_info = json.dumps({
                'type': 'SERVER_INFO',
                'supported_languages': list(CodeExecutor.SUPPORTED_LANGUAGES.keys()),
                'active_users': list(self.clients.keys()),
                'http_port': self.http_port,
                'file_upload_url': f'http://{self.host}:{self.http_port}/upload',
                'file_download_url': f'http://{self.host}:{self.http_port}/download',
                'file_list_url': f'http://{self.host}:{self.http_port}/files'
            })
            client_socket.send(f"SERVER_INFO|{server_info}".encode('utf-8'))
            log_networking(f"Sent server info to {client_name}", client_name)
            
            # Send user's groups immediately after connection
            user_groups = self.db.get_user_groups(client_name)
            if user_groups:
                groups_info = json.dumps({
                    'type': 'USER_GROUPS',
                    'groups': user_groups
                })
                client_socket.send(f"USER_GROUPS|{groups_info}".encode('utf-8'))
                log_networking(f"Sent user groups to {client_name}: {user_groups}", client_name)
                
                # Small delay to ensure groups are processed before history
                time.sleep(0.1)
            
            # Send general chat history immediately
            self.send_message_history(client_name, "BROADCAST", None)
            
            # Broadcast new client connection and update user lists
            self.broadcast_message(f"SERVER: {client_name} has joined the chat!")
            self.broadcast_user_list()
            log_networking(f" Announced {client_name}'s arrival to all clients")
            
            # Handle client messages
            log_networking(f"Starting message loop for {client_name}", client_name)
            while True:
                data = client_socket.recv(8192).decode('utf-8')
                if not data:
                    log_networking(f"No data received from {client_name}, closing connection", client_name)
                    break
                
                log_networking(f" Received from {client_name}: {data[:100]}{'...' if len(data) > 100 else ''}", client_name)
                self.process_message(client_name, data)
                
        except Exception as e:
            log_networking(f" Error handling client {client_address}: {e}", client_name)
        finally:
            # Clean up on disconnect
            if client_name and client_name in self.clients:
                del self.clients[client_name]
                log_networking(f" {client_name} disconnected, removed from client list", client_name)
                
                # Remove from code sessions
                sessions_removed = []
                for session_id in list(self.code_sessions.keys()):
                    if client_name in self.code_sessions[session_id]['participants']:
                        self.code_sessions[session_id]['participants'].remove(client_name)
                        sessions_removed.append(session_id)
                        log_code_session(f"{client_name} removed from session", session_id)
                        
                        # Notify other participants
                        self.broadcast_to_session(session_id, {
                            'type': 'user_left',
                            'user': client_name,
                            'participants': self.code_sessions[session_id]['participants']
                        })
                        
                        # Remove empty sessions
                        if len(self.code_sessions[session_id]['participants']) == 0:
                            del self.code_sessions[session_id]
                            log_code_session(f"Empty session deleted", session_id)
                
                if sessions_removed:
                    log_code_session(f"{client_name} was removed from {len(sessions_removed)} sessions")
                
                self.broadcast_message(f"SERVER: {client_name} has left the chat")
                self.broadcast_user_list()
                log_networking(f" Announced {client_name}'s departure to all clients")
            
            try:
                client_socket.close()
                log_networking(f" Socket closed for {client_name or client_address}")
            except:
                pass
    
    def broadcast_user_list(self):
        """Broadcast updated user list to all clients"""
        user_list = list(self.clients.keys())
        log_networking(f" Broadcasting user list update: {user_list}")
        
        user_list_data = json.dumps({
            'type': 'USER_LIST_UPDATE',
            'users': user_list
        })
        self.broadcast_message(f"USER_LIST|{user_list_data}", exclude=None, is_system=True)
    
    def process_message(self, sender, message):
        try:
            # Parse the message protocol
            parts = message.split('|', 2)
            message_type = parts[0]
            
            log_networking(f"🔍 Processing {message_type} message from {sender}", sender)
            
            if message_type == "BROADCAST":
                broadcast_msg = parts[1]
                log_networking(f" BROADCAST: {sender} -> ALL: {broadcast_msg}", sender)
                self.db.save_message(sender, broadcast_msg, "BROADCAST")
                self.broadcast_message(f"{sender}: {broadcast_msg}", exclude=None)
                
            elif message_type == "PERSONAL":
                recipient = parts[1]
                content = parts[2]
                log_networking(f" PERSONAL: {sender} -> {recipient}: {content}", sender)
                self.db.save_message(sender, content, "PERSONAL", recipient=recipient)
                self.send_personal_message(sender, recipient, content)
                
            elif message_type == "CREATE_GROUP":
                group_name = parts[1]
                members = parts[2].split(',') if len(parts) > 2 else []
                log_networking(f" CREATE_GROUP: {sender} creating '{group_name}' with members: {members}", sender)
                self.create_group(sender, group_name, members)
                
            elif message_type == "GROUP":
                group_name = parts[1]
                content = parts[2]
                log_networking(f" GROUP: {sender} -> [{group_name}]: {content}", sender)
                self.db.save_message(sender, content, "GROUP", group_name=group_name)
                self.send_group_message(sender, group_name, content)
                
            elif message_type == "LIST_CLIENTS":
                log_networking(f" LIST_CLIENTS request from {sender}", sender)
                client_list = ", ".join(self.clients.keys())
                self.send_personal_message("SERVER", sender, f"Connected clients: {client_list}")
                
            elif message_type == "LIST_GROUPS":
                log_networking(f" LIST_GROUPS request from {sender}", sender)
                user_groups = self.db.get_user_groups(sender)
                if user_groups:
                    group_list = ", ".join(user_groups)
                    self.send_personal_message("SERVER", sender, f"Your groups: {group_list}")
                else:
                    self.send_personal_message("SERVER", sender, "You are not a member of any groups")
            
            elif message_type == "GET_MESSAGES":
                msg_type = parts[1]
                target = parts[2] if len(parts) > 2 else None
                log_networking(f" GET_MESSAGES: {sender} requesting {msg_type} messages for {target}", sender)
                self.send_message_history(sender, msg_type, target)
            
            # File-related message handling
            elif message_type == "LIST_FILES":
                log_file_transfer(f"LIST_FILES request from {sender}")
                files = self.db.get_user_files(sender)
                files_info = {
                    'type': 'FILE_LIST',
                    'files': files
                }
                if sender in self.clients:
                    try:
                        self.clients[sender][0].send(f"FILE_LIST|{json.dumps(files_info)}".encode('utf-8'))
                        log_file_transfer(f"Sent {len(files)} files list to {sender}")
                    except:
                        log_file_transfer(f"Failed to send files list to {sender}", "ERROR")
            
            elif message_type == "DELETE_FILE":
                file_id = parts[1]
                log_file_transfer(f"DELETE_FILE request from {sender} for file {file_id}")
                success = self.db.delete_file(file_id, sender)
                response = {
                    'type': 'FILE_DELETE_RESPONSE',
                    'success': success,
                    'file_id': file_id
                }
                if sender in self.clients:
                    try:
                        self.clients[sender][0].send(f"FILE_DELETE_RESPONSE|{json.dumps(response)}".encode('utf-8'))
                        log_file_transfer(f"File deletion {'successful' if success else 'failed'} for {file_id}")
                    except:
                        log_file_transfer(f"Failed to send delete response to {sender}", "ERROR")
            
            # Code editor related messages
            elif message_type == "CREATE_CODE_SESSION":
                language = parts[1] if len(parts) > 1 else "python"
                log_code_session(f"{sender} creating new {language} session")
                self.handle_create_code_session(sender, language)
                
            elif message_type == "JOIN_CODE_SESSION":
                session_id = parts[1]
                log_code_session(f"{sender} joining session", session_id)
                self.handle_join_code_session(sender, session_id)
                
            elif message_type == "CODE_UPDATE":
                try:
                    update_data = json.loads(parts[1])
                    session_id = update_data.get('session_id')
                    log_code_session(f"Code update from {sender} ({len(update_data.get('code', ''))} chars)", session_id)
                    self.handle_code_update(sender, update_data)
                except json.JSONDecodeError:
                    log_code_session(f"Invalid JSON in CODE_UPDATE from {sender}", "ERROR")
                    
            elif message_type == "EXECUTE_CODE":
                try:
                    exec_data = json.loads(parts[1])
                    session_id = exec_data.get('session_id')
                    language = exec_data.get('language', 'python')
                    log_code_session(f"{sender} executing {language} code", session_id)
                    self.handle_code_execution(sender, exec_data)
                except json.JSONDecodeError:
                    log_code_session(f"Invalid JSON in EXECUTE_CODE from {sender}", "ERROR")
                    
            elif message_type == "INVITE_TO_CODE":
                try:
                    invite_data = json.loads(parts[1])
                    recipient = invite_data.get('recipient')
                    session_id = invite_data.get('session_id')
                    log_code_session(f"{sender} inviting {recipient} to session", session_id)
                    self.handle_code_invitation(sender, invite_data)
                except json.JSONDecodeError:
                    log_code_session(f"Invalid JSON in INVITE_TO_CODE from {sender}", "ERROR")
            
            else:
                log_networking(f" Unknown message type: {message_type} from {sender}", sender)
        
        except Exception as e:
            log_networking(f" Error processing message from {sender}: {e}", sender)
    
    def send_message_history(self, requester, msg_type, target):
        """Send message history to a client with improved reliability"""
        try:
            if msg_type == "BROADCAST":
                messages = self.db.get_messages("BROADCAST")
            elif msg_type == "PERSONAL":
                messages = self.db.get_messages("PERSONAL", requester, target)
            elif msg_type == "GROUP":
                messages = self.db.get_messages("GROUP", requester, target)
            else:
                log_networking(f"Invalid message type for history: {msg_type}", requester)
                return
            
            history_data = {
                'type': 'MESSAGE_HISTORY',
                'msg_type': msg_type,
                'target': target,
                'messages': []
            }
            
            for msg in messages:
                sender, content, timestamp, file_data = msg
                message_item = {
                    'sender': sender,
                    'content': content,
                    'timestamp': timestamp,
                    'file_data': file_data
                }
                history_data['messages'].append(message_item)
            
            if requester in self.clients:
                try:
                    history_json = json.dumps(history_data)
                    message_to_send = f"MESSAGE_HISTORY|{history_json}"
                    self.clients[requester][0].send(message_to_send.encode('utf-8'))
                    log_networking(f" Sent {len(messages)} message history ({msg_type}) to {requester}", requester)
                except Exception as send_error:
                    log_networking(f"Failed to send message history to {requester}: {send_error}", requester)
                    
        except Exception as e:
            log_networking(f"Error sending message history: {e}", requester)
    
    def create_group(self, creator, group_name, members):
        """Create a new chat group with database storage and improved notifications"""
        log_networking(f"👥 Creating group '{group_name}' by {creator} with members: {members}")
        
        if self.db.create_group(group_name, creator):
            # Add creator to group
            self.db.add_group_member(group_name, creator)
            
            valid_members = [creator]
            invalid_members = []
            
            for member in members:
                member = member.strip()
                if member and member in self.clients and member != creator:
                    self.db.add_group_member(group_name, member)
                    valid_members.append(member)
                    log_networking(f" Added {member} to group '{group_name}'")
                elif member and member != creator:
                    invalid_members.append(member)
                    log_networking(f" User {member} not found or offline")
            
            # Send group creation notification
            group_notification = f"SERVER: Group '{group_name}' created by {creator}"
            member_list = ", ".join(valid_members)
            group_notification += f"\nMembers: {member_list}"
            
            # Send group info to all members
            group_info = {
                'type': 'GROUP_CREATED',
                'group_name': group_name,
                'creator': creator,
                'members': valid_members
            }
            
            log_networking(f" Notifying {len(valid_members)} members about new group '{group_name}'")
            for member in valid_members:
                # Send text notification
                self.send_personal_message("SERVER", member, group_notification)
                # Send group creation data
                if member in self.clients:
                    try:
                        self.clients[member][0].send(f"GROUP_CREATED|{json.dumps(group_info)}".encode('utf-8'))
                        log_networking(f" Sent group creation info to {member}")
                    except Exception as e:
                        log_networking(f"Failed to send group info to {member}: {e}")
            
            if invalid_members:
                invalid_list = ", ".join(invalid_members)
                self.send_personal_message("SERVER", creator, 
                                         f"The following users were not found: {invalid_list}")
                log_networking(f" Invalid members in group creation: {invalid_list}")
        else:
            self.send_personal_message("SERVER", creator, f"Group '{group_name}' already exists")
            log_networking(f" Group '{group_name}' already exists")
    
    def send_group_message(self, sender, group_name, content):
        """Send a message to all members of a group"""
        group_members = self.db.get_group_members(group_name)
        
        if not group_members:
            self.send_personal_message("SERVER", sender, f"Group '{group_name}' does not exist")
            log_networking(f" Group '{group_name}' does not exist", sender)
            return
        
        if sender not in group_members:
            self.send_personal_message("SERVER", sender, f"You are not a member of group '{group_name}'")
            log_networking(f" {sender} not a member of group '{group_name}'", sender)
            return
        
        message = f"[{group_name}] {sender}: {content}"
        log_networking(f"👥 Broadcasting to group '{group_name}' ({len(group_members)} members): {content[:50]}...")
        
        # Send directly to group members
        delivered = 0
        for member in group_members:
            if member in self.clients:
                try:
                    self.clients[member][0].send(message.encode('utf-8'))
                    delivered += 1
                except:
                    log_networking(f"Failed to deliver group message to {member}")
        
        log_networking(f" Group message delivered to {delivered}/{len(group_members)} members")
    
    # Code editor methods with enhanced logging
    def handle_create_code_session(self, creator, language="python"):
        """Create a new code editing session"""
        session_id = str(uuid.uuid4())[:8]
        log_code_session(f"Creating new {language} session for {creator}", session_id)
        
        self.code_sessions[session_id] = {
            'code': f'# Welcome to collaborative {language} coding!\n# Start writing your code here...\n\n',
            'language': language or 'python',
            'participants': [creator],
            'owner': creator,
            'created_at': datetime.now().isoformat()
        }
        
        session_data = {
            'type': 'session_created',
            'session_id': session_id,
            'language': language or 'python',
            'code': self.code_sessions[session_id]['code']
        }
        
        if creator in self.clients:
            try:
                self.clients[creator][0].send(f"CODE_SESSION|{json.dumps(session_data)}".encode('utf-8'))
                log_code_session(f" Session created and sent to {creator}", session_id)
            except:
                log_code_session(f" Failed to send session to {creator}", session_id)
                
        log_code_session(f" Total active sessions: {len(self.code_sessions)}")
    
    def handle_join_code_session(self, user, session_id):
        """Add user to existing code session"""
        if session_id in self.code_sessions:
            if user not in self.code_sessions[session_id]['participants']:
                self.code_sessions[session_id]['participants'].append(user)
                log_code_session(f"{user} joined session (now {len(self.code_sessions[session_id]['participants'])} participants)", session_id)
                
                session_data = {
                    'type': 'session_joined',
                    'session_id': session_id,
                    'language': self.code_sessions[session_id]['language'],
                    'code': self.code_sessions[session_id]['code'],
                    'participants': self.code_sessions[session_id]['participants']
                }
                
                if user in self.clients:
                    try:
                        self.clients[user][0].send(f"CODE_SESSION|{json.dumps(session_data)}".encode('utf-8'))
                        log_code_session(f" Sent session data to {user}", session_id)
                    except:
                        log_code_session(f" Failed to send session data to {user}", session_id)
                
                self.broadcast_to_session(session_id, {
                    'type': 'user_joined',
                    'user': user,
                    'participants': self.code_sessions[session_id]['participants']
                }, exclude=user)
            else:
                log_code_session(f"{user} already in session", session_id)
        else:
            log_code_session(f" Session not found for {user}", session_id)
            if user in self.clients:
                try:
                    error_data = {'type': 'error', 'message': 'Code session not found'}
                    self.clients[user][0].send(f"CODE_SESSION|{json.dumps(error_data)}".encode('utf-8'))
                except:
                    pass
    
    def handle_code_update(self, sender, update_data):
        """Handle real-time code updates"""
        session_id = update_data.get('session_id')
        
        if session_id in self.code_sessions and sender in self.code_sessions[session_id]['participants']:
            code_length = len(update_data.get('code', ''))
            self.code_sessions[session_id]['code'] = update_data.get('code', '')
            log_code_session(f"Code updated by {sender} ({code_length} chars)", session_id)
            
            broadcast_data = {
                'type': 'code_update',
                'session_id': session_id,
                'code': update_data.get('code', ''),
                'user': sender,
                'cursor_pos': update_data.get('cursor_pos')
            }
            
            self.broadcast_to_session(session_id, broadcast_data, exclude=sender)
            log_code_session(f"Broadcasted code update to {len(self.code_sessions[session_id]['participants'])-1} participants", session_id)
        else:
            log_code_session(f" Invalid code update from {sender}", session_id)
    
    def handle_code_execution(self, sender, exec_data):
        """Handle code execution requests"""
        session_id = exec_data.get('session_id')
        
        if session_id in self.code_sessions and sender in self.code_sessions[session_id]['participants']:
            code = exec_data.get('code', self.code_sessions[session_id]['code'])
            language = exec_data.get('language', self.code_sessions[session_id]['language'])
            input_data = exec_data.get('input', '')
            
            log_code_session(f" Executing {language} code by {sender} ({len(code)} chars)", session_id)
            if input_data:
                log_code_session(f" Input provided: {input_data[:50]}{'...' if len(input_data) > 50 else ''}", session_id)
            
            # Execute code (this might take time)
            start_time = time.time()
            result = CodeExecutor.execute_code(code, language, input_data)
            execution_time = time.time() - start_time
            
            success = result.get('success', False)
            output = result.get('output', '')
            error = result.get('error', '')
            
            log_code_session(f" Execution {'successful' if success else 'failed'} in {execution_time:.2f}s", session_id)
            if output:
                log_code_session(f" Output: {output[:100]}{'...' if len(output) > 100 else ''}", session_id)
            if error:
                log_code_session(f" Error: {error[:100]}{'...' if len(error) > 100 else ''}", session_id)
            
            result_data = {
                'type': 'execution_result',
                'session_id': session_id,
                'result': result,
                'executed_by': sender
            }
            
            self.broadcast_to_session(session_id, result_data)
            log_code_session(f" Execution result broadcasted to all participants", session_id)
        else:
            log_code_session(f" Invalid execution request from {sender}", session_id)
    
    def handle_code_invitation(self, sender, invite_data):
        """Handle code session invitations"""
        recipient = invite_data.get('recipient')
        session_id = invite_data.get('session_id')
        
        log_code_session(f"{sender} inviting {recipient} to session", session_id)
        
        if recipient in self.clients and session_id in self.code_sessions:
            invitation = {
                'type': 'code_invitation',
                'from': sender,
                'session_id': session_id,
                'language': self.code_sessions[session_id]['language']
            }
            
            try:
                self.clients[recipient][0].send(f"CODE_SESSION|{json.dumps(invitation)}".encode('utf-8'))
                log_code_session(f" Invitation sent to {recipient}", session_id)
            except:
                log_code_session(f" Failed to send invitation to {recipient}", session_id)
        else:
            log_code_session(f" Cannot invite {recipient} (not online or session not found)", session_id)
    
    def broadcast_to_session(self, session_id, data, exclude=None):
        """Broadcast message to all participants in a code session"""
        if session_id in self.code_sessions:
            participants = self.code_sessions[session_id]['participants']
            message = f"CODE_SESSION|{json.dumps(data)}"
            
            sent_count = 0
            for participant in participants:
                if exclude and participant == exclude:
                    continue
                if participant in self.clients:
                    try:
                        self.clients[participant][0].send(message.encode('utf-8'))
                        sent_count += 1
                    except:
                        log_code_session(f"Failed to send to {participant}", session_id)
            
            log_code_session(f"Broadcasted to {sent_count}/{len(participants)} participants", session_id)
        else:
            log_code_session(f" Cannot broadcast to non-existent session", session_id)
    
    def broadcast_message(self, message, exclude=None, is_system=False):
        """Send a message to all connected clients"""
        recipients = [name for name in self.clients.keys() if name != exclude]
        log_networking(f" Broadcasting to {len(recipients)} clients: {message[:50]}...")
        
        sent_count = 0
        for client_name, (client_socket, _) in self.clients.items():
            if exclude and client_name == exclude:
                continue
            try:
                client_socket.send(message.encode('utf-8'))
                sent_count += 1
            except:
                log_networking(f"Failed to broadcast to {client_name}")
        
        log_networking(f" Broadcast delivered to {sent_count}/{len(recipients)} clients")
    
    def send_personal_message(self, sender, recipient, content):
        """Send a private message to a specific client"""
        log_networking(f" Sending personal message: {sender} -> {recipient}: {content[:50]}...")
        
        if recipient in self.clients:
            recipient_socket = self.clients[recipient][0]
            message = f"PM from {sender}: {content}"
            try:
                recipient_socket.send(message.encode('utf-8'))
                log_networking(f" Personal message delivered to {recipient}")
                
                if sender != "SERVER" and sender in self.clients:
                    sender_socket = self.clients[sender][0]
                    sender_socket.send(f"PM to {recipient}: {content}".encode('utf-8'))
                    log_networking(f" Confirmation sent to {sender}")
            except Exception as e:
                log_networking(f" Failed to deliver personal message to {recipient}: {e}")
                if sender != "SERVER" and sender in self.clients:
                    try:
                        sender_socket = self.clients[sender][0]
                        sender_socket.send(f"SERVER: Failed to send message to {recipient}".encode('utf-8'))
                    except:
                        pass
        else:
            log_networking(f" Recipient {recipient} not found")
            if sender != "SERVER" and sender in self.clients:
                try:
                    sender_socket = self.clients[sender][0]
                    sender_socket.send(f"SERVER: User '{recipient}' not found".encode('utf-8'))
                except:
                    pass

if __name__ == "__main__":
    print("=" * 60)
    print(" STARTING ENHANCED CHAT SERVER WITH DETAILED LOGGING")
    print("=" * 60)
    
    server = ChatServer()
    server.start()