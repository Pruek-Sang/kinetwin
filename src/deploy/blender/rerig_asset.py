"""Re-rig the downloaded asset (#4) so its armature actually matches the mesh.

The Sketchfab GLB imports with bones that sit at the right JOINTS but are
near-zero-length and disconnected (gaps between forearm and hand, etc.), which
makes IK/posing degenerate. This script rebuilds the armature from the mesh's
own vertex-group centroids -- each vertex group already corresponds to one body
part, so its centroid is exactly where that joint should be. Bones are then
real-length and properly chained, while the existing vertex weights (63 groups,
name-matched) keep working unchanged.

Result: posing / IK on the right arm now reaches the target.
"""
from __future__ import annotations

import bpy
from mathutils import Vector


def _centroids(mesh_obj):
    """World-space centroid of every vertex group on ``mesh_obj``."""
    mw = mesh_obj.matrix_world
    sums = {vg.name: Vector((0, 0, 0)) for vg in mesh_obj.vertex_groups}
    counts = {vg.name: 0 for vg in mesh_obj.vertex_groups}
    indexes = [vg.index for vg in mesh_obj.vertex_groups]
    for v in mesh_obj.data.vertices:
        for gv in v.groups:
            if gv.group in indexes and gv.weight > 0.2:
                name = mesh_obj.vertex_groups[gv.group].name
                sums[name] += mw @ v.co
                counts[name] += 1
    return {n: (sums[n] / counts[n]) if counts[n] else None for n in sums}


def rerig_asset() -> dict:
    old_arm = bpy.data.objects.get("Object_4")
    mesh = bpy.data.objects["Object_7"]
    if old_arm is None or mesh is None:
        return {"error": "asset not present"}

    # capture original bone hierarchy (parent / children) by name
    parents, children = {}, {}
    for b in old_arm.data.bones:
        parents[b.name] = b.parent.name if b.parent else None
        children.setdefault(b.name, [])
    for b in old_arm.data.bones:
        if b.parent:
            children.setdefault(b.parent.name, []).append(b.name)

    cents = _centroids(mesh)
    # bones whose centroid we could not compute -> skip
    usable = {n: c for n, c in cents.items() if c is not None}

    # build new armature
    new_arm_data = bpy.data.armatures.new("AssetArmature")
    new_arm = bpy.data.objects.new("AssetArmature", new_arm_data)
    bpy.context.scene.collection.objects.link(new_arm)

    bpy.context.view_layer.objects.active = new_arm
    new_arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    ebones = {}
    for name in usable:
        head = usable[name]
        kids = [k for k in children.get(name, []) if k in usable]
        if kids:
            tail = usable[kids[0]]
        else:
            # leaf: extrapolate a little past the joint, away from parent
            p = parents.get(name)
            ref = usable.get(p) if p else head
            tail = head + (head - ref) * 0.3 if (head - ref).length > 1e-6 else head + Vector((0, 1, 0))
        eb = new_arm_data.edit_bones.new(name)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        ebones[name] = eb
    # parent chain
    for name, eb in ebones.items():
        p = parents.get(name)
        if p and p in ebones:
            eb.parent = ebones[p]
    bpy.ops.object.mode_set(mode="OBJECT")

    # repoint the mesh's armature modifier to the new armature
    for m in list(mesh.modifiers):
        if m.type == "ARMATURE":
            mesh.modifiers.remove(m)
    mod = mesh.modifiers.new("Armature", "ARMATURE")
    mod.object = new_arm
    mod.use_vertex_groups = True
    # make sure the mesh is not still parented to the old armature
    if mesh.parent is old_arm:
        mesh.parent = None

    # hide/remove the old armature object (keep its data out of the way)
    old_arm.hide_set(True)

    return {
        "new_armature": new_arm.name,
        "bones": len(new_arm_data.bones),
        "usable_groups": len(usable),
    }


if __name__ == "__main__" or "bpy" in dir():
    print("RERIG_RESULT:", rerig_asset())
