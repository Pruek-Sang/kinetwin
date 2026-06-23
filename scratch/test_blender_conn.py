import socket
import json
import traceback

code = """
import bpy
print("--- Blender MCP Python execution start ---")
print("Blender version:", bpy.app.version_string)
result = {"status": "success", "version": bpy.app.version_string}
"""

request = {
    "type": "execute",
    "code": code,
    "strict_json": False
}

payload = json.dumps(request).encode('utf-8') + b'\0'

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5.0)
        s.connect(('127.0.0.1', 9876))
        s.sendall(payload)
        
        data = bytearray()
        while b'\0' not in data:
            chunk = s.recv(4096)
            if not chunk: break
            data.extend(chunk)
            
    if b'\0' in data:
        resp = data[:data.index(b'\0')].decode('utf-8')
        print('Response:', resp)
    else:
        print('No complete response received.')
except Exception as e:
    print(f"Error: {e}")
