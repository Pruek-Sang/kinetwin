import socket
import json
import traceback

code = r"""
import bpy
import bmesh
import math
from mathutils import Matrix, Vector

arm = bpy.data.objects.get("HandRig")
cup = bpy.data.objects.get("Cup")

if arm and cup:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    
    root_bone = arm.pose.bones["root"]
    
    # ดึงค่าตำแหน่งแก้วเดิม (ตอนวางอยู่บนโต๊ะ)
    # ซึ่งตั้งไว้ที่ cup_grasp_loc ในสคริปต์ที่แล้ว
    
    # ให้ Frame 72 และ 90 ยกมือ 'ขึ้น' (ค่าบวกของแกน X ใน Local Space = แกน Z ใน Global)
    bpy.context.scene.frame_set(72)
    root_bone.location = (0.1, 0, 0) 
    root_bone.keyframe_insert(data_path="location", frame=72)
    
    bpy.context.scene.frame_set(90)
    root_bone.location = (0.1, 0, 0)
    root_bone.keyframe_insert(data_path="location", frame=90)
    
    bpy.ops.object.mode_set(mode="OBJECT")
    
    # อนิเมทแก้วน้ำให้ถูกยก 'ขึ้น' ตามมือ (บวกค่า Z ไป 0.1)
    # ดึงตำแหน่งที่เฟรม 45 (ตอนแก้วยังวางอยู่)
    bpy.context.scene.frame_set(45)
    cup_base_loc = cup.location.copy()
    
    # กำหนดตำแหน่งตอนยกขึ้น (เฟรม 72)
    cup_lift_loc = cup_base_loc + Vector((0.0, 0.0, 0.1))
    
    bpy.context.scene.frame_set(72)
    cup.location = cup_lift_loc
    cup.keyframe_insert(data_path="location", frame=72)
    
    bpy.context.scene.frame_set(90)
    cup.location = cup_lift_loc
    cup.keyframe_insert(data_path="location", frame=90)
    
    # คืนค่าไปที่เฟรมแรกแล้วกด Play ใหม่
    bpy.context.scene.frame_set(1)
    
    # รีเซ็ตมุมกล้องให้เห็นชัดๆ
    cam = bpy.data.objects.get("Camera")
    if cam:
        cam.location = (0.2, -0.2, 0.25)
        cam.rotation_euler = (cup_base_loc - cam.location).to_track_quat("-Z", "Y").to_euler()

    bpy.ops.screen.animation_play()

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
