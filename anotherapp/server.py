# enhanced_server_with_database.py
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

class ChatDatabase:
    def __init__(self, db_file="chat_history.db"):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
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
        
        # Groups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT UNIQUE NOT NULL,
                creator TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
        
        # Files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                file_data BLOB NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT,
                group_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_message(self, sender, content, message_type, recipient=None, group_name=None, file_data=None):
        """Save a message to the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (sender, recipient, group_name, content, message_type, file_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sender, recipient, group_name, content, message_type, file_data))
        
        conn.commit()
        conn.close()
    
    def get_messages(self, message_type, user1=None, user2_or_group=None, limit=50):
        """Retrieve messages from the database"""
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
            # Get messages between two users
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
        return list(reversed(messages))  # Return in chronological order
    
    def create_group(self, group_name, creator):
        """Create a new group"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO groups (group_name, creator) VALUES (?, ?)', 
                          (group_name, creator))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def add_group_member(self, group_name, member):
        """Add a member to a group"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO group_members (group_name, member) 
            VALUES (?, ?)
        ''', (group_name, member))
        
        conn.commit()
        conn.close()
    
    def get_group_members(self, group_name):
        """Get all members of a group"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT member FROM group_members WHERE group_name = ?
        ''', (group_name,))
        
        members = [row[0] for row in cursor.fetchall()]
        conn.close()
        return members
    
    def get_user_groups(self, username):
        """Get all groups a user is a member of"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT group_name FROM group_members WHERE member = ?
        ''', (username,))
        
        groups = [row[0] for row in cursor.fetchall()]
        conn.close()
        return groups
    
    def remove_group_member(self, group_name, member):
        """Remove a member from a group"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM group_members WHERE group_name = ? AND member = ?
        ''', (group_name, member))
        
        conn.commit()
        conn.close()
    
    def save_file(self, file_id, filename, file_data, sender, recipient=None, group_name=None):
        """Save a file to the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO shared_files (file_id, filename, file_data, sender, recipient, group_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (file_id, filename, file_data, sender, recipient, group_name))
        
        conn.commit()
        conn.close()
    
    def get_file(self, file_id):
        """Retrieve a file from the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT filename, file_data FROM shared_files WHERE file_id = ?
        ''', (file_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result

class ChatServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.clients = {}  # {client_name: (client_socket, client_address)}
        self.db = ChatDatabase()
        
        # Code editor sessions
        self.code_sessions = {}  # {session_id: {code, language, participants, owner}}
        
    def start(self):
        self.server_socket.listen(5)
        print(f"Chat server started on {self.host}:{self.port}")
        print("Supported programming languages:", list(CodeExecutor.SUPPORTED_LANGUAGES.keys()))
        
        try:
            while True:
                client_socket, client_address = self.server_socket.accept()
                client_thread = threading.Thread(target=self.handle_client, 
                                               args=(client_socket, client_address))
                client_thread.daemon = True
                client_thread.start()
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            self.server_socket.close()
            
    def handle_client(self, client_socket, client_address):
        client_name = None
        try:
            # Get client name
            client_name = client_socket.recv(1024).decode('utf-8')
            
            # Check if name already exists
            if client_name in self.clients:
                client_socket.send("NAME_TAKEN".encode('utf-8'))
                client_socket.close()
                return
            
            # Add client to clients dictionary
            self.clients[client_name] = (client_socket, client_address)
            client_socket.send("CONNECTED".encode('utf-8'))
            
            # Send server info including active users
            server_info = json.dumps({
                'type': 'SERVER_INFO',
                'supported_languages': list(CodeExecutor.SUPPORTED_LANGUAGES.keys()),
                'active_users': list(self.clients.keys())
            })
            client_socket.send(f"SERVER_INFO|{server_info}".encode('utf-8'))
            
            # Send user's groups
            user_groups = self.db.get_user_groups(client_name)
            if user_groups:
                groups_info = json.dumps({
                    'type': 'USER_GROUPS',
                    'groups': user_groups
                })
                client_socket.send(f"USER_GROUPS|{groups_info}".encode('utf-8'))
            
            # Broadcast new client connection and update user lists
            self.broadcast_message(f"SERVER: {client_name} has joined the chat!")
            self.broadcast_user_list()
            print(f"New connection: {client_name} ({client_address})")
            
            # Handle client messages
            while True:
                data = client_socket.recv(8192).decode('utf-8')  # Increased buffer for files
                if not data:
                    break
                
                # Process the message based on protocol
                self.process_message(client_name, data)
                
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            # Clean up on disconnect
            if client_name and client_name in self.clients:
                del self.clients[client_name]
                
                # Remove from code sessions
                for session_id in list(self.code_sessions.keys()):
                    if client_name in self.code_sessions[session_id]['participants']:
                        self.code_sessions[session_id]['participants'].remove(client_name)
                        # Notify other participants
                        self.broadcast_to_session(session_id, {
                            'type': 'user_left',
                            'user': client_name
                        })
                        # Remove empty sessions
                        if len(self.code_sessions[session_id]['participants']) == 0:
                            del self.code_sessions[session_id]
                
                self.broadcast_message(f"SERVER: {client_name} has left the chat")
                self.broadcast_user_list()
                print(f"Connection closed: {client_name}")
            
            try:
                client_socket.close()
            except:
                pass
    
    def broadcast_user_list(self):
        """Broadcast updated user list to all clients"""
        user_list = json.dumps({
            'type': 'USER_LIST_UPDATE',
            'users': list(self.clients.keys())
        })
        self.broadcast_message(f"USER_LIST|{user_list}", exclude=None, is_system=True)
    
    def process_message(self, sender, message):
        try:
            # Parse the message protocol
            parts = message.split('|', 2)
            message_type = parts[0]
            
            if message_type == "BROADCAST":
                broadcast_msg = parts[1]
                self.db.save_message(sender, broadcast_msg, "BROADCAST")
                self.broadcast_message(f"{sender}: {broadcast_msg}", exclude=None)
                
            elif message_type == "PERSONAL":
                recipient = parts[1]
                content = parts[2]
                self.db.save_message(sender, content, "PERSONAL", recipient=recipient)
                self.send_personal_message(sender, recipient, content)
                
            elif message_type == "CREATE_GROUP":
                group_name = parts[1]
                members = parts[2].split(',') if len(parts) > 2 else []
                self.create_group(sender, group_name, members)
                
            elif message_type == "GROUP":
                group_name = parts[1]
                content = parts[2]
                self.db.save_message(sender, content, "GROUP", group_name=group_name)
                self.send_group_message(sender, group_name, content)
                
            elif message_type == "LIST_CLIENTS":
                client_list = ", ".join(self.clients.keys())
                self.send_personal_message("SERVER", sender, f"Connected clients: {client_list}")
                
            elif message_type == "LIST_GROUPS":
                user_groups = self.db.get_user_groups(sender)
                if user_groups:
                    group_list = ", ".join(user_groups)
                    self.send_personal_message("SERVER", sender, f"Your groups: {group_list}")
                else:
                    self.send_personal_message("SERVER", sender, "You are not a member of any groups")
            
            elif message_type == "GET_MESSAGES":
                msg_type = parts[1]
                target = parts[2] if len(parts) > 2 else None
                self.send_message_history(sender, msg_type, target)
                    
            elif message_type == "FILE_SHARE":
                try:
                    file_data = json.loads(parts[1])
                    self.handle_file_share(sender, file_data)
                except json.JSONDecodeError:
                    self.send_personal_message("SERVER", sender, "Invalid file sharing data")
            
            elif message_type == "GET_FILE":
                file_id = parts[1]
                self.send_file(sender, file_id)
            
            # Code editor related messages
            elif message_type == "CREATE_CODE_SESSION":
                self.handle_create_code_session(sender, parts[1] if len(parts) > 1 else "")
                
            elif message_type == "JOIN_CODE_SESSION":
                session_id = parts[1]
                self.handle_join_code_session(sender, session_id)
                
            elif message_type == "CODE_UPDATE":
                try:
                    update_data = json.loads(parts[1])
                    self.handle_code_update(sender, update_data)
                except json.JSONDecodeError:
                    pass
                    
            elif message_type == "EXECUTE_CODE":
                try:
                    exec_data = json.loads(parts[1])
                    self.handle_code_execution(sender, exec_data)
                except json.JSONDecodeError:
                    pass
                    
            elif message_type == "INVITE_TO_CODE":
                try:
                    invite_data = json.loads(parts[1])
                    self.handle_code_invitation(sender, invite_data)
                except json.JSONDecodeError:
                    pass
        
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def send_message_history(self, requester, msg_type, target):
        """Send message history to a client"""
        try:
            if msg_type == "BROADCAST":
                messages = self.db.get_messages("BROADCAST")
            elif msg_type == "PERSONAL":
                messages = self.db.get_messages("PERSONAL", requester, target)
            elif msg_type == "GROUP":
                messages = self.db.get_messages("GROUP", requester, target)
            else:
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
                    self.clients[requester][0].send(f"MESSAGE_HISTORY|{json.dumps(history_data)}".encode('utf-8'))
                except:
                    pass
                    
        except Exception as e:
            print(f"Error sending message history: {e}")
    
    def handle_file_share(self, sender, file_data):
        """Handle file sharing with database storage"""
        try:
            filename = file_data.get('filename')
            file_content = file_data.get('content')  # Base64 encoded
            file_size = file_data.get('size', 0)
            recipient = file_data.get('recipient')
            group_name = file_data.get('group')
            
            print(f"Processing file share from {sender}: {filename}")  # Debug
            
            if not filename or not file_content:
                self.send_personal_message("SERVER", sender, "Invalid file data")
                return
            
            # Generate unique file ID
            file_id = str(uuid.uuid4())[:12]
            
            # Decode base64 content
            try:
                file_bytes = base64.b64decode(file_content)
            except Exception as e:
                print(f"Error decoding file: {e}")
                self.send_personal_message("SERVER", sender, "Failed to decode file data")
                return
            
            # Save file to database
            self.db.save_file(file_id, filename, file_bytes, sender, recipient, group_name)
            
            # Create file sharing message
            file_msg_data = {
                'type': 'FILE_SHARED',
                'sender': sender,
                'filename': filename,
                'file_id': file_id,
                'file_size': len(file_bytes)
            }
            
            file_msg = f"📎 {sender} shared file: {filename} ({len(file_bytes)} bytes)"
            
            if recipient:
                # Private file share
                print(f"Sharing file privately with {recipient}")  # Debug
                self.db.save_message(sender, file_msg, "PERSONAL", recipient=recipient, file_data=json.dumps(file_msg_data))
                if recipient in self.clients:
                    try:
                        self.clients[recipient][0].send(f"FILE_SHARED|{json.dumps(file_msg_data)}".encode('utf-8'))
                        print(f"File share message sent to {recipient}")  # Debug
                    except Exception as e:
                        print(f"Error sending file to {recipient}: {e}")
                        pass
                    self.send_personal_message("SERVER", sender, f"File '{filename}' shared with {recipient}")
                else:
                    self.send_personal_message("SERVER", sender, f"User '{recipient}' not found")
                    
            elif group_name:
                # Group file share
                print(f"Sharing file with group {group_name}")  # Debug
                group_members = self.db.get_group_members(group_name)
                if sender in group_members:
                    self.db.save_message(sender, file_msg, "GROUP", group_name=group_name, file_data=json.dumps(file_msg_data))
                    file_msg_data['group'] = group_name
                    for member in group_members:
                        if member != sender and member in self.clients:
                            try:
                                self.clients[member][0].send(f"FILE_SHARED|{json.dumps(file_msg_data)}".encode('utf-8'))
                            except:
                                pass
                    self.send_personal_message("SERVER", sender, f"File '{filename}' shared with group '{group_name}'")
                else:
                    self.send_personal_message("SERVER", sender, f"You are not a member of group '{group_name}'")
            else:
                # Broadcast file share
                print(f"Broadcasting file to everyone")  # Debug
                self.db.save_message(sender, file_msg, "BROADCAST", file_data=json.dumps(file_msg_data))
                for client_name, (client_socket, _) in self.clients.items():
                    if client_name != sender:
                        try:
                            client_socket.send(f"FILE_SHARED|{json.dumps(file_msg_data)}".encode('utf-8'))
                        except:
                            pass
                self.send_personal_message("SERVER", sender, f"File '{filename}' shared with everyone")
                
        except Exception as e:
            print(f"Error handling file share: {e}")
            self.send_personal_message("SERVER", sender, f"Failed to share file: {str(e)}")
    
    def send_file(self, requester, file_id):
        """Send file to requester"""
        try:
            print(f"Sending file {file_id} to {requester}")  # Debug
            file_info = self.db.get_file(file_id)
            if file_info:
                filename, file_data = file_info
                file_content_b64 = base64.b64encode(file_data).decode('utf-8')
                
                response_data = {
                    'type': 'FILE_DOWNLOAD',
                    'file_id': file_id,
                    'filename': filename,
                    'content': file_content_b64
                }
                
                if requester in self.clients:
                    try:
                        self.clients[requester][0].send(f"FILE_DOWNLOAD|{json.dumps(response_data)}".encode('utf-8'))
                        print(f"File {filename} sent to {requester}")  # Debug
                    except Exception as e:
                        print(f"Error sending file to {requester}: {e}")
                        pass
            else:
                print(f"File {file_id} not found in database")  # Debug
                self.send_personal_message("SERVER", requester, f"File not found: {file_id}")
                
        except Exception as e:
            print(f"Error sending file: {e}")
            self.send_personal_message("SERVER", requester, f"Error retrieving file: {str(e)}")
    
    def create_group(self, creator, group_name, members):
        """Create a new chat group with database storage"""
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
                elif member and member != creator:
                    invalid_members.append(member)
            
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
            
            for member in valid_members:
                self.send_personal_message("SERVER", member, group_notification)
                if member in self.clients:
                    try:
                        self.clients[member][0].send(f"GROUP_CREATED|{json.dumps(group_info)}".encode('utf-8'))
                    except:
                        pass
            
            if invalid_members:
                invalid_list = ", ".join(invalid_members)
                self.send_personal_message("SERVER", creator, 
                                         f"The following users were not found: {invalid_list}")
        else:
            self.send_personal_message("SERVER", creator, f"Group '{group_name}' already exists")
    
    def send_group_message(self, sender, group_name, content):
        """Send a message to all members of a group"""
        group_members = self.db.get_group_members(group_name)
        
        if not group_members:
            self.send_personal_message("SERVER", sender, f"Group '{group_name}' does not exist")
            return
        
        if sender not in group_members:
            self.send_personal_message("SERVER", sender, f"You are not a member of group '{group_name}'")
            return
        
        message = f"[{group_name}] {sender}: {content}"
        for member in group_members:
            if member != sender:
                self.send_personal_message("SERVER", member, message)
        
        self.send_personal_message("SERVER", sender, f"Message sent to group '{group_name}'")
    
    # Code editor methods (unchanged from original)
    def handle_create_code_session(self, creator, language="python"):
        """Create a new code editing session"""
        session_id = str(uuid.uuid4())[:8]
        
        self.code_sessions[session_id] = {
            'code': '# Welcome to collaborative coding!\n# Start writing your code here...\n\n',
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
            except:
                pass
    
    def handle_join_code_session(self, user, session_id):
        """Add user to existing code session"""
        if session_id in self.code_sessions:
            if user not in self.code_sessions[session_id]['participants']:
                self.code_sessions[session_id]['participants'].append(user)
                
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
                    except:
                        pass
                
                self.broadcast_to_session(session_id, {
                    'type': 'user_joined',
                    'user': user,
                    'participants': self.code_sessions[session_id]['participants']
                }, exclude=user)
        else:
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
            self.code_sessions[session_id]['code'] = update_data.get('code', '')
            
            broadcast_data = {
                'type': 'code_update',
                'session_id': session_id,
                'code': update_data.get('code', ''),
                'user': sender,
                'cursor_pos': update_data.get('cursor_pos')
            }
            
            self.broadcast_to_session(session_id, broadcast_data, exclude=sender)
    
    def handle_code_execution(self, sender, exec_data):
        """Handle code execution requests"""
        session_id = exec_data.get('session_id')
        
        if session_id in self.code_sessions and sender in self.code_sessions[session_id]['participants']:
            code = exec_data.get('code', self.code_sessions[session_id]['code'])
            language = exec_data.get('language', self.code_sessions[session_id]['language'])
            input_data = exec_data.get('input', '')
            
            result = CodeExecutor.execute_code(code, language, input_data)
            
            result_data = {
                'type': 'execution_result',
                'session_id': session_id,
                'result': result,
                'executed_by': sender
            }
            
            self.broadcast_to_session(session_id, result_data)
    
    def handle_code_invitation(self, sender, invite_data):
        """Handle code session invitations"""
        recipient = invite_data.get('recipient')
        session_id = invite_data.get('session_id')
        
        if recipient in self.clients and session_id in self.code_sessions:
            invitation = {
                'type': 'code_invitation',
                'from': sender,
                'session_id': session_id,
                'language': self.code_sessions[session_id]['language']
            }
            
            try:
                self.clients[recipient][0].send(f"CODE_SESSION|{json.dumps(invitation)}".encode('utf-8'))
            except:
                pass
    
    def broadcast_to_session(self, session_id, data, exclude=None):
        """Broadcast message to all participants in a code session"""
        if session_id in self.code_sessions:
            message = f"CODE_SESSION|{json.dumps(data)}"
            for participant in self.code_sessions[session_id]['participants']:
                if exclude and participant == exclude:
                    continue
                if participant in self.clients:
                    try:
                        self.clients[participant][0].send(message.encode('utf-8'))
                    except:
                        pass
    
    def broadcast_message(self, message, exclude=None, is_system=False):
        """Send a message to all connected clients"""
        for client_name, (client_socket, _) in self.clients.items():
            if exclude and client_name == exclude:
                continue
            try:
                client_socket.send(message.encode('utf-8'))
            except:
                pass
    
    def send_personal_message(self, sender, recipient, content):
        """Send a private message to a specific client"""
        if recipient in self.clients:
            recipient_socket = self.clients[recipient][0]
            message = f"PM from {sender}: {content}"
            try:
                recipient_socket.send(message.encode('utf-8'))
                if sender != "SERVER":
                    sender_socket = self.clients[sender][0]
                    sender_socket.send(f"PM to {recipient}: {content}".encode('utf-8'))
            except:
                if sender != "SERVER":
                    sender_socket = self.clients[sender][0]
                    sender_socket.send(f"SERVER: Failed to send message to {recipient}".encode('utf-8'))
        else:
            if sender != "SERVER":
                sender_socket = self.clients[sender][0]
                sender_socket.send(f"SERVER: User '{recipient}' not found".encode('utf-8'))

if __name__ == "__main__":
    server = ChatServer()
    server.start()