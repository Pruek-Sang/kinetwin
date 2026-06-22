"""Animate the rigged KineTwin reference hand doing Reach -> Grasp -> Lift.

Rebuilds + rigs the procedural hand (via rig_hand.py), then keyframes a clean
"normal-speed" Reach-Grasp-Lift of a cup, renders the reference video, and
exports the 21-landmark trajectory (MediaPipe schema, metres) as JSON for the
metrics pipeline.

Timeline @ 30 fps, 90 frames (3 s):
  f1      rest, hand back, fingers open
  f1-30   reach  (root translates +Y toward the cup)
  f30-45  grasp  (fingers + thumb curl around the cup)
  f45-72  lift   (root translates +Z, cup follows)
  f72-90  hold
"""
from __future__ import annotations

import json
import math
import os

import bpy
from mathutils import Vector, Matrix

RIG_PATH = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\src\deploy\blender\rig_hand.py"
RENDER_DIR = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\render_output"
TRAJ_PATH = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\src\ai\tracking\data\reference_hand_trajectory.json"

FPS = 30
FRAME_END = 90

FINGER_CURL_BONES = [
    "f_index.01", "f_index.02", "f_index.03",
    "f_middle.01", "f_middle.02", "f_middle.03",
    "f_ring.01", "f_ring.02", "f_ring.03",
    "f_pinky.01", "f_pinky.02", "f_pinky.03",
    "thumb.01", "thumb.02", "thumb.03",
]


def _add_cup(location, radius=0.035, height=0.10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=radius, depth=height,
                                        location=location)
    cup = bpy.context.active_object
    cup.name = "Cup"
    # hollow look: a slightly smaller inner cylinder boolean would be ideal, but
    # a solid matte cup reads fine at this scale.
    mat = bpy.data.materials.new("CupMat")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.92, 0.92, 0.94, 1.0)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.3
    cup.data.materials.append(mat)
    for poly in cup.data.polygons:
        poly.use_smooth = True
    return cup


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


def animate() -> dict:
    # 1) rebuild + rig
    exec(open(RIG_PATH, encoding="utf-8").read(), {"__name__": "__not_main__"})
    arm = bpy.data.objects["HandRig"]
    hand = bpy.data.objects["Hand"]

    # hide the ugly skin mesh + nails (skeleton replaces them)
    for hide_name in ("Hand", "Nails"):
        obj = bpy.data.objects.get(hide_name)
        if obj:
            obj.hide_render = True
            obj.hide_set(True)

    _build_skeleton(arm)

    if arm.animation_data:
        arm.animation_data_clear()

    # Rotate the armature object so the arm points along the world X-axis and palm is vertical
    R = Matrix((
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0)
    ))
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = R.to_euler('XYZ')

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
    bpy.ops.object.mode_set(mode="OBJECT")

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.render.fps = FPS

    # 2) cup
    cup_rest = Vector((0.0, 0.20, 0.05))
    cup = _add_cup(cup_rest)

    # 3) keyframes -- reach/lift via root location
    root = arm.pose.bones["root"]
    root_keyframes = {
        1: (0.05, -0.205, 0.158),
        30: (0.05, -0.110, 0.158),    # reach forward in world X (local Y)
        45: (0.05, -0.110, 0.158),    # grasp (hold position)
        72: (0.13, -0.110, 0.158),    # lift up in world Z (local X)
        90: (0.13, -0.110, 0.158),    # hold
    }
    for f, loc in root_keyframes.items():
        scene.frame_set(f)
        root.location = loc
        root.keyframe_insert(data_path="location", frame=f)

    # 4) keyframes -- grasp via finger curl (opposing curls)
    # Optimized collision-free angles:
    # Index: MCP=51.17, PIP=34.86, DIP=19.97
    # Middle: MCP=49.39, PIP=34.86, DIP=19.98
    # Ring: MCP=50.65, PIP=34.86, DIP=19.98
    # Pinky: MCP=52.27, PIP=34.88, DIP=19.97
    # Thumb: 01=4.98, 02=-3.83, 03=1.54
    import math
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
            scene.frame_set(f)
            pb.rotation_euler = (ang, 0, 0)
            pb.keyframe_insert(data_path="rotation_euler", frame=f)

    # 5) cup follows the lift
    cup_loc_keyframes = {1: cup_rest, 30: cup_rest, 45: cup_rest,
                         72: Vector((0.0, 0.20, 0.13)), 90: Vector((0.0, 0.20, 0.13))}
    for f, loc in cup_loc_keyframes.items():
        scene.frame_set(f)
        cup.location = loc
        cup.keyframe_insert(data_path="location", frame=f)

    scene.frame_set(1)
    bpy.context.view_layer.update()

    # 6) camera framed on hand + cup
    cam = bpy.data.objects.get("Camera")
    if cam:
        cam.location = (-0.22, 0.20 - 0.28, 0.25)
        target = Vector((0.0, 0.20, 0.08))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 50.0
        scene.camera = cam

    # 7) key stills for quick visual review
    os.makedirs(RENDER_DIR, exist_ok=True)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"
    for f in (1, 30, 45, 72):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        scene.render.filepath = os.path.join(RENDER_DIR, f"ref_frame_{f:02d}.png")
        bpy.ops.render.render(write_still=True)

    # 8) export 21-landmark trajectory (metres)
    lm_names = [f"LM_{i:02d}" for i in range(21)]
    frames_out = []
    for f in range(1, FRAME_END + 1):
        scene.frame_set(f)
        bpy.context.evaluated_depsgraph_get().update()
        landmarks = [[round(v, 6) for v in bpy.data.objects[n].matrix_world.translation]
                     for n in lm_names]
        frames_out.append({"frame": f, "landmarks": landmarks})

    os.makedirs(os.path.dirname(TRAJ_PATH), exist_ok=True)
    with open(TRAJ_PATH, "w", encoding="utf-8") as fh:
        json.dump({"fps": FPS, "n_frames": FRAME_END, "schema": "mediapipe_hands_21",
                   "units": "meters", "label": "reference", "frames": frames_out}, fh)

    # 9) render the reference VIDEO as a PNG sequence, then encode to mp4 with
    #    OpenCV (this Blender build has no FFMPEG output container; opencv is
    #    already a project dependency via the tracking layer).
    seq_dir = os.path.join(RENDER_DIR, "reference_seq")
    os.makedirs(seq_dir, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.filepath = os.path.join(seq_dir, "frame_####")
    bpy.ops.render.render(animation=True)
    video_path = _encode_sequence(seq_dir, os.path.join(RENDER_DIR, "reference_hand.mp4"),
                                  fps=FPS, size=(960, 540))

    return {
        "video": video_path,
        "sequence_dir": seq_dir,
        "trajectory": TRAJ_PATH,
        "frames": FRAME_END,
        "fps": FPS,
    }


def _encode_sequence(seq_dir, out_path, fps=30, size=(960, 540)):
    """PNG sequence -> mp4 via OpenCV (no ffmpeg binary required)."""
    try:
        import cv2  # lazy
    except ImportError:
        return None
    files = sorted(f for f in os.listdir(seq_dir) if f.endswith(".png"))
    if not files:
        return None
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(out_path, fourcc, fps, size)
    for f in files:
        img = cv2.imread(os.path.join(seq_dir, f))
        if img is not None:
            vw.write(img)
    vw.release()
    return out_path


if __name__ == "__main__" or "bpy" in dir():
    print("ANIMATE_RESULT:", animate())
