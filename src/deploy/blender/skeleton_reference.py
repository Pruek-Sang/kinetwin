"""KineTwin reference as a clean KINEMATIC SKELETON (no skin mesh).

Why: the sculpted mesh looked bad and the asset mesh collapsed under the rig.
A skeleton side-steps all skinning -- each bone is a thin cylinder rigidly
parented to its armature bone (no vertex weights => cannot collapse), and a
sphere sits at every MediaPipe landmark. The result reads as a clean
anatomical / "digital twin" hand and follows the Reach-Grasp-Lift animation
perfectly. This also visualises the exact 21 landmarks the metrics analyse.

Pipeline: rebuild the procedural rig (rig_hand.py) -> apply the reach-grasp-lift
keyframes -> build bone cylinders + landmark spheres -> hide the skin mesh ->
save scene for background rendering.
"""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Matrix, Vector

RIG_PATH = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\src\deploy\blender\rig_hand.py"
BLEND_OUT = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\render_output\skeleton_scene.blend"
FPS = 30
FEND = 90

FINGER_CURL_BONES = [
    "f_index.01", "f_index.02", "f_index.03",
    "f_middle.01", "f_middle.02", "f_middle.03",
    "f_ring.01", "f_ring.02", "f_ring.03",
    "f_pinky.01", "f_pinky.02", "f_pinky.03",
    "thumb.01", "thumb.02", "thumb.03",
]
# MediaPipe HAND_CONNECTIONS (pairs of landmark indices)
CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


def _material(name, color, emission=0.0, roughness=0.4):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def _apply_animation(arm):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = FEND
    scene.render.fps = FPS
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)

    root = arm.pose.bones["root"]
    # Animates a straight reach along world X and a vertical lift along world Z
    root_keys = {
        1: (0.05, -0.205, 0.158),
        30: (0.05, -0.110, 0.158),
        45: (0.05, -0.110, 0.158),
        72: (0.13, -0.110, 0.158),
        90: (0.13, -0.110, 0.158)
    }
    for f, loc in root_keys.items():
        scene.frame_set(f); root.location = loc
        root.keyframe_insert(data_path="location", frame=f)

    # Optimized collision-free angles:
    # Index: MCP=51.17, PIP=34.86, DIP=19.97
    # Middle: MCP=49.39, PIP=34.86, DIP=19.98
    # Ring: MCP=50.65, PIP=34.86, DIP=19.98
    # Pinky: MCP=52.27, PIP=34.88, DIP=19.97
    # Thumb: 01=4.98, 02=-3.83, 03=1.54
    angles = {
        "f_index.01": -math.radians(51.17),
        "f_index.02": -math.radians(34.86),
        "f_index.03": -math.radians(19.97),
        "f_middle.01": -math.radians(49.39),
        "f_middle.02": -math.radians(34.86),
        "f_middle.03": -math.radians(19.98),
        "f_ring.01": math.radians(50.65),
        "f_ring.02": math.radians(34.86),
        "f_ring.03": math.radians(19.98),
        "f_pinky.01": math.radians(52.27),
        "f_pinky.02": math.radians(34.88),
        "f_pinky.03": math.radians(19.97),
        "thumb.01": math.radians(4.98),
        "thumb.02": -math.radians(3.83),
        "thumb.03": math.radians(1.54),
    }

    for bname in FINGER_CURL_BONES:
        pb = arm.pose.bones[bname]
        curl_angle = angles.get(bname, 0.0)

        for f, ang in {1: 0.0, 30: 0.0, 45: curl_angle, 90: curl_angle}.items():
            scene.frame_set(f); pb.rotation_euler = (ang, 0, 0)
            pb.keyframe_insert(data_path="rotation_euler", frame=f)

    bpy.ops.object.mode_set(mode="OBJECT")
    scene.frame_set(1)
    bpy.context.view_layer.update()


