import socket
import json
import traceback

code = r"""
import bpy
from mathutils import Vector

cup = bpy.data.objects.get("Cup")
arm = bpy.data.objects.get("HandRig")

if cup and arm:
    # เคลียร์ Keyframe เก่าของแก้วทั้งหมดเพื่อความชัวร์
    if cup.animation_data:
        cup.animation_data_clear()
        
    # ดึงตำแหน่งที่เฟรม 45 (ตอนมือกำแก้วพอดี)
    bpy.context.scene.frame_set(45)
    bpy.context.view_layer.update()
    
    # เราใช้วิธีคำนวณจากตำแหน่งกระดูก palm แทน จะได้แม่นยำ 100% ว่ามืออยู่ไหน
    palm_bone = arm.pose.bones["palm"]
    
    # ตำแหน่ง Global ของกระดูก palm ตอนที่กำแก้วอยู่บนโต๊ะ
    palm_global_matrix = arm.matrix_world @ palm_bone.matrix
    
    # ให้แก้วอยู่ตรงกลางอุ้งมือพอดี (ขยับ Y ออกมานิดนึงให้พอดีกำ)
    # สมมติให้แก้วอยู่ห่างจากโคนนิ้ว (tail ของ palm)
    cup_grasp_loc = palm_global_matrix @ Vector((0, 0.06, -0.01))
    
    # ล็อก Keyframe เฟรม 1 ถึง 45 ให้แก้วตั้งอยู่กับที่
    for f in [1, 30, 45]:
        bpy.context.scene.frame_set(f)
        cup.location = cup_grasp_loc
        cup.keyframe_insert(data_path="location", frame=f)
        
    # ดึงตำแหน่งที่เฟรม 72 (ตอนมือยกขึ้นไปแล้ว)
    bpy.context.scene.frame_set(72)
    bpy.context.view_layer.update()
    palm_global_matrix_lifted = arm.matrix_world @ palm_bone.matrix
    cup_lift_loc = palm_global_matrix_lifted @ Vector((0, 0.06, -0.01))
    
    # ล็อก Keyframe เฟรม 72 และ 90 ให้แก้วขยับตามไปเป๊ะๆ
    for f in [72, 90]:
        bpy.context.scene.frame_set(f)
        cup.location = cup_lift_loc
        cup.keyframe_insert(data_path="location", frame=f)
        
    # กลับไปเล่นเฟรมแรก
    bpy.context.scene.frame_set(1)

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
                break
except Exception as e:
    pass
