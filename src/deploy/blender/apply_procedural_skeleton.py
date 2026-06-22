import bpy
import bmesh
import math
from mathutils import Matrix, Vector

# 1. ทำความสะอาดโมเดลกระดูกและแก้วเก่า
for obj in bpy.data.objects:
    if obj.name.startswith("skel_") or obj.name.startswith("joint_") or obj.name == "Cup":
        bpy.data.objects.remove(obj, do_unlink=True)

# 2. สร้างแก้วน้ำสีแดง (เพื่อให้ตัดกับสีกระดูกชัดเจน)
CUP_LOC = Vector((0.0, 0.20, 0.05))
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.035, depth=0.10, location=CUP_LOC)
cup = bpy.context.active_object
cup.name = "Cup"
mat_cup = bpy.data.materials.new("RedCup")
mat_cup.use_nodes = True
mat_cup.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.05, 0.05, 1.0)
mat_cup.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.2
cup.data.materials.append(mat_cup)

# 3. จัดการ Rig และซ่อนมือเนื้อ
arm = bpy.data.objects.get("HandRig")
if arm:
    for hide_name in ("Hand", "Nails"):
        obj = bpy.data.objects.get(hide_name)
        if obj:
            obj.hide_render = True
            obj.hide_set(True)
            obj.hide_viewport = True

    # บังคับมือให้อยู่บนแกน X
    R = Matrix(((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)))
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = R.to_euler('XYZ')
    
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    
    # ล็อกข้อมือให้ตรงเป๊ะ
    for bn in ["root", "wrist", "palm"]:
        if bn in arm.pose.bones:
            pb = arm.pose.bones[bn]
            pb.rotation_euler = (0, 0, 0)
            for i in range(3): pb.lock_rotation[i] = True
                
    # ตั้งระยะมือให้พอดีกับแก้ว (กำรอบแกน Z พอดี)
    if "root" in arm.pose.bones:
        arm.pose.bones["root"].location = (0.05, -0.055, 0.245)
    
    # ดัดนิ้วให้กำรอบแก้วอย่างเป็นธรรมชาติ
    angles = {
        "f_index.01": -math.radians(65), "f_index.02": -math.radians(45), "f_index.03": -math.radians(35),
        "f_middle.01": -math.radians(65), "f_middle.02": -math.radians(45), "f_middle.03": -math.radians(35),
        "f_ring.01": math.radians(65), "f_ring.02": math.radians(45), "f_ring.03": math.radians(35),
        "f_pinky.01": math.radians(65), "f_pinky.02": math.radians(45), "f_pinky.03": math.radians(35),
        "thumb.01": math.radians(25), "thumb.02": -math.radians(20), "thumb.03": math.radians(10),
    }
    for bn, ang in angles.items():
        if bn in arm.pose.bones:
            arm.pose.bones[bn].rotation_euler[0] = ang
            
    bpy.ops.object.mode_set(mode="OBJECT")

# 4. สร้างรูปทรงกระดูก 3D แบบปั้นโครง (Procedural Bone Shape) ให้สวยงามสมจริง
bone_mat = bpy.data.materials.new("RealBone")
bone_mat.use_nodes = True
bone_bsdf = bone_mat.node_tree.nodes["Principled BSDF"]
bone_bsdf.inputs["Base Color"].default_value = (0.9, 0.88, 0.85, 1.0)
bone_bsdf.inputs["Roughness"].default_value = 0.35

def create_bone_mesh(name, length, radius):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    segments = 12
    # กำหนดความคอดของกระดูกตรงกลาง และป่องตรงข้อต่อ
    rings = [
        (0.0, radius * 1.5),
        (length * 0.15, radius * 0.7),
        (length * 0.50, radius * 0.45),
        (length * 0.85, radius * 0.7),
        (length, radius * 1.4)
    ]
    circle_verts = [(math.cos(2*math.pi*i/segments), math.sin(2*math.pi*i/segments)*0.85) for i in range(segments)]
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
        # สร้างกระดูกทีละท่อนและผูกเข้ากับข้อต่อ
        c = create_bone_mesh("skel_" + bone.name, L, 0.0035)
        c.parent = arm
        c.parent_type = "BONE"
        c.parent_bone = bone.name
        c.matrix_parent_inverse = Matrix.Identity(4)
        c.location = (0,0,0)
        c.rotation_euler = (0,0,0)

# 5. เพิ่มลูกแก้วข้อต่อ (Joints) บริเวณปลายนิ้ว
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

# 6. หรี่ไฟลงเล็กน้อยและอัปเดตมุมกล้อง
if bpy.data.worlds.get("World"):
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5

cam = bpy.data.objects.get("Camera")
if cam:
    cam.location = (-0.25, 0.05, 0.25)
    cam.rotation_euler = (CUP_LOC - cam.location).to_track_quat("-Z", "Y").to_euler()

bpy.context.view_layer.update()