def _build_skeleton(arm):
    bone_mat = _material("SkelBone", (0.90, 0.92, 0.95), emission=0.25)
    joint_mat = _material("SkelJoint", (0.20, 0.85, 0.95), emission=1.6, roughness=0.3)

    # bone cylinders (rigid, bone-parented -> follow pose exactly)
    for bone in arm.data.bones:
        L = bone.length
        if L < 1e-4:
            continue
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.001, depth=L, location=(0, 0, 0))
        c = bpy.context.active_object
        c.name = "skel_" + bone.name
        c.data.materials.append(bone_mat)
        for p in c.data.polygons:
            p.use_smooth = True
        c.parent = arm
        c.parent_type = "BONE"
        c.parent_bone = bone.name
        c.matrix_parent_inverse = Matrix.Identity(4)
        c.location = (0.0, L / 2.0, 0.0)
        c.rotation_euler = (math.radians(90), 0, 0)

    # landmark spheres at the 21 LM_* empties (already bone-parented in rig_hand)
    for i in range(21):
        ename = f"LM_{i:02d}"
        e = bpy.data.objects.get(ename)
        if not e:
            continue
        bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=8, radius=0.002, location=(0, 0, 0))
        s = bpy.context.active_object
        s.name = "joint_" + ename
        s.data.materials.append(joint_mat)
        for p in s.data.polygons:
            p.use_smooth = True
        s.parent = arm
        s.parent_type = "BONE"
        s.parent_bone = e.parent_bone
        s.matrix_parent_inverse = Matrix.Identity(4)
        s.location = e.location.copy()
        s.rotation_euler = (0, 0, 0)


def build_skeleton_reference() -> dict:
    exec(open(RIG_PATH, encoding="utf-8").read(), {"__name__": "__not_main__"})
    arm = bpy.data.objects["HandRig"]

    if arm.animation_data:
        arm.animation_data_clear()

    # hide the ugly skin mesh + nails (skeleton replaces them)
    for hide_name in ("Hand", "Nails"):
        obj = bpy.data.objects.get(hide_name)
        if obj:
            obj.hide_render = True
            obj.hide_set(True)

    # Rotate the armature object so the arm points along the world X-axis and palm is vertical
    R = Matrix((
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0)
    ))
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = R.to_euler('XYZ')

    _apply_animation(arm)
    _build_skeleton(arm)

    # cup rests on the table; once the fingers wrap (f~45) it is grasped and
    # follows the hand up via a Child-Of constraint to the palm bone.
    cup_rest = Vector((0.0, 0.20, 0.05))
    if "Cup" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cup"], do_unlink=True)
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=0.035, depth=0.10, location=tuple(cup_rest))
    cup = bpy.context.active_object
    cup.name = "Cup"
    cm = _material("Cup", (0.93, 0.93, 0.95), roughness=0.3)
    cup.data.materials.append(cm)
    for p in cup.data.polygons:
        p.use_smooth = True
    scene = bpy.context.scene
    # Child-Of to the palm: influence 0 until grasp, 1 after -> cup rises with hand
    co = cup.constraints.new("CHILD_OF")
    co.target = arm
    co.subtarget = "palm"
    GRASP_F = 45
    scene.frame_set(GRASP_F)
    bpy.context.view_layer.update()
    palm_world = arm.matrix_world @ arm.pose.bones["palm"].matrix
    co.inverse_matrix = palm_world.inverted() @ cup.matrix_world
    co.influence = 0.0
    co.keyframe_insert(data_path="influence", frame=1)
    co.keyframe_insert(data_path="influence", frame=GRASP_F - 5)
    co.influence = 1.0
    co.keyframe_insert(data_path="influence", frame=GRASP_F)

    if "Table" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Table"], do_unlink=True)
    bpy.ops.mesh.primitive_plane_add(size=1.6, location=(0.0, 0.10, 0.0))
    t = bpy.context.active_object
    t.name = "Table"
    tm = _material("Table", (0.12, 0.13, 0.15), roughness=0.9)
    t.data.materials.append(tm)

    # dark world + camera on the hand
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.04, 0.05, 0.07, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

    cam = bpy.data.objects["Camera"]
    cam.data.clip_start = 0.01
    cam.data.clip_end = 100.0
    # Frame the action centered on the horizontal X-axis layout
    cam.location = (-0.22, 0.20 - 0.28, 0.25)
    target = Vector((0.0, 0.20, 0.08))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50.0
    scene.camera = cam

    # lights
    for nm in ("Key", "Fill", "Sun"):
        if nm in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
    for nm, en, rot in [("Key", 40, (math.radians(55), 0, math.radians(30))),
                        ("Fill", 18, (math.radians(60), 0, math.radians(-150))),
                        ("Rim", 25, (math.radians(120), 0, math.radians(180)))]:
        bpy.ops.object.light_add(type="AREA", location=(0, 0, 0.4))
        l = bpy.context.active_object
        l.name = nm
        l.data.energy = en
        l.data.size = 0.6
        l.rotation_euler = rot

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.frame_set(1)
    bpy.context.view_layer.update()

    os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    return {"blend": BLEND_OUT, "bones": len(arm.data.bones)}


if __name__ == "__main__" or "bpy" in dir():
    print("SKELETON_RESULT:", build_skeleton_reference())
