"""Rig the KineTwin procedural hand (v2) with a clean armature + auto-weights.

The downloaded Sketchfab asset's rig turned out to be non-functional in Blender
(posing bones does not deform the mesh), so we go back to the procedural hand we
fully control. This script:

  1. rebuilds the anatomical hand scene (metres) via build_reference_hand.py,
  2. creates an armature whose bones sit *inside* the hand geometry
     (forearm/wrist/palm + 4 fingers x 3 phalanges + thumb x 2),
  3. parents the Hand mesh to the armature with automatic weights,
  4. creates 21 landmark Empties (parented to bones, MediaPipe schema) for the
     metrics-export step,
  5. VERIFIES the rig actually deforms the mesh (root translation + a finger
     curl must move vertices) before we bother animating.

Run after import_reference_hand has been used (it clears the asset scene); this
file resets and rebuilds from the procedural hand.
"""
from __future__ import annotations

import os

import bpy
from mathutils import Vector

BUILD_PATH = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\src\deploy\blender\build_reference_hand.py"
PALM_Z = 0.042


# ----------------------------------------------------------------- bone layout
# Each finger: (name, x, [seg lengths]). Thumb given separately.
FINGERS = [
    ("Index", +0.030, [0.042, 0.025, 0.023]),
    ("Middle", +0.010, [0.048, 0.027, 0.025]),
    ("Ring", -0.011, [0.044, 0.025, 0.023]),
    ("Pinky", -0.031, [0.034, 0.020, 0.019]),
]
KNUCKLE_Y = 0.055


def _bone_specs():
    """Return a list of (name, head, tail, parent) edit-bone specs (metres)."""
    specs = []
    # main chain: root(forearm) -> wrist -> palm
    specs.append(("root", (0.0, -0.30, PALM_Z), (0.0, -0.08, PALM_Z), None))
    specs.append(("wrist", (0.0, -0.08, PALM_Z), (0.0, -0.02, PALM_Z), "root"))
    specs.append(("palm", (0.0, -0.02, PALM_Z), (0.0, KNUCKLE_Y, PALM_Z), "wrist"))

    for fname, fx, segs in FINGERS:
        prev = "palm"
        y = KNUCKLE_Y
        for i, L in enumerate(segs, start=1):
            head = (fx, y, PALM_Z)
            y += L
            tail = (fx, y, PALM_Z)
            bname = f"f_{fname.lower()}.{i:02d}"
            specs.append((bname, head, tail, prev))
            prev = bname

    # thumb: 3 segments (CMC->MCP->IP->TIP) angled from the thenar side.
    thumb_dir = Vector((0.62, 1.0, -0.05)).normalized()
    t0 = Vector((0.052, -0.020, PALM_Z))
    t_segs = [0.022, 0.030, 0.028]
    prev = "palm"
    cursor = t0
    for i, L in enumerate(t_segs, start=1):
        head = tuple(cursor)
        cursor = cursor + thumb_dir * L
        tail = tuple(cursor)
        bname = f"thumb.{i:02d}"
        specs.append((bname, head, tail, prev))
        prev = bname
    return specs


# ----------------------------------------------------------------- build rig
def build_rig() -> dict:
    # 1) rebuild the procedural hand scene (metres)
    exec(open(BUILD_PATH, encoding="utf-8").read(), {"__name__": "__not_main__"})
    hand = bpy.data.objects["Hand"]

    # 2) create armature + bones
    arm_data = bpy.data.armatures.new("HandArmature_data")
    arm_obj = bpy.data.objects.new("HandRig", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)

    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    created = {}
    for name, head, tail, parent in _bone_specs():
        eb = arm_data.edit_bones.new(name)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        if parent and parent in created:
            eb.parent = created[parent]
        created[name] = eb
    # connect children for clean chains
    bpy.ops.armature.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")

    # 3) parent Hand mesh -> armature, then OVERRIDE weights with nearest-bone
    #    skinning. Automatic weights assigned the finger vertices to the root
    #    bone, so curls did nothing; nearest-bone makes each capsule/phalanx
    #    follow its own bone rigidly (clean for a segmented hand).
    bpy.ops.object.select_all(action="DESELECT")
    hand.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    _assign_nearest_bone_weights(arm_obj, hand)

    # Bones default-created as QUATERNION here; force XYZ euler so rotation_euler
    # keyframes (used for finger curls) actually apply.
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = "XYZ"
    bpy.ops.object.mode_set(mode="OBJECT")

    # 4) 21 landmark empties (MediaPipe schema), parented to bones.
    landmarks = _create_landmark_empties(arm_obj)

    # 5) VERIFY deformation: translate root, curl a finger, check vertices move.
    deform_ok = _verify_deformation(arm_obj, hand)

    return {
        "armature": arm_obj.name,
        "bones": len(arm_data.bones),
        "landmarks": len(landmarks),
        "deforms": deform_ok,
    }


