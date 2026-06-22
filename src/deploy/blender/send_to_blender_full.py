import socket
import json
import traceback

code = r"""
import sys
import os
import bpy
from mathutils import Vector, Matrix

# 1. Clean the scene completely
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

# 2. Add some basic lighting
light_data = bpy.data.lights.new(name="Light", type='SUN')
light_data.energy = 5.0
light_obj = bpy.data.objects.new(name="Light", object_data=light_data)
bpy.context.collection.objects.link(light_obj)
light_obj.location = (2, 2, 5)
light_obj.rotation_euler = (0.7, 0, 0.7)

# 3. Build the rig using rig_hand.py
rig_path = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\src\deploy\blender\rig_hand.py"
with open(rig_path, "r", encoding="utf-8") as f:
    exec(f.read(), {"__name__": "__main__"})

# 4. Run the procedural skeleton script
skel_path = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\src\deploy\blender\apply_procedural_skeleton.py"
with open(skel_path, "r", encoding="utf-8") as f:
    exec(f.read(), {"__name__": "__main__"})

# Ensure view updates
bpy.context.view_layer.update()

result = {"status": "success"}
"""

request = {
    "type": "execute",
    "code": code,
    "strict_json": False
}

payload = json.dumps(request).encode('utf-8') + b'\0'

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(15.0)
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
