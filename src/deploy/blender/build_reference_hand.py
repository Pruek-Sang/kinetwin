"""KineTwin Blender reference hand -- anatomical build (v2).

Rebuilds the hand to look like a science-classroom *anatomy model*: volumetric
palm with thenar/hypothenar mounds, segmented fingers (3 phalanges + joints =
visible knuckle/PIP/DIP definition), a tapered forearm with a distinct wrist,
fingernails, and a matte resin material. Built from spheres + capsules so the
3D volume reads clearly (the v1 bevelled-box palm looked flat).

Run inside Blender; clears the scene first. Later scripts add the armature +
reach-grasp-lift animation + the cup.
"""
from __future__ import annotations

import math
import sys

import bpy
from mathutils import Vector

# --------------------------------------------------------------------- helpers
def _reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.objects):
        for item in list(coll):
            coll.remove(item)


def _make_material(name, base_color, roughness=0.55, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def add_sphere(name, co, radius, segs=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=max(8, segs // 2),
                                         radius=radius, location=tuple(co))
    obj = bpy.context.active_object
    obj.name = name
    return obj


def add_capsule(name, p1, p2, radius, verts=18):
    """Cylinder + two end spheres between points p1 and p2."""
    p1 = Vector(p1)
    p2 = Vector(p2)
    axis = p2 - p1
    length = axis.length
    if length < 1e-6:
        return [add_sphere(name + "_s", p1, radius)]
    mid = (p1 + p2) / 2.0
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=length, location=tuple(mid))
    cyl = bpy.context.active_object
    cyl.name = name + "_cyl"
    z = Vector((0.0, 0.0, 1.0))
    cyl.rotation_mode = "QUATERNION"
    cyl.rotation_quaternion = z.rotation_difference(axis.normalized())
    return [cyl, add_sphere(name + "_a", p1, radius), add_sphere(name + "_b", p2, radius)]


def add_finger(prefix, start, direction, lengths, radii, joint_r):
    """Segmented finger: capsules + joint spheres. Returns (objs, tip_pos)."""
    objs = []
    cursor = Vector(start)
    d = Vector(direction).normalized()
    for i, (length, radius) in enumerate(zip(lengths, radii)):
        end = cursor + d * length
        objs += add_capsule(f"{prefix}_p{i}", cursor, end, radius)
        cursor = end
        if i < len(lengths) - 1:
            objs.append(add_sphere(f"{prefix}_j{i}", cursor, joint_r))
    return objs, cursor


def add_nail(name, tip, direction, up):
    """Flattened ellipsoid on the back of a fingertip."""
    tip = Vector(tip)
    d = Vector(direction).normalized()
    u = Vector(up).normalized()
    centre = tip + d * 0.001 + u * 0.0055
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8,
                                         radius=0.0065, location=tuple(centre))
    o = bpy.context.active_object
    o.name = name
    o.scale = (0.9, 0.6, 0.35)
    # orient nail: long axis across finger (perp to d, in the hand plane)
    return o


def _join_into(target_name, parts):
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = target_name
    return obj


def _shade_smooth(obj, subsurf_levels=1):
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if subsurf_levels > 0:
        sub = obj.modifiers.new("Subsurf", "SUBSURF")
        sub.levels = subsurf_levels
        sub.render_levels = subsurf_levels + 1


