import socket
import json

code = r"""
import bpy
import os

# 1. ซ่อน Object ที่ไม่ต้องการ
for obj in bpy.data.objects:
    if obj.type == 'EMPTY':
        obj.hide_render = True
        obj.hide_set(True)
    if obj.name == "Table":
        obj.hide_render = True
        obj.hide_set(True)

# 2. เลือกเฉพาะสิ่งที่ต้องการ Export
bpy.ops.object.select_all(action='DESELECT')
export_names = []
for obj in bpy.data.objects:
    if obj.name.startswith("skel_") or obj.name.startswith("joint_") or obj.name == "Cup" or obj.name == "HandRig":
        obj.select_set(True)
        obj.hide_set(False)
        export_names.append(obj.name)

# 3. Export เป็น GLB
export_path = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\src\frontend\public\reference_hand.glb"
os.makedirs(os.path.dirname(export_path), exist_ok=True)

bpy.ops.export_scene.gltf(
    filepath=export_path,
    export_format='GLB',
    use_selection=True,
    export_animations=True,
    export_apply=True,
)

result = {"status": "success", "exported": export_names, "path": export_path}
"""

request = {"type": "execute", "code": code, "strict_json": False}
payload = json.dumps(request).encode('utf-8') + b'\0'

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(30.0)
        s.connect(('127.0.0.1', 9876))
        s.sendall(payload)
        data = bytearray()
        while b'\0' not in data:
            try:
                chunk = s.recv(4096)
                if not chunk: break
                data.extend(chunk)
            except socket.timeout:
                break
    if b'\0' in data:
        print('Response:', data[:data.index(b'\0')].decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
