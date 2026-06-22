import math
import os
import bpy
from mathutils import Vector, Matrix

# Input / Output paths
BLEND_IN = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\render_output\skeleton_scene.blend"
STILL_OUT = r"C:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\render_output\grasp_test.png"

def test_grasp_x_axis():
    # Load the skeleton scene
    bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
    
    arm = bpy.data.objects["HandRig"]
    
    # Clear animation data so it doesn't overwrite our manual pose
    if arm.animation_data:
        arm.animation_data_clear()
        
    cup = bpy.data.objects.get("Cup")
    if cup:
        if cup.animation_data:
            cup.animation_data_clear()
        # Clean constraints
        for c in list(cup.constraints):
            cup.constraints.remove(c)
        # Position cup at target
        cup.location = (0.0, 0.20, 0.05)
        cup.rotation_euler = (0, 0, 0)
        
    # 1) Rotate the armature object so the arm points along the world X-axis
    R = Matrix((
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0)
    ))
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = R.to_euler('XYZ')
    
    # 2) Put the armature into Pose mode and reset bones
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        for i in range(3):
            pb.lock_rotation[i] = False
            
    # 3) Lock the wrist/forearm straight (single rigid line)
    LOCK_STRAIGHT = ["root", "wrist", "palm"]
    for bn in LOCK_STRAIGHT:
        if bn in arm.pose.bones:
            pb = arm.pose.bones[bn]
            pb.rotation_euler = (0, 0, 0)
            for i in range(3):
                pb.lock_rotation[i] = True
                
    # 4) Position the hand relative to the cup using the corrected math
    # We want knuckles to be at world (-0.038, 0.20, 0.05) to be right on the surface (radius 0.035 + some margin)
    root = arm.pose.bones["root"]
    root.location = (0.05, -0.127, 0.158)
    
    # 5) Curl fingers around the cup with natural angles to wrap the surface (not penetrate)
    # Segment 1 (MCP): 42 degrees
    # Segment 2 (PIP): 35 degrees
    # Segment 3 (DIP): 22 degrees
    angles = {
        "01": math.radians(42),
        "02": math.radians(35),
        "03": math.radians(22)
    }
    
    # Thumb: opposable curl angles
    thumb_angles = {
        "01": math.radians(25),
        "02": math.radians(30),
        "03": math.radians(20)
    }
    
    INDEX_MIDDLE = ["f_index", "f_middle"]
    RING_PINKY = ["f_ring", "f_pinky"]
    
    for pb in arm.pose.bones:
        parts = pb.name.split(".")
        if len(parts) == 2:
            name, seg = parts[0], parts[1]
            if name in INDEX_MIDDLE:
                pb.rotation_euler = (-angles[seg], 0, 0)
            elif name in RING_PINKY:
                pb.rotation_euler = (angles[seg], 0, 0)
            elif name == "thumb":
                pb.rotation_euler = (-thumb_angles[seg], 0, 0)
                
    bpy.ops.object.mode_set(mode="OBJECT")
    
    # Force depsgraph evaluation to update all matrices
    bpy.context.evaluated_depsgraph_get().update()
    
    # Print the coordinates of landmarks from within the script
    print("LM_COORDINATES:")
    for i in range(21):
        ename = f"LM_{i:02d}"
        e = bpy.data.objects.get(ename)
        if e:
            print(f"  {ename}: {[round(v, 4) for v in e.matrix_world.translation]}")
            
    # Let's position the camera to frame this new X-axis orientation
    cam = bpy.data.objects.get("Camera")
    if cam:
        cam.location = (-0.22, 0.20 - 0.28, 0.25)
        target = Vector((0.0, 0.20, 0.08))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        
    # Render and save
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = STILL_OUT
    bpy.ops.render.render(write_still=True)
    print("RENDERED TO:", STILL_OUT)

if __name__ == "__main__":
    test_grasp_x_axis()
