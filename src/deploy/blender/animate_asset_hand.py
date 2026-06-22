"""Animate the re-rigged asset #4 (right arm) doing Reach -> Grasp -> Lift.

Operates on the current scene (asset imported + rerig_asset.py run + a posed
right arm + cup/table/camera/suns). Keyframes the right-arm bones for a
reach then a lift, curls the fingers for the grasp, and makes the cup follow
the lift. Saves the scene to a .blend for background rendering.
"""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Vector

BLEND_OUT = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\render_output\asset_scene.blend"
FPS = 30
FEND = 90

FINGER_BONES = [b.name for b in bpy.data.objects["AssetArmature"].data.bones
                if ".R_" in b.name and ("f_index" in b.name or "f_middle" in b.name
                or "f_ring" in b.name or "f_pinky" in b.name or "thumb" in b.name)
                and "_end" not in b.name]


def animate() -> dict:
    arm = bpy.data.objects["AssetArmature"]
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = FEND
    scene.render.fps = FPS

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)

    ua = arm.pose.bones["upper_arm.R_03"]
    fa = arm.pose.bones["forearm.R_04"]

    # right-arm pose timeline (rotation_euler, radians)
    arm_keys = {
        1:  ((0, 0, math.radians(-60)),  (0, 0, math.radians(30))),    # hand back/up
        30: ((0, 0, math.radians(-110)), (0, 0, math.radians(70))),    # reach to cup
        45: ((0, 0, math.radians(-110)), (0, 0, math.radians(70))),    # hold (grasp)
        72: ((math.radians(35), 0, math.radians(-100)), (0, 0, math.radians(55))),  # lift
        90: ((math.radians(35), 0, math.radians(-100)), (0, 0, math.radians(55))),  # hold
    }
    for f, (uar, far) in arm_keys.items():
        scene.frame_set(f)
        ua.rotation_euler = uar
        fa.rotation_euler = far
        ua.keyframe_insert(data_path="rotation_euler", frame=f)
        fa.keyframe_insert(data_path="rotation_euler", frame=f)

    # finger curl (grasp) -- minimal on this asset but included
    for bname in FINGER_BONES:
        pb = arm.pose.bones[bname]
        for f, ang in {1: 0.0, 30: 0.0, 45: math.radians(120), 90: math.radians(120)}.items():
            scene.frame_set(f)
            pb.rotation_euler = (ang, 0, 0)
            pb.keyframe_insert(data_path="rotation_euler", frame=f)

    bpy.ops.object.mode_set(mode="OBJECT")

    # cup follows the lift (stays on table until grasp, rises after)
    cup = bpy.data.objects.get("Cup")
    if cup:
        base = Vector(cup.location)
        lifted = Vector((base.x, base.y, base.z + 360))
        for f, loc in {1: base, 30: base, 45: base, 72: lifted, 90: lifted}.items():
            scene.frame_set(f)
            cup.location = loc
            cup.keyframe_insert(data_path="location", frame=f)

    scene.frame_set(1)
    bpy.context.view_layer.update()

    os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    return {"blend": BLEND_OUT, "frames": FEND, "fps": FPS, "finger_bones": len(FINGER_BONES)}


if __name__ == "__main__" or "bpy" in dir():
    print("ANIMATE_ASSET_RESULT:", animate())