def _assign_nearest_bone_weights(arm_obj, hand) -> None:
    """Replace every vertex's weights so it follows only its nearest bone.

    Rigid per-bone skinning: each mesh vertex is fully (1.0) assigned to the
    closest bone segment and removed from all other groups. Works well for the
    segmented procedural hand (forearm/palm/phalanges are distinct capsules).
    """
    mw_inv = hand.matrix_world.inverted()
    arm_mw = arm_obj.matrix_world

    segs = []  # (bone_name, head_meshlocal, tail_meshlocal)
    for b in arm_obj.data.bones:
        h = mw_inv @ (arm_mw @ b.head_local)
        t = mw_inv @ (arm_mw @ b.tail_local)
        segs.append((b.name, h, t))

    # Ensure a vertex group exists for every bone.
    existing = {vg.name: vg for vg in hand.vertex_groups}
    for name, _, _ in segs:
        if name not in existing:
            existing[name] = hand.vertex_groups.new(name=name)

    def dist_seg(p, a, b):
        ab = b - a
        L = ab.length
        if L < 1e-9:
            return (p - a).length
        tt = max(0.0, min(1.0, (p - a).dot(ab) / (L * L)))
        return (p - (a + ab * tt)).length

    for v in hand.data.vertices:
        best = None
        best_d = 1e9
        for name, a, b in segs:
            d = dist_seg(v.co, a, b)
            if d < best_d:
                best_d = d
                best = name
        # remove from every group, then assign fully to the nearest bone
        for vg in hand.vertex_groups:
            vg.remove([v.index])
        existing[best].add([v.index], 1.0, "REPLACE")


def _create_landmark_empties(arm_obj):
    """Create 21 empties following the MediaPipe Hands schema, bone-parented."""
    schema = [
        # (landmark_index, bone_name, at_tail?)
        (0, "wrist", False),
        (1, "thumb.01", False), (2, "thumb.02", False), (3, "thumb.03", False), (4, "thumb.03", True),
        (5, "f_index.01", False), (6, "f_index.02", False), (7, "f_index.03", False), (8, "f_index.03", True),
        (9, "f_middle.01", False), (10, "f_middle.02", False), (11, "f_middle.03", False), (12, "f_middle.03", True),
        (13, "f_ring.01", False), (14, "f_ring.02", False), (15, "f_ring.03", False), (16, "f_ring.03", True),
        (17, "f_pinky.01", False), (18, "f_pinky.02", False), (19, "f_pinky.03", False), (20, "f_pinky.03", True),
    ]
    empties = []
    for idx, bone_name, at_tail in schema:
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
        e = bpy.context.active_object
        e.name = f"LM_{idx:02d}"
        e.empty_display_size = 0.004
        e.parent = arm_obj
        e.parent_type = "BONE"
        e.parent_bone = bone_name
        bone = arm_obj.data.bones[bone_name]
        # bone-local +Y runs head->tail; (0,0,0)=head, (0,length,0)=tail
        e.location = (0.0, bone.length, 0.0) if at_tail else (0.0, 0.0, 0.0)
        empties.append(e)
    return empties


def _vg_centroid(obj, vg_name):
    idx = obj.vertex_groups.find(vg_name)
    if idx < 0:
        return None
    deg = bpy.context.evaluated_depsgraph_get()
    eobj = obj.evaluated_get(deg)
    me = eobj.to_mesh()
    grp = eobj.vertex_groups[idx]
    mw = obj.matrix_world
    acc = Vector((0, 0, 0))
    n = 0
    for v in me.vertices:
        try:
            w = grp.weight(v.index)
        except RuntimeError:
            w = 0.0
        if w > 0.2:
            acc += mw @ v.co
            n += 1
    eobj.to_mesh_clear()
    if n == 0:
        return None
    c = acc / n
    return Vector((round(c.x, 4), round(c.y, 4), round(c.z, 4)))


def _verify_deformation(arm_obj, hand) -> bool:
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm_obj.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()

    rest_root = _vg_centroid(hand, "root")
    rest_idx = _vg_centroid(hand, "f_index.02")

    # translate root forward in Y
    arm_obj.pose.bones["root"].location = (0.0, 0.10, 0.0)
    bpy.context.view_layer.update()
    moved_root = _vg_centroid(hand, "root")
    arm_obj.pose.bones["root"].location = (0, 0, 0)

    # curl index finger
    arm_obj.pose.bones["f_index.02"].rotation_euler = (0, 0, -1.2)
    bpy.context.view_layer.update()
    moved_idx = _vg_centroid(hand, "f_index.02")
    arm_obj.pose.bones["f_index.02"].rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()

    bpy.ops.object.mode_set(mode="OBJECT")

    root_delta = (moved_root - rest_root).length if (rest_root and moved_root) else 0
    idx_delta = (moved_idx - rest_idx).length if (rest_idx and moved_idx) else 0
    print("VERIFY rest_root", rest_root, "moved_root", moved_root, "delta", round(root_delta, 4))
    print("VERIFY rest_idx ", rest_idx, "moved_idx ", moved_idx, "delta", round(idx_delta, 4))
    return root_delta > 0.01 and idx_delta > 0.005


if __name__ == "__main__" or "bpy" in dir():
    print("RIG_RESULT:", build_rig())