# ----------------------------------------------------------------- scene build
def build_anatomical_hand() -> dict:
    _reset_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"

    resin = _make_material("AnatomyResin", (0.90, 0.74, 0.60), roughness=0.62)
    nail_mat = _make_material("Nail", (0.94, 0.88, 0.80), roughness=0.35)
    table_mat = _make_material("Table", (0.62, 0.63, 0.66), roughness=0.85)

    parts = []
    PALM_Z = 0.042          # palm centre height
    BACK_Z = 0.060          # back-of-hand (knuckle) height
    HAND_Y0 = -0.060        # palm back edge (wrist side)

    # ---- table ----
    bpy.ops.mesh.primitive_plane_add(size=1.6, location=(0, 0.05, 0))
    table = bpy.context.active_object
    table.name = "Table"
    table.data.materials.append(table_mat)

    # ---- forearm (tapered cone) + wrist band ----
    bpy.ops.mesh.primitive_cone_add(vertices=28, radius1=0.041, radius2=0.030,
                                    depth=0.240, location=(0.0, -0.205, PALM_Z),
                                    rotation=(math.radians(90), 0, 0))
    forearm = bpy.context.active_object
    forearm.name = "Forearm"
    parts.append(forearm)

    parts.append(add_sphere("Wrist", (0.0, -0.060, PALM_Z), 0.037, segs=24))

    # ---- palm: thick rounded box ----
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, -0.005, PALM_Z))
    palm = bpy.context.active_object
    palm.name = "Palm"
    palm.scale = (0.104, 0.122, 0.040)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bev = palm.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.016
    bev.segments = 6
    bev.limit_method = "ANGLE"
    parts.append(palm)

    # ---- palm mounds (thenar under thumb, hypothenar under pinky) ----
    parts.append(add_sphere("Thenar", (0.046, -0.030, PALM_Z - 0.002), 0.031, segs=22))
    parts.append(add_sphere("Hypothenar", (-0.044, -0.010, PALM_Z - 0.002), 0.027, segs=22))
    parts.append(add_sphere("PalmPad", (0.0, -0.005, PALM_Z - 0.020), 0.030, segs=20))

    # ---- knuckle (MCP) bumps on the back of the hand ----
    knuckle_xs = [+0.030, +0.010, -0.011, -0.031]
    for i, x in enumerate(knuckle_xs):
        parts.append(add_sphere(f"MCP_{i}", (x, 0.050, BACK_Z), 0.0135, segs=18))

    # ---- fingers (segmented: 3 phalanges + 2 joints), pointing +Y ----
    finger_defs = [
        # name,        x,      lengths,                radii,                  joint_r
        ("Index",  +0.030, [0.042, 0.025, 0.023], [0.0105, 0.0095, 0.0085], 0.0125),
        ("Middle", +0.010, [0.048, 0.027, 0.025], [0.0110, 0.0100, 0.0090], 0.0130),
        ("Ring",   -0.011, [0.044, 0.025, 0.023], [0.0105, 0.0095, 0.0085], 0.0125),
        ("Pinky",  -0.031, [0.034, 0.020, 0.019], [0.0095, 0.0085, 0.0080], 0.0115),
    ]
    nails = []
    up = Vector((0.0, 0.0, 1.0))
    for fname, fx, lengths, radii, jr in finger_defs:
        start = (fx, 0.055, PALM_Z)
        fobjs, tip = add_finger(fname, start, (0.0, 1.0, 0.0), lengths, radii, jr)
        parts.extend(fobjs)
        n = add_nail(fname + "_Nail", tip, (0.0, 1.0, 0.0), up)
        nails.append(n)

    # ---- thumb (2 phalanges), angled from the thenar mound ----
    thumb_start = (0.052, -0.020, PALM_Z)
    thumb_dir = Vector((0.62, 1.0, -0.05)).normalized()
    tobjs, ttip = add_finger("Thumb", thumb_start, thumb_dir,
                             [0.036, 0.030], [0.0115, 0.0100], 0.0135)
    parts.extend(tobjs)
    nails.append(add_nail("Thumb_Nail", ttip, thumb_dir, up))

    # ---- join the hand body, then attach nails as a separate joined piece ----
    hand = _join_into("Hand", parts)
    hand.data.materials.append(resin)
    _shade_smooth(hand, subsurf_levels=1)

    nail_obj = _join_into("Nails", nails)
    nail_obj.data.materials.append(nail_mat)
    _shade_smooth(nail_obj, subsurf_levels=1)
    nail_obj.parent = hand

    # ---- lighting (3-point) ----
    bpy.ops.object.light_add(type="AREA", location=(0.36, -0.30, 0.62))
    key = bpy.context.active_object
    key.name = "Key"
    key.data.energy = 200.0
    key.data.size = 0.6
    key.rotation_euler = (math.radians(52), math.radians(12), math.radians(35))

    bpy.ops.object.light_add(type="AREA", location=(-0.46, -0.18, 0.42))
    fill = bpy.context.active_object
    fill.name = "Fill"
    fill.data.energy = 80.0
    fill.data.size = 0.8
    fill.rotation_euler = (math.radians(62), math.radians(-12), math.radians(-40))

    bpy.ops.object.light_add(type="SUN", location=(0.0, 0.4, 0.9))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 1.6
    sun.rotation_euler = (math.radians(35), math.radians(20), 0)

    # ---- world ----
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.60, 0.63, 0.68, 1.0)
    bg.inputs["Strength"].default_value = 1.0

    # ---- camera (3/4 view to show volume) ----
    bpy.ops.object.camera_add(location=(0.34, -0.30, 0.26))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.data.lens = 50.0
    direction = Vector((0.0, 0.035, 0.055)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100

    bpy.ops.object.select_all(action="DESELECT")
    hand.select_set(True)
    bpy.context.view_layer.objects.active = hand

    return {"hand": hand.name, "verts": len(hand.data.vertices)}


if __name__ == "__main__" or "bpy" in sys.modules:
    _result = build_anatomical_hand()
    print("BUILD_ANATOMICAL_RESULT:", _result)
