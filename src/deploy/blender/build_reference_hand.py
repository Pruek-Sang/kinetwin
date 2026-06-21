"""KineTwin Blender reference hand -- build stage 1 (scene + clean hand mesh).

Run inside Blender (interactive addon or ``blender --python``). It clears the
default scene and builds a clean stylized right hand posed mid-reach, on a
table, with camera + lighting + materials, ready for a look-check screenshot.

Later stages (rigging, reach-grasp-lift animation, cup, 21-landmark export)
are added in separate scripts so each step can be reviewed.

Coordinate convention (metres):
  +Y = reach direction (forward, toward the cup)
  +Z = up (lift)
  +X = thumb side (right hand: thumb points +X)
"""
from __future__ import annotations

import math
import sys

import bpy
from mathutils import Vector

# --------------------------------------------------------------------- helpers
def _reset_scene() -> None:
    """Remove every object/mesh/material from the current scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                       bpy.data.cameras, bpy.data.objects):
        for item in list(collection):
            collection.remove(item)


def _make_material(name: str, base_color, roughness: float = 0.5,
                   metallic: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def _add_cylinder(name: str, location, length: float, radius: float,
                  rotation_euler=(0, 0, 0), vertices: int = 24) -> bpy.types.Object:
    """Cylinder aligned along its local Z, then rotated; placed in world space."""
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=length,
        location=location, rotation=rotation_euler,
    )
    obj = bpy.context.active_object
    obj.name = name
    return obj


def _add_rounded_box(name: str, location, size, bevel_width: float = 0.01,
                     bevel_segments: int = 4) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size  # full dimensions (not half)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bev = obj.modifiers.new("Bevel", "BEVEL")
    bev.width = bevel_width
    bev.segments = bevel_segments
    bev.limit_method = "ANGLE"
    return obj


def _shade_smooth(obj: bpy.types.Object, subsurf_levels: int = 2) -> None:
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if subsurf_levels > 0:
        sub = obj.modifiers.new("Subsurf", "SUBSURF")
        sub.levels = subsurf_levels
        sub.render_levels = subsurf_levels


def _join_into(target_name: str, parts) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = target_name
    return joined


# ----------------------------------------------------------------- scene build
def build_stage1() -> dict:
    _reset_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"

    skin = _make_material("Skin", (0.90, 0.74, 0.62), roughness=0.45)
    table_mat = _make_material("Table", (0.62, 0.63, 0.66), roughness=0.85)

    # ---- table ----
    bpy.ops.mesh.primitive_plane_add(size=1.6, location=(0, 0.05, 0))
    table = bpy.context.active_object
    table.name = "Table"
    table.data.materials.append(table_mat)

    # ---- hand parts (right hand, palm down, reaching +Y) ----
    palm = _add_rounded_box("Palm", location=(0.0, -0.02, 0.040),
                            size=(0.100, 0.130, 0.026),
                            bevel_width=0.012, bevel_segments=5)

    # Forearm: cylinder along Y (rotate Z-cylinder 90deg about X).
    forearm = _add_cylinder("Forearm", location=(0.0, -0.195, 0.040),
                            length=0.230, radius=0.036,
                            rotation_euler=(math.radians(90), 0, 0))

    # Fingers: cylinders along +Y. base at knuckles Y=0.04 (palm front edge).
    finger_specs = [
        # name,            x,      length, radius
        ("FingerIndex",  +0.026, 0.088, 0.0095),
        ("FingerMiddle", +0.009, 0.100, 0.0100),
        ("FingerRing",   -0.010, 0.090, 0.0095),
        ("FingerPinky",  -0.029, 0.070, 0.0085),
    ]
    fingers = []
    for fname, fx, flen, frad in finger_specs:
        fy = 0.040 + flen / 2.0
        f = _add_cylinder(fname, location=(fx, fy, 0.040), length=flen, radius=frad,
                          rotation_euler=(math.radians(90), 0, 0))
        fingers.append(f)

    # Thumb: angled from the +X side of the palm toward forward/+Y.
    thumb = _add_cylinder("Thumb", location=(0.058, 0.018, 0.040),
                          length=0.064, radius=0.0095,
                          rotation_euler=(math.radians(90), math.radians(15),
                                          math.radians(-55)))

    hand = _join_into("Hand", [forearm, palm, *fingers, thumb])
    hand.data.materials.append(skin)
    _shade_smooth(hand, subsurf_levels=2)

    # ---- lighting (3-point) ----
    bpy.ops.object.light_add(type="AREA", location=(0.35, -0.30, 0.65))
    key = bpy.context.active_object
    key.name = "Key"
    key.data.energy = 180.0
    key.data.size = 0.6
    key.rotation_euler = (math.radians(55), math.radians(10), math.radians(35))

    bpy.ops.object.light_add(type="AREA", location=(-0.45, -0.20, 0.45))
    fill = bpy.context.active_object
    fill.name = "Fill"
    fill.data.energy = 70.0
    fill.data.size = 0.8
    fill.rotation_euler = (math.radians(65), math.radians(-15), math.radians(-40))

    bpy.ops.object.light_add(type="SUN", location=(0.0, 0.4, 0.9))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 1.8
    sun.rotation_euler = (math.radians(35), math.radians(20), 0)

    # ---- world ----
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.62, 0.64, 0.68, 1.0)
    bg.inputs["Strength"].default_value = 1.0

    # ---- camera ----
    bpy.ops.object.camera_add(location=(0.42, -0.34, 0.30))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.data.lens = 50.0
    # Aim camera at the hand centre.
    direction = Vector((0.0, 0.04, 0.055)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    # Render settings (Eevee, fast preview).
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100

    bpy.ops.object.select_all(action="DESELECT")
    hand.select_set(True)
    bpy.context.view_layer.objects.active = hand

    return {"hand": hand.name, "camera": cam.name, "parts": len(hand.data.vertices)}


if __name__ == "__main__" or "bpy" in sys.modules:
    _result = build_stage1()
    print("BUILD_STAGE1_RESULT:", _result)
