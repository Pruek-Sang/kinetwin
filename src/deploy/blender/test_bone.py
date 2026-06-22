import bpy
import bmesh
import math
from mathutils import Vector

def create_bone_obj(name, length, radius):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    bm = bmesh.new()
    
    segments = 8
    rings = [
        (0.0, radius * 1.1),
        (min(length * 0.15, radius * 1.5), radius * 0.8),
        (length * 0.5, radius * 0.5),
        (length - min(length * 0.15, radius * 1.5), radius * 0.8),
        (length, radius * 1.1)
    ]
    
    circle_verts = []
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        # slightly flattened in Y (so it's wider in X, like a real finger bone)
        circle_verts.append((math.cos(angle), math.sin(angle) * 0.8))
        
    created_rings = []
    for z, r in rings:
        ring_verts = []
        for cx, cy in circle_verts:
            v = bm.verts.new((cx * r, cy * r, z))
            ring_verts.append(v)
        created_rings.append(ring_verts)
        
    # Create faces
    for r_idx in range(len(created_rings) - 1):
        ring1 = created_rings[r_idx]
        ring2 = created_rings[r_idx + 1]
        for i in range(segments):
            v1 = ring1[i]
            v2 = ring1[(i + 1) % segments]
            v3 = ring2[(i + 1) % segments]
            v4 = ring2[i]
            bm.faces.new((v1, v2, v3, v4))
            
    # Caps
    bm.faces.new(reversed(created_rings[0]))
    bm.faces.new(created_rings[-1])
    
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    
    for poly in mesh.polygons:
        poly.use_smooth = True
        
    # Add subsurf modifier for that smooth skeletal look
    subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subsurf.levels = 1
    subsurf.render_levels = 2
    
    return obj

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Test
obj = create_bone_obj("TestBone", 0.05, 0.005)

# Render to check
bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.render.filepath = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\render_output\bone_test.png"

# Camera
bpy.ops.object.camera_add(location=(0.04, -0.04, 0.04))
cam = bpy.context.active_object
cam.rotation_euler = (math.radians(60), 0, math.radians(45))
bpy.context.scene.camera = cam

# Light
bpy.ops.object.light_add(type='SUN', location=(0, 0, 1))
bpy.ops.render.render(write_still=True)
