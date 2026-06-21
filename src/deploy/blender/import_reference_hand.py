"""Import the downloaded rigged hand (.glb) into the KineTwin reference scene.

Clears the scene, imports the Sketchfab GLB, inspects its structure (meshes,
armature + bone names, materials, animations, world bounding box), then drops
it onto a table with 3-point lighting and an auto-framed camera, and renders a
preview PNG so a human can review the look/orientation before rigging/animation.

Run inside Blender:
    exec(open(<this path>, encoding="utf-8").read())
"""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Vector

GLB_PATH = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\src\deploy\blender\models\first_person_hands_rigged.glb"
RENDER_DIR = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\render_output"


def _reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.armatures, bpy.data.objects,
                 bpy.data.actions, bpy.data.images):
        for item in list(coll):
            try:
                coll.remove(item)
            except RuntimeError:
                pass


def _world_bbox(mesh_objs):
    mins = [1e12, 1e12, 1e12]
    maxs = [-1e12, -1e12, -1e12]
    for obj in mesh_objs:
        for corner in obj.bound_box:
            wc = obj.matrix_world @ Vector(corner)
            for i in range(3):
                if wc[i] < mins[i]:
                    mins[i] = wc[i]
                if wc[i] > maxs[i]:
                    maxs[i] = wc[i]
    return Vector(mins), Vector(maxs)


def _make_material(name, base_color, roughness=0.6):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def import_and_preview() -> dict:
    _reset_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"

    bpy.ops.import_scene.gltf(filepath=GLB_PATH)

    mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
    arm_objs = [o for o in bpy.data.objects if o.type == "ARMATURE"]

    mins, maxs = _world_bbox(mesh_objs)
    center = (mins + maxs) / 2.0
    dim = maxs - mins
    max_dim = max(dim) if max(dim) > 1e-6 else 0.2
    # NOTE: the asset is authored in arbitrary units (max_dim ~92). For the
    # visual reference / animation the *unit* is irrelevant -- only relative
    # sizes matter -- so we frame everything in the asset's native unit. The
    # real-world metre conversion (for the metrics pipeline) is applied later
    # at landmark-export time via scene.unit_settings.scale_length.

    bones = []
    for a in arm_objs:
        bones.extend(b.name for b in a.data.bones)

    print("IMPORT_MESHES:", [o.name for o in mesh_objs])
    print("IMPORT_ARMATURES:", [o.name for o in arm_objs])
    print("IMPORT_BONES_COUNT:", len(bones), "| SAMPLE:", bones[:25])
    print("IMPORT_MATERIALS:", [m.name for m in bpy.data.materials])
    print("IMPORT_ACTIONS:", [a.name for a in bpy.data.actions])
    print("BBOX_MIN:", tuple(round(v, 4) for v in mins))
    print("BBOX_MAX:", tuple(round(v, 4) for v in maxs))
    print("CENTER:", tuple(round(v, 4) for v in center))
    print("DIM:", tuple(round(v, 4) for v in dim), "max_dim:", round(max_dim, 4))

    # ---- table ----
    table_mat = _make_material("Table", (0.62, 0.63, 0.66), roughness=0.85)
    table_z = mins.z
    bpy.ops.mesh.primitive_plane_add(size=max(max_dim * 6.0, 1.2),
                                     location=(center.x, center.y, table_z))
    table = bpy.context.active_object
    table.name = "Table"
    table.data.materials.append(table_mat)

    # ---- lighting (3-point, scaled to the hand) ----
    d = max_dim
    bpy.ops.object.light_add(type="AREA", location=(center.x + d * 1.6,
                                  center.y - d * 1.4, center.z + d * 2.4))
    key = bpy.context.active_object
    key.name = "Key"
    key.data.energy = max_dim * 600.0
    key.data.size = d * 2.0
    key.rotation_euler = (math.radians(55), math.radians(10), math.radians(35))

    bpy.ops.object.light_add(type="AREA", location=(center.x - d * 2.0,
                                  center.y - d * 1.0, center.z + d * 1.6))
    fill = bpy.context.active_object
    fill.name = "Fill"
    fill.data.energy = max_dim * 240.0
    fill.data.size = d * 3.0
    fill.rotation_euler = (math.radians(62), math.radians(-12), math.radians(-40))

    bpy.ops.object.light_add(type="SUN", location=(center.x, center.y + d, center.z + d * 3))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 1.8
    sun.rotation_euler = (math.radians(35), math.radians(20), 0)

    # ---- world ----
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.60, 0.63, 0.68, 1.0)
    bg.inputs["Strength"].default_value = 1.0

    # ---- camera (3/4, auto-framed on the hand bbox) ----
    cam_offset = Vector((d * 1.6, -d * 2.0, d * 1.1))
    bpy.ops.object.camera_add(location=tuple(center + cam_offset))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.data.lens = 50.0
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    # ---- render preview ----
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(RENDER_DIR, exist_ok=True)
    scene.render.filepath = os.path.join(RENDER_DIR, "hand_preview_03.png")
    bpy.ops.render.render(write_still=True)

    return {
        "meshes": len(mesh_objs),
        "armatures": len(arm_objs),
        "bones": len(bones),
        "max_dim_m": round(max_dim, 4),
        "preview": scene.render.filepath,
    }


if __name__ == "__main__" or "bpy" in dir():
    print("IMPORT_PREVIEW_RESULT:", import_and_preview())
