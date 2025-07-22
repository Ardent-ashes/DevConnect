# 🚀 DevConnect 


A comprehensive communication platform integrating messaging, file sharing, and collaborative code editing with Python TCP/HTTP protocols.

## ✨ Features

- **💬 Real-time Messaging**: Broadcast, private, and group chat with persistent history
- **👨‍💻 Collaborative Code Editor**: Multi-user real-time coding in Python, JavaScript, Java, C++, C
- **📁 File Sharing**: HTTP-based upload/download with context-aware sharing
- **🎨 Modern GUI**: Tabbed interface with online user tracking and intuitive design

## 🛠️ Tech Stack

- **Python 3+** 
- **TCP Sockets** for real-time messaging (Port 5555)
- **HTTP Server** for RESTful file operations (Port 8080)
- **SQLite** database for persistent storage
- **Multi-threading** for concurrent user handling
- **customtkinter/tkinter** for UI
- **Node.js (JavaScript), GCC/G++ (C/C++), Java JDK** for code execution on server side



## 🚀 Quick Start

### Start Server
```bash
python3 server.py
```

### Start Client
```bash
python3 client.py
```

### Usage
1. **Login**: Enter username and server details
2. **Chat**: Send messages, create private/group conversations
3. **Code**: Click "Code Editor" → Choose language → Invite users → Code together
4. **Files**: Click "File" button to upload, click links to download

## 📡 Protocol Reference

### TCP Messages
```python
"BROADCAST|message"
"PERSONAL|recipient|message"
"GROUP|group_name|message"
"CREATE_GROUP|group_name|members"
"CODE_UPDATE|{session_data}"
```

### HTTP API
```http
POST /upload          # Upload files
GET /download/{id}    # Download files
GET /files?user={u}   # List user files
```

## 🏗️ Architecture

```
Client (GUI) ←→ TCP Server (Chat) ←→ SQLite Database
             ←→ HTTP Server (Files) ←→
```

**Thread Model:**
- Main TCP Thread (1)
- HTTP Server Thread (1) 
- Client Handler Threads (N users)
- HTTP Request Threads (M requests)
- Code Execution Subprocesses (K executions)

## 🔧 Configuration

```python
# Server settings (enhanced_server_with_database.py)
HOST = '192.168.176.113'  # Change to your IP
TCP_PORT = 5555
HTTP_PORT = 8080
```

## 🧪 Testing

Run multiple clients to test messaging, file sharing, and code collaboration:
```bash
python client.py  # User 1
python client.py  # User 2
python client.py  # User 3
```

## ⚠️ Security Notice

This is an **educational project** with basic security:
- No encryption (plain text communication)
- Simple username authentication
- Sandboxed code execution with timeouts


## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/name`)
5. Open Pull Request


## 👨‍💻 Author

**Papry Rahman**
- GitHub: [@Ardent-ashes](https://github.com/Ardent-ashes)
- Email: papryrahman59@example.com
**Rubaiya Tarannum Mrittika**
- GitHub: [@mri17](https://github.com/mri17)
- Email:....@example.com

---

⭐ **Star this project if you found it helpful!** ⭐
