"""Clean FK cylindrical grasp on the skeleton hand (no IK, no Child-Of).

Follows the clinical grasp spec:
  * wrist/forearm locked straight (rotation 0, locked) -> single straight arm;
  * cup = fixed vertical Z-axis cylinder (does NOT drift forward);
  * fingers curl by FORWARD KINEMATICS on their hinge axis to wrap the cup;
  * thumb opposes the fingers.

Renders a single STILL at the grasp pose so the pivot/axis can be checked
before animating. Tweak AXIS / CURL / ROOT at the top if the local hinge
differs (the spec warns the hinge may be X or Z).
"""
from __future__ import annotations

import math
import os

import bpy

from mathutils import Matrix, Vector

STILL_OUT = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\render_output\grasp_test.png"
CUP_POS = (0.0, 0.20, 0.05)        # fixed vertical cup (Z axis)
ROOT_LOC = (0.05, -0.110, 0.158)   # hand brought to the cup, knuckles at (-0.055, 0.20, 0.05)

FINGER_BONES = [
    "f_index.01", "f_index.02", "f_index.03",
    "f_middle.01", "f_middle.02", "f_middle.03",
    "f_ring.01", "f_ring.02", "f_ring.03",
    "f_pinky.01", "f_pinky.02", "f_pinky.03",
]
THUMB_BONES = ["thumb.01", "thumb.02", "thumb.03"]
LOCK_STRAIGHT = ["root", "wrist", "palm"]  # forearm/wrist/hand kept as a straight line


def _set_axis_rot(pb, axis, angle):
    rot = [0.0, 0.0, 0.0]
    rot[axis] = angle
    pb.rotation_euler = tuple(rot)


def fk_grasp() -> dict:
    arm = bpy.data.objects["HandRig"]

    # --- clear any previous animation + cup attachment so the cup stays put ---
    if arm.animation_data:
        arm.animation_data_clear()
    cup = bpy.data.objects.get("Cup")
    if cup:
        if cup.animation_data:
            cup.animation_data_clear()
        for c in list(cup.constraints):
            cup.constraints.remove(c)
        cup.location = CUP_POS
        cup.rotation_euler = (0, 0, 0)

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
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        for i in range(3):
            pb.lock_rotation[i] = False

    # --- lock the wrist/forearm straight (single rigid line) ---
    for bn in LOCK_STRAIGHT:
        if bn in arm.pose.bones:
            pb = arm.pose.bones[bn]
            pb.rotation_euler = (0, 0, 0)
            for i in range(3):
                pb.lock_rotation[i] = True

    # --- bring the hand to the cup (translate the root only; rotations locked) ---
    arm.pose.bones["root"].location = ROOT_LOC

    # --- FK finger flexion around the cup (opposing curls) ---
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

    ALL_CURL_BONES = FINGER_BONES + THUMB_BONES
    for bn in ALL_CURL_BONES:
        if bn in arm.pose.bones:
            _set_axis_rot(arm.pose.bones[bn], 0, angles.get(bn, 0.0))

    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.evaluated_depsgraph_get().update()

    # --- position the camera to frame this new X-axis orientation ---
    cam = bpy.data.objects.get("Camera")
    if cam:
        cam.location = (-0.22, 0.20 - 0.28, 0.25)
        target = Vector((0.0, 0.20, 0.08))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()

    # --- render the grasp still ---
    scene = bpy.context.scene
    scene.frame_set(1)
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.filepath = STILL_OUT
    bpy.ops.render.render(write_still=True)
    return {"still": STILL_OUT, "finger_axis": FINGER_AXIS, "exists": os.path.exists(STILL_OUT)}


if __name__ == "__main__" or "bpy" in dir():
    print("GRASP_RESULT:", fk_grasp())
