import socket
import json
import traceback

code = r"""
import bpy
import bmesh
import math
from mathutils import Matrix, Vector

# 1. ลบโมเดลเก่าทิ้งทั้งหมด
for obj in list(bpy.data.objects):
    if obj.name.startswith("skel_") or obj.name.startswith("joint_") or obj.name == "Cup":
        bpy.data.objects.remove(obj, do_unlink=True)

# 2. สร้างแก้วน้ำ (Cup) แบบกลวงและบาง (Hollow & Thin)
# ใช้ NOTHING เพื่อไม่ให้มีฝาปิดหัวท้าย
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.035, depth=0.10, end_fill_type='NOTHING', location=(0,0,0))
cup = bpy.context.active_object
cup.name = "Cup"

# เพิ่มความหนาให้แก้วบางๆ
solid_mod = cup.modifiers.new("Solidify", 'SOLIDIFY')
solid_mod.thickness = 0.002

# ตั้งค่าสีแดงให้แก้ว
mat_cup = bpy.data.materials.new("RedCup")
mat_cup.use_nodes = True
bsdf = mat_cup.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.9, 0.05, 0.05, 1.0)
bsdf.inputs["Roughness"].default_value = 0.1
# เพิ่มความโปร่งใสให้ดูเป็นแก้วบาง
bsdf.inputs["Alpha"].default_value = 0.6
mat_cup.blend_method = 'BLEND'
cup.data.materials.append(mat_cup)

arm = bpy.data.objects.get("HandRig")
if arm:
    # รีเซ็ตตำแหน่งมือให้อยู่จุดศูนย์กลาง
    arm.location = (0, 0, 0)
    R = Matrix(((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)))
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = R.to_euler('XYZ')
    
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    
    # เคลียร์ Pose เก่า
    for pb in arm.pose.bones:
        pb.location = (0,0,0)
        pb.rotation_euler = (0,0,0)
        for i in range(3): pb.lock_rotation[i] = True
        
    bpy.ops.object.mode_set(mode="OBJECT")

# 3. จัดตำแหน่งแก้วให้อยู่ที่ "ต้นข้อนิ้ว" (โคนนิ้วติดกับอุ้งมือ)
# แกน Y ของมือชี้ไปทางนิ้ว, อุ้งมือยาวประมาณ 0.055, ให้แก้วอยู่ประมาณ Y=0.06 และ Z ยกขึ้นมาให้พอดีกำ
# ปรับให้แก้วอยู่ในจุดที่เส้นสีแดงของนายท่านชี้พอดี
cup_grasp_loc = arm.matrix_world @ Vector((0.0, 0.06, -0.01))
cup.location = cup_grasp_loc
# ให้แก้วตั้งตรงตามแกนโลก
cup.rotation_euler = (0, 0, 0)

# 4. สร้างรูปทรงกระดูก 3D
bone_mat = bpy.data.materials.new("RealBone")
bone_mat.use_nodes = True
bone_bsdf = bone_mat.node_tree.nodes["Principled BSDF"]
bone_bsdf.inputs["Base Color"].default_value = (0.9, 0.88, 0.85, 1.0)
bone_bsdf.inputs["Roughness"].default_value = 0.35

def create_bone_mesh(name, length, radius, flatten=False):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    
    if flatten:
        # อุ้งมือ: ทำให้ป่องออกเล็กน้อยตรงกลาง ไม่เป็นรูปโบว์ (Bow-tie)
        rings = [
            (0.0, radius * 1.0),
            (length * 0.5, radius * 1.3),
            (length, radius * 1.5)
        ]
        segments = 16
        z_scale = 0.3
        x_scale = 2.2
    else:
        rings = [
            (0.0, radius * 1.5),
            (length * 0.15, radius * 0.7),
            (length * 0.50, radius * 0.45),
            (length * 0.85, radius * 0.7),
            (length, radius * 1.4)
        ]
        segments = 12
        z_scale = 1.0
        x_scale = 1.0
        
    circle_verts = [(math.cos(2*math.pi*i/segments)*x_scale, math.sin(2*math.pi*i/segments)*z_scale) for i in range(segments)]
    created_rings = [[bm.verts.new((cx*r, y, cz*r)) for cx, cz in circle_verts] for y, r in rings]
    
    for r_idx in range(len(created_rings) - 1):
        r1, r2 = created_rings[r_idx], created_rings[r_idx + 1]
        for i in range(segments):
            bm.faces.new((r1[i], r1[(i+1)%segments], r2[(i+1)%segments], r2[i]))
    
    bm.faces.new(reversed(created_rings[0]))
    bm.faces.new(created_rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    
    for poly in mesh.polygons: poly.use_smooth = True
    obj.data.materials.append(bone_mat)
    sub = obj.modifiers.new("Subdivision", 'SUBSURF')
    sub.levels = 1
    return obj

if arm:
    for bone in arm.data.bones:
        L = bone.length
        if L < 1e-4: continue
        
        if bone.name == "palm":
            c = create_bone_mesh("skel_" + bone.name, L, 0.015, flatten=True)
        elif bone.name in ["root", "wrist"]:
            c = create_bone_mesh("skel_" + bone.name, L, 0.01)
        else:
            c = create_bone_mesh("skel_" + bone.name, L, 0.0035)
            
        c.parent = arm
        c.parent_type = "BONE"
        c.parent_bone = bone.name
        c.matrix_parent_inverse = Matrix.Identity(4)
        c.location = (0, -L, 0)
        c.rotation_euler = (0,0,0)

# ลูกแก้วข้อต่อ
for i in range(21):
    ename = f"LM_{i:02d}"
    e = bpy.data.objects.get(ename)
    if not e: continue
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.004, location=(0,0,0))
    s = bpy.context.active_object
    s.name = "joint_" + ename
    s.data.materials.append(bone_mat)
    for p in s.data.polygons: p.use_smooth = True
    s.parent = arm
    s.parent_type = "BONE"
    s.parent_bone = e.parent_bone
    s.matrix_parent_inverse = Matrix.Identity(4)
    s.location = e.location.copy()

# 5. ทำ Animation: กางมือ -> กำแก้ว -> ยกแก้ว
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 90

if arm:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    
    angles_grasp = {
        "f_index.01": -math.radians(75), "f_index.02": -math.radians(55), "f_index.03": -math.radians(45),
        "f_middle.01": -math.radians(80), "f_middle.02": -math.radians(60), "f_middle.03": -math.radians(50),
        "f_ring.01": -math.radians(85), "f_ring.02": -math.radians(65), "f_ring.03": -math.radians(55),
        "f_pinky.01": -math.radians(90), "f_pinky.02": -math.radians(70), "f_pinky.03": -math.radians(60),
        "thumb.01": math.radians(40), "thumb.02": -math.radians(25), "thumb.03": -math.radians(15),
    }
    
    root_bone = arm.pose.bones["root"]
    
    # Frame 1: กางมือ
    root_bone.location = (0, -0.1, 0) # ถอยมือออกไปก่อน
    root_bone.keyframe_insert(data_path="location", frame=1)
    for bn in angles_grasp.keys():
        if bn in arm.pose.bones:
            arm.pose.bones[bn].rotation_euler[0] = 0
            arm.pose.bones[bn].keyframe_insert(data_path="rotation_euler", index=0, frame=1)
            
    # Frame 30: เอื้อมมือมาถึงแก้ว (Reach)
    root_bone.location = (0, 0, 0)
    root_bone.keyframe_insert(data_path="location", frame=30)
    for bn in angles_grasp.keys():
        if bn in arm.pose.bones:
            arm.pose.bones[bn].keyframe_insert(data_path="rotation_euler", index=0, frame=30)
            
    # Frame 45: กำแก้ว (Grasp)
    root_bone.keyframe_insert(data_path="location", frame=45)
    for bn, ang in angles_grasp.items():
        if bn in arm.pose.bones:
            arm.pose.bones[bn].rotation_euler[0] = ang
            arm.pose.bones[bn].keyframe_insert(data_path="rotation_euler", index=0, frame=45)
            
    # Frame 72: ยกแก้วขึ้น (Lift)
    root_bone.location = (-0.1, 0, 0) # ยกขึ้นตามแกน X ใน local (ซึ่งคือ Z ใน global เพราะถูกหมุนไว้)
    root_bone.keyframe_insert(data_path="location", frame=72)
    for bn in angles_grasp.keys():
        if bn in arm.pose.bones:
            arm.pose.bones[bn].keyframe_insert(data_path="rotation_euler", index=0, frame=72)

    # Frame 90: ถือค้างไว้
    root_bone.keyframe_insert(data_path="location", frame=90)
    for bn in angles_grasp.keys():
        if bn in arm.pose.bones:
            arm.pose.bones[bn].keyframe_insert(data_path="rotation_euler", index=0, frame=90)
            
    bpy.ops.object.mode_set(mode="OBJECT")

# อนิเมทแก้วน้ำให้ขยับตามมือตั้งแต่ Frame 45 เป็นต้นไป
cup.location = cup_grasp_loc
cup.keyframe_insert(data_path="location", frame=1)
cup.keyframe_insert(data_path="location", frame=45)

# หาตำแหน่งแก้วตอนที่มือยกขึ้น (Frame 72)
arm.pose.bones["root"].location = (-0.1, 0, 0)
bpy.context.view_layer.update()
cup_lift_loc = arm.matrix_world @ Vector((0.0, 0.06, -0.01))
cup.location = cup_lift_loc
cup.keyframe_insert(data_path="location", frame=72)
cup.keyframe_insert(data_path="location", frame=90)

# คืนค่ากลับไป Frame 1
bpy.context.scene.frame_set(1)

# ปรับมุมกล้องให้เห็นชัดๆ
cam = bpy.data.objects.get("Camera")
if cam:
    cam.location = (0.2, -0.2, 0.15)
    cam.rotation_euler = (cup.location - cam.location).to_track_quat("-Z", "Y").to_euler()

# สั่งให้เล่น Animation ทันที!
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
