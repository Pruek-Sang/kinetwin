import socket
import json
import traceback

code = r"""
import bpy
from mathutils import Vector

arm = bpy.data.objects.get("HandRig")
cup = bpy.data.objects.get("Cup")

if arm and cup:
    # ยกแขนขึ้น 0.15
    arm.location.z += 0.15
    
    # อัปเดตเฟรมของแก้วให้ยกตาม 0.15 ตลอดทุก Keyframe
    for f in [1, 45, 72, 90]:
        bpy.context.scene.frame_set(f)
        cup.location.z += 0.15
        cup.keyframe_insert(data_path="location", frame=f)

    # เปลี่ยนโต๊ะให้เป็นสีเทาเข้มเพื่อไม่ให้สะท้อนแสงแยงตา (แผ่นขาวๆ)
    table = bpy.data.objects.get("Table")
    if table:
        mat_table = bpy.data.materials.get("TableMat")
        if not mat_table:
            mat_table = bpy.data.materials.new("TableMat")
            mat_table.use_nodes = True
            mat_table.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.1, 0.1, 0.1, 1.0)
            mat_table.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
        
        if not table.data.materials:
            table.data.materials.append(mat_table)
        else:
            table.data.materials[0] = mat_table

    # เลื่อนกล้องขึ้น 0.15
    cam = bpy.data.objects.get("Camera")
    if cam:
        cam.location.z += 0.15

    bpy.context.scene.frame_set(1)
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
