import bpy
import json

def read_scene(context):
    scene = context.scene

    # Basic scene information
    data = {
        "scene_name": scene.name,
        "current_frame": scene.frame_current,
        "objects": []
    }

    # Collect information about objects in the scene
    for obj in scene.objects:
        obj_data = {
            "name": obj.name,
            "type": obj.type,
            "location": [round(c, 4) for c in obj.location],
            "rotation_euler": [round(c, 4) for c in obj.rotation_euler],
            "scale": [round(c, 4) for c in obj.scale],
        }
        data["objects"].append(obj_data)

    # Dump to JSON and print to console
    snapshot = json.dumps(data, indent=4)
    print("=== THE BRAIN: SCENE SNAPSHOT ===")
    print(snapshot)
    print("=================================")

    return data
