# file_transfer.py - With Detailed Logging
import threading
import json
import uuid
import mimetypes
import sqlite3
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Enhanced logging functions
def log_http(message, level="INFO", client_ip=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client_info = f"[{client_ip}]" if client_ip else "[HTTP]"
    print(f"[HTTP {level}] {timestamp} {client_info} {message}")

def log_file_operation(message, operation="TRANSFER", file_info=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    file_details = f"[{file_info}]" if file_info else "[FILE]"
    print(f"[FILE {operation}] {timestamp} {file_details} {message}")

def log_database_file(message, operation="DB"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[FILE_DB {operation}] {timestamp} - {message}")

class FileTransferHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, database=None, clients=None, **kwargs):
        self.database = database
        self.clients = clients
        self.client_ip = None
        super().__init__(*args, **kwargs)
    
    def setup(self):
        super().setup()
        self.client_ip = self.client_address[0]
        log_http(f"New HTTP connection established", client_ip=self.client_ip)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        log_http("CORS preflight request received", client_ip=self.client_ip)
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        log_http("CORS headers sent", client_ip=self.client_ip)
    
    def do_GET(self):
        """Handle file download requests"""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            log_http(f"GET request: {path}", client_ip=self.client_ip)
            
            if path.startswith('/download/'):
                file_id = path.split('/')[-1]
                log_file_operation(f"Download request for file ID: {file_id}", "DOWNLOAD", self.client_ip)
                self.handle_file_download(file_id)
            elif path == '/files':
                query_params = parse_qs(parsed_url.query)
                user = query_params.get('user', [None])[0]
                log_file_operation(f"File list request for user: {user}", "LIST", self.client_ip)
                self.handle_file_list(user)
            else:
                log_http(f"❌ Unknown endpoint: {path}", "ERROR", self.client_ip)
                self.send_error(404, "Endpoint not found")
        except Exception as e:
            log_http(f"❌ Error in GET request: {e}", "ERROR", self.client_ip)
            self.send_error(500, "Internal server error")
    
    def do_POST(self):
        """Handle file upload requests"""
        try:
            log_http(f"POST request: {self.path}", client_ip=self.client_ip)
            if self.path == '/upload':
                log_file_operation("File upload started", "UPLOAD", self.client_ip)
                self.handle_file_upload()
            else:
                log_http(f"❌ Unknown POST endpoint: {self.path}", "ERROR", self.client_ip)
                self.send_error(404, "Endpoint not found")
        except Exception as e:
            log_http(f"❌ Error in POST request: {e}", "ERROR", self.client_ip)
            self.send_error(500, "Internal server error")
    
    def handle_file_upload(self):
        """Handle file upload via POST request"""
        try:
            content_type = self.headers.get('Content-Type', '')
            log_file_operation(f"Upload content type: {content_type}", "UPLOAD")
            
            if not content_type.startswith('multipart/form-data'):
                log_file_operation("❌ Invalid content type", "UPLOAD")
                self.send_error(400, "Content-Type must be multipart/form-data")
                return
            
            content_length = int(self.headers.get('Content-Length', 0))
            log_file_operation(f"Upload size: {content_length} bytes ({content_length/1024:.1f} KB)", "UPLOAD")
            
            if content_length == 0:
                log_file_operation("❌ No content received", "UPLOAD")
                self.send_error(400, "No content received")
                return
            
            # Read the request body
            log_file_operation("Reading upload data...", "UPLOAD")
            post_data = self.rfile.read(content_length)
            log_file_operation(f"✅ Read {len(post_data)} bytes", "UPLOAD")
            
            # Parse multipart data
            log_file_operation("Parsing multipart data...", "UPLOAD")
            boundary = content_type.split('boundary=')[1].encode()
            parts = post_data.split(b'--' + boundary)
            log_file_operation(f"Found {len(parts)} parts in multipart data", "UPLOAD")
            
            file_data = None
            filename = None
            sender = None
            recipient = None
            group_name = None
            
            for i, part in enumerate(parts):
                if b'Content-Disposition' in part:
                    log_file_operation(f"Processing part {i}", "UPLOAD")
                    lines = part.split(b'\r\n')
                    for j, line in enumerate(lines):
                        if b'Content-Disposition' in line:
                            if b'name="file"' in line:
                                # Extract filename
                                if b'filename=' in line:
                                    filename = line.split(b'filename=')[1].strip(b'"').decode('utf-8')
                                    log_file_operation(f"📄 Filename: {filename}", "UPLOAD")
                                # Find file data
                                data_start = part.find(b'\r\n\r\n') + 4
                                if data_start > 3:
                                    file_data = part[data_start:].rstrip(b'\r\n')
                                    log_file_operation(f"📦 File data: {len(file_data)} bytes", "UPLOAD")
                            elif b'name="sender"' in line:
                                data_start = part.find(b'\r\n\r\n') + 4
                                if data_start > 3:
                                    sender = part[data_start:].rstrip(b'\r\n').decode('utf-8')
                                    log_file_operation(f"👤 Sender: {sender}", "UPLOAD")
                            elif b'name="recipient"' in line:
                                data_start = part.find(b'\r\n\r\n') + 4
                                if data_start > 3:
                                    recipient = part[data_start:].rstrip(b'\r\n').decode('utf-8')
                                    log_file_operation(f"👤 Recipient: {recipient}", "UPLOAD")
                            elif b'name="group_name"' in line:
                                data_start = part.find(b'\r\n\r\n') + 4
                                if data_start > 3:
                                    group_name = part[data_start:].rstrip(b'\r\n').decode('utf-8')
                                    log_file_operation(f"👥 Group: {group_name}", "UPLOAD")
            
            if not file_data or not filename or not sender:
                log_file_operation("❌ Missing required fields", "UPLOAD")
                self.send_error(400, "Missing required fields: file, filename, or sender")
                return
            
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            log_file_operation(f"🆔 Generated file ID: {file_id}", "UPLOAD")
            
            # Determine target
            target = group_name or recipient or "BROADCAST"
            log_file_operation(f"🎯 Target: {target}", "UPLOAD")
            
            # Save file to database
            log_file_operation(f"💾 Saving file to database...", "UPLOAD")
            success = self.database.save_file(file_id, filename, file_data, sender, recipient, group_name)
            
            if success:
                log_file_operation(f"✅ File saved successfully", "UPLOAD")
                
                # Notify relevant clients
                log_file_operation(f"📢 Notifying clients...", "UPLOAD")
                self.notify_file_upload(file_id, filename, sender, recipient, group_name)
                
                # Send success response
                response = {
                    'status': 'success',
                    'file_id': file_id,
                    'filename': filename,
                    'download_url': f'/download/{file_id}'
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
                log_file_operation(f"✅ Upload complete - sent response", "UPLOAD")
            else:
                log_file_operation(f"❌ Failed to save file to database", "UPLOAD")
                self.send_error(500, "Failed to save file")
                
        except Exception as e:
            log_file_operation(f"❌ Upload error: {e}", "UPLOAD")
            self.send_error(500, f"Upload error: {str(e)}")
    
    def handle_file_download(self, file_id):
        """Handle file download via GET request"""
        try:
            log_file_operation(f"🔍 Looking up file ID: {file_id}", "DOWNLOAD")
            file_info = self.database.get_file(file_id)
            
            if not file_info:
                log_file_operation(f"❌ File not found: {file_id}", "DOWNLOAD")
                self.send_error(404, "File not found")
                return
            
            filename, file_data, sender, recipient, group_name, timestamp = file_info
            log_file_operation(f"✅ File found: {filename} ({len(file_data)} bytes, from {sender})", "DOWNLOAD")
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = 'application/octet-stream'
            log_file_operation(f"📋 Content type: {content_type}", "DOWNLOAD")
            
            # Send file
            log_file_operation(f"📤 Sending file to client...", "DOWNLOAD")
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(len(file_data)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(file_data)
            log_file_operation(f"✅ Download complete: {filename}", "DOWNLOAD")
            
        except Exception as e:
            log_file_operation(f"❌ Download error: {e}", "DOWNLOAD")
            self.send_error(500, "Download error")
    
    def handle_file_list(self, user):
        """Handle file listing request"""
        try:
            if not user:
                log_file_operation("❌ No user specified for file list", "LIST")
                self.send_error(400, "User parameter required")
                return
            
            log_file_operation(f"📋 Getting file list for user: {user}", "LIST")
            files = self.database.get_user_files(user)
            log_file_operation(f"✅ Found {len(files)} files for {user}", "LIST")
            
            response = {
                'status': 'success',
                'files': files
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            log_file_operation(f"✅ File list sent to {user}", "LIST")
            
        except Exception as e:
            log_file_operation(f"❌ File list error: {e}", "LIST")
            self.send_error(500, "List error")
    
    def notify_file_upload(self, file_id, filename, sender, recipient, group_name):
        """Notify clients about new file upload"""
        try:
            file_notification = {
                'type': 'FILE_UPLOADED',
                'file_id': file_id,
                'filename': filename,
                'sender': sender,
                'recipient': recipient,
                'group_name': group_name,
                'download_url': f'/download/{file_id}',
                'timestamp': datetime.now().isoformat()
            }
            
            message = f"FILE_NOTIFICATION|{json.dumps(file_notification)}"
            
            # Determine who to notify
            notified_users = []
            
            if group_name:
                # Notify all group members
                log_file_operation(f" Notifying group '{group_name}' about file upload", "NOTIFY")
                group_members = self.database.get_group_members(group_name)
                log_file_operation(f" Group has {len(group_members)} members: {group_members}", "NOTIFY")
                
                for member in group_members:
                    if member in self.clients:
                        try:
                            self.clients[member][0].send(message.encode('utf-8'))
                            notified_users.append(member)
                            log_file_operation(f" Notified group member: {member}", "NOTIFY")
                        except Exception as e:
                            log_file_operation(f" Failed to notify {member}: {e}", "NOTIFY")
                            
            elif recipient:
                # Notify specific recipient and sender
                log_file_operation(f" Notifying private chat participants", "NOTIFY")
                
                if recipient in self.clients:
                    try:
                        self.clients[recipient][0].send(message.encode('utf-8'))
                        notified_users.append(recipient)
                        log_file_operation(f" Notified recipient: {recipient}", "NOTIFY")
                    except Exception as e:
                        log_file_operation(f" Failed to notify recipient {recipient}: {e}", "NOTIFY")
                        
                if sender in self.clients and sender != recipient:
                    try:
                        self.clients[sender][0].send(message.encode('utf-8'))
                        notified_users.append(sender)
                        log_file_operation(f" Notified sender: {sender}", "NOTIFY")
                    except Exception as e:
                        log_file_operation(f" Failed to notify sender {sender}: {e}", "NOTIFY")
                        
            else:
                # Broadcast to all clients
                log_file_operation(f" Broadcasting file notification to all clients", "NOTIFY")
                
                for client_name, (client_socket, _) in self.clients.items():
                    try:
                        client_socket.send(message.encode('utf-8'))
                        notified_users.append(client_name)
                        log_file_operation(f" Notified client: {client_name}", "NOTIFY")
                    except Exception as e:
                        log_file_operation(f" Failed to notify {client_name}: {e}", "NOTIFY")
            
            log_file_operation(f" Notification summary: {len(notified_users)} users notified", "NOTIFY")
            
        except Exception as e:
            log_file_operation(f" Notification error: {e}", "NOTIFY")
    
    def log_message(self, format, *args):
        """Override to reduce HTTP server logging"""
        return  # Comment this out if you want HTTP logs

class FileTransferServer:
    def __init__(self, host='localhost', port=8080, database=None, clients=None):
        self.host = host
        self.port = port
        self.database = database
        
        self.clients = clients
        self.http_server = None
        self.server_thread = None
        
        log_http(f"FileTransferServer initialized on {host}:{port}")
        
    def start(self):
        """Start the HTTP file transfer server"""
        log_http(f"Starting HTTP file transfer server...")
        
        def handler(*args, **kwargs):
            return FileTransferHandler(*args, database=self.database, clients=self.clients, **kwargs)
        
        try:
            self.http_server = HTTPServer((self.host, self.port), handler)
            log_http(f" HTTP server socket bound to {self.host}:{self.port}")
        except Exception as e:
            log_http(f" Failed to bind HTTP server: {e}", "ERROR")
            raise
        
        def run_server():
            try:
                log_http(f" HTTP file transfer server listening on {self.host}:{self.port}")
                log_http(f" Available endpoints:")
                log_http(f"  - POST /upload (file uploads)")
                log_http(f"  - GET /download/<file_id> (file downloads)")
                log_http(f"  - GET /files?user=<username> (file listing)")
                log_http("=" * 50)
                self.http_server.serve_forever()
            except Exception as e:
                log_http(f" HTTP server error: {e}", "ERROR")
        
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        log_http(f" HTTP server thread started")
        return f"http://{self.host}:{self.port}"
    
    def stop(self):
        """Stop the HTTP file transfer server"""
        log_http(" Stopping HTTP file transfer server...")
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
            log_http(" HTTP file transfer server stopped")

# Database extensions for file handling
class FileTransferDatabase:
    """Mixin class to add file transfer capabilities to your existing database"""
    
    def init_file_tables(self):
        """Initialize file-related tables"""
        log_database_file("Initializing file transfer tables")
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Enhanced files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                file_data BLOB NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT,
                group_name TEXT,
                file_size INTEGER,
                mime_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        log_database_file("File transfer tables initialized")
    
    def save_file(self, file_id, filename, file_data, sender, recipient=None, group_name=None):
        """Save a file to the database"""
        try:
            target = group_name or recipient or "BROADCAST"
            log_database_file(f"Saving file: {filename} ({len(file_data)} bytes) from {sender} to {target}")
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'
            log_database_file(f"MIME type determined: {mime_type}")
            
            cursor.execute('''
                INSERT INTO shared_files (file_id, filename, file_data, sender, recipient, group_name, file_size, mime_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (file_id, filename, file_data, sender, recipient, group_name, len(file_data), mime_type))
            
            conn.commit()
            conn.close()
            log_database_file(f" File saved successfully with ID: {file_id}")
            return True
        except Exception as e:
            log_database_file(f" Error saving file: {e}")
            return False
    
    def get_file(self, file_id):
        """Retrieve a file from the database"""
        try:
            log_database_file(f"Retrieving file with ID: {file_id}")
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT filename, file_data, sender, recipient, group_name, timestamp
                FROM shared_files 
                WHERE file_id = ?
            ''', (file_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                filename, file_data, sender, recipient, group_name, timestamp = result
                log_database_file(f" File found: {filename} ({len(file_data)} bytes)")
            else:
                log_database_file(f" File not found: {file_id}")
                
            return result
        except Exception as e:
            log_database_file(f" Error retrieving file: {e}")
            return None
    
    def get_user_files(self, username):
        """Get all files accessible to a user"""
        try:
            log_database_file(f"Getting accessible files for user: {username}")
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get user's groups
            cursor.execute('SELECT group_name FROM group_members WHERE member = ?', (username,))
            user_groups = [row[0] for row in cursor.fetchall()]
            log_database_file(f"User {username} is in groups: {user_groups}")
            
            # Build query for files accessible to user
            conditions = ['sender = ?', 'recipient = ?']
            params = [username, username]
            
            # Add group conditions
            if user_groups:
                group_conditions = ['group_name = ?'] * len(user_groups)
                conditions.extend(group_conditions)
                params.extend(user_groups)
            
            # Add files with no specific recipient (broadcast files)
            conditions.append('(recipient IS NULL AND group_name IS NULL)')
            
            query = f'''
                SELECT file_id, filename, sender, recipient, group_name, file_size, mime_type, timestamp
                FROM shared_files 
                WHERE {' OR '.join(conditions)}
                ORDER BY timestamp DESC
            '''
            
            cursor.execute(query, params)
            files = []
            for row in cursor.fetchall():
                files.append({
                    'file_id': row[0],
                    'filename': row[1],
                    'sender': row[2],
                    'recipient': row[3],
                    'group_name': row[4],
                    'file_size': row[5],
                    'mime_type': row[6],
                    'timestamp': row[7],
                    'download_url': f'/download/{row[0]}'
                })
            
            conn.close()
            log_database_file(f" Found {len(files)} accessible files for {username}")
            return files
        except Exception as e:
            log_database_file(f" Error getting user files: {e}")
            return []
    
    def get_group_members(self, group_name):
        log_database_file(f"Getting members for group: {group_name}")
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT member FROM group_members WHERE group_name = ?", (group_name,))
        members = [row[0] for row in cursor.fetchall()]
        conn.close()
        log_database_file(f"Group {group_name} has {len(members)} members")
        return members
