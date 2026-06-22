import socket
import json
import traceback

code = r"""
import bpy
cup = bpy.data.objects.get("Cup")
if cup and cup.animation_data and cup.animation_data.action:
    print("ACTION DIR:", dir(cup.animation_data.action))
    
    # Just recreate the cup's animation completely!
    cup.animation_data_clear()
    
    arm = bpy.data.objects.get("HandRig")
    
    # Base location (when grasped)
    bpy.context.scene.frame_set(45)
    bpy.context.view_layer.update()
    # Snap cup to the palm's base
    cup_grasp_loc = arm.matrix_world @ __import__("mathutils").Vector((0.0, 0.06, -0.01))
    
    # Lifted location
    bpy.context.scene.frame_set(72)
    bpy.context.view_layer.update()
    cup_lift_loc = arm.matrix_world @ __import__("mathutils").Vector((0.0, 0.06, -0.01))
    
    for f in [1, 30, 45]:
        bpy.context.scene.frame_set(f)
        cup.location = cup_grasp_loc
        cup.keyframe_insert(data_path="location", frame=f)
        
    for f in [72, 90]:
        bpy.context.scene.frame_set(f)
        cup.location = cup_lift_loc
        cup.keyframe_insert(data_path="location", frame=f)
        
    bpy.context.scene.frame_set(1)

result = {"status": "success"}
"""

request = {
    "type": "execute",
    "code": code,
    "strict_json": False
}

payload = json.dumps(request).encode('utf-8') + b'\0'

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(15.0)
        s.connect(('127.0.0.1', 9876))
        s.sendall(payload)
        
        data = bytearray()
        while b'\0' not in data:
            try:
                chunk = s.recv(4096)
                if not chunk: break
                data.extend(chunk)
            except socket.timeout:
                break
except Exception as e:
    pass
