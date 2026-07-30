import socket
import subprocess
import threading

def handle_client(conn):
    proc = subprocess.Popen(['python3', '/root/agents/-Octopus/skills/mcp/skills_mcp_server.py'], 
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    def forward_stdout():
        for line in proc.stdout:
            conn.sendall(line.encode())
    
    threading.Thread(target=forward_stdout, daemon=True).start()
    
    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            proc.stdin.write(data.decode())
            proc.stdin.flush()
    except:
        pass
    finally:
        proc.terminate()
        conn.close()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('127.0.0.1', 9566))
server.listen(5)
print("MCP TCP Server listening on 9566")
while True:
    conn, addr = server.accept()
    threading.Thread(target=handle_client, args=(conn,)).start()
