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
    # 1. ทำให้แก้วเป็นสีแดงในโหมด Solid Viewport ด้วย!
    mat_cup = bpy.data.materials.get("RedCup")
    if mat_cup:
        # เปลี่ยนสีสำหรับการมองผ่านหน้าจอ (Viewport Display)
        mat_cup.diffuse_color = (0.9, 0.05, 0.05, 0.6)
    
    # บังคับเปิดโหมด Material Preview เพื่อให้เห็นความใสและสีสันเต็มรูปแบบ
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    
    # 2. ปรับการดัดนิ้ว (Grasp Pose) ให้โอบรอบแก้วโดยไม่ทะลุ
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    
    # ปรับองศานิ้วให้กำแบบหลวมๆ โอบตามโค้งของแก้ว (แก้วรัศมี 3.5cm นิ้วยาวไม่พอจะกำมิด)
    angles_grasp = {
        "f_index.01": -math.radians(40), "f_index.02": -math.radians(35), "f_index.03": -math.radians(30),
        "f_middle.01": -math.radians(40), "f_middle.02": -math.radians(35), "f_middle.03": -math.radians(30),
        "f_ring.01": -math.radians(40), "f_ring.02": -math.radians(35), "f_ring.03": -math.radians(30),
        "f_pinky.01": -math.radians(40), "f_pinky.02": -math.radians(35), "f_pinky.03": -math.radians(30),
        "thumb.01": math.radians(20), "thumb.02": math.radians(10), "thumb.03": math.radians(10),
    }
    
    # อัปเดต Keyframe นิ้วในเฟรม 45, 72, 90
    for f in [45, 72, 90]:
        bpy.context.scene.frame_set(f)
        for bn, ang in angles_grasp.items():
            if bn in arm.pose.bones:
                arm.pose.bones[bn].rotation_euler[0] = ang
                arm.pose.bones[bn].keyframe_insert(data_path="rotation_euler", index=0, frame=f)
    
    # 3. จัดตำแหน่งแก้วให้อยู่ที่ "ขอบ" ของนิ้วและอุ้งมือ ไม่ให้ทะลุ
    if cup.animation_data:
        cup.animation_data_clear()
        
    palm_bone = arm.pose.bones["palm"]
    
    # เฟรม 45 (ตอนกำแก้วบนโต๊ะ)
    bpy.context.scene.frame_set(45)
    bpy.context.view_layer.update()
    
    # กระดูกอุ้งมือ (palm) ยาว 7.5cm (Y=0.075) แก้วรัศมี 3.5cm (0.035) 
    # ดังนั้นให้จุดศูนย์กลางแก้วห่างออกไปที่ Y = 0.075 (สุดอุ้งมือ) + 0.035 (รัศมีแก้ว) + 0.005 (ช่องว่าง) = 0.115
    cup_grasp_loc = (arm.matrix_world @ palm_bone.matrix) @ Vector((0.0, 0.115, -0.015))
    
    for f in [1, 30, 45]:
        bpy.context.scene.frame_set(f)
        cup.location = cup_grasp_loc
        cup.keyframe_insert(data_path="location", frame=f)
        
    # เฟรม 72 (ตอนยกแก้วขึ้น)
    bpy.context.scene.frame_set(72)
    bpy.context.view_layer.update()
    cup_lift_loc = (arm.matrix_world @ palm_bone.matrix) @ Vector((0.0, 0.115, -0.015))
    
    for f in [72, 90]:
        bpy.context.scene.frame_set(f)
        cup.location = cup_lift_loc
        cup.keyframe_insert(data_path="location", frame=f)
        
    bpy.ops.object.mode_set(mode="OBJECT")
    
    # รีเซ็ตกล้องให้เห็นภาพรวม
    cam = bpy.data.objects.get("Camera")
    if cam:
        cam.location = (0.25, -0.1, 0.25)
        cam.rotation_euler = (cup_grasp_loc - cam.location).to_track_quat("-Z", "Y").to_euler()

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
