import socket
import json
import traceback

code = r"""
import bpy
import math
from mathutils import Vector

arm = bpy.data.objects.get("HandRig")
cup = bpy.data.objects.get("Cup")

if arm and cup:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    
    # 1. ปรับองศานิ้วให้กางออกไปข้างหน้าก่อน แล้วค่อยงอรัดรอบแก้ว (ลดการหักข้อนิ้วแรก)
    # ทำให้มือดูเอื้อมไปข้างหน้ามากขึ้น และนิ้วไปรัดขอบแก้วอีกฝั่งได้พอดีโดยไม่ทะลุ
    angles_grasp = {
        "f_index.01": -math.radians(10), "f_index.02": -math.radians(35), "f_index.03": -math.radians(25),
        "f_middle.01": -math.radians(12), "f_middle.02": -math.radians(35), "f_middle.03": -math.radians(25),
        "f_ring.01": -math.radians(15), "f_ring.02": -math.radians(35), "f_ring.03": -math.radians(25),
        "f_pinky.01": -math.radians(18), "f_pinky.02": -math.radians(35), "f_pinky.03": -math.radians(25),
        # หัวแม่มือหักเข้ามาล็อกแก้วด้านหลัง
        "thumb.01": math.radians(25), "thumb.02": math.radians(15), "thumb.03": math.radians(10),
    }
    
    # อัปเดต Keyframe นิ้ว
    for f in [45, 72, 90]:
        bpy.context.scene.frame_set(f)
        for bn, ang in angles_grasp.items():
            if bn in arm.pose.bones:
                arm.pose.bones[bn].rotation_euler[0] = ang
                arm.pose.bones[bn].keyframe_insert(data_path="rotation_euler", index=0, frame=f)
    
    bpy.ops.object.mode_set(mode="OBJECT")

    # 2. ขยับแก้วขึ้นหน้าไปอีก (Y เพิ่มขึ้น) 
    # ทำให้แก้วไปอยู่ตรงปลายนิ้วพอดี นิ้วจะได้โค้งรัดพอดีขอบแก้วด้านหน้าโดยไม่ทะลุเนื้อ
    if cup.animation_data:
        cup.animation_data_clear()
        
    palm_bone = arm.pose.bones["palm"]
    
    # เฟรม 45 (ตอนกำแก้ว)
    bpy.context.scene.frame_set(45)
    bpy.context.view_layer.update()
    
    # ขยับ Y ไปที่ 0.105 (ขึ้นหน้าไปอีก 2.5 ซม. จากเดิม 0.08)
    cup_grasp_loc = (arm.matrix_world @ palm_bone.matrix) @ Vector((0.0, 0.105, -0.045))
    
    for f in [1, 30, 45]:
        bpy.context.scene.frame_set(f)
        cup.location = cup_grasp_loc
        cup.keyframe_insert(data_path="location", frame=f)
        
    # เฟรม 72 (ตอนยกขึ้น)
    bpy.context.scene.frame_set(72)
    bpy.context.view_layer.update()
    cup_lift_loc = (arm.matrix_world @ palm_bone.matrix) @ Vector((0.0, 0.105, -0.045))
    
    for f in [72, 90]:
        bpy.context.scene.frame_set(f)
        cup.location = cup_lift_loc
        cup.keyframe_insert(data_path="location", frame=f)
        
    # รีเซ็ตกลับไปเฟรมแรกและเล่น
    bpy.context.scene.frame_set(1)
    if not bpy.context.screen.is_animation_playing:
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
                break
except Exception as e:
    pass
