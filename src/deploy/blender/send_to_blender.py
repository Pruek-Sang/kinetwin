import socket
import json
import traceback

with open(r'c:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\src\deploy\blender\apply_procedural_skeleton.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add a result variable so mcp_to_blender_server.py is happy
code += '\n\nresult = {"status": "success"}\n'

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
            try:
                chunk = s.recv(4096)
                if not chunk: break
                data.extend(chunk)
            except socket.timeout:
                print('Timeout waiting for response')
                break

    if b'\0' in data:
        resp = data[:data.index(b'\0')].decode('utf-8')
        print('Response:', resp)
    else:
        print('No complete response received.')
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
