import bpy
import json
import os
from mathutils import Vector

def extract_and_save(context):
    obj = context.active_object
    if not obj or obj.type != 'GREASEPENCIL':
        print("Active object is not a Grease Pencil object.")
        return None

    # GP3 API: Get active layer
    layer = obj.data.layers.active
    if not layer:
        print("No active layer found.")
        return None

    current_frame_num = context.scene.frame_current

    # Find the frame that matches the current frame number
    frame = None
    for f in layer.frames:
        if f.frame_number == current_frame_num:
            frame = f
            break

    if not frame:
        print(f"No drawing found on active layer at frame {current_frame_num}.")
        return None

    # Calculate bounding box
    min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
    max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

    has_points = False

    # Read the points from the strokes using GP3 API
    for stroke in frame.drawing.strokes:
        for point in stroke.points:
            pos = Vector(point.position)
            # Transform to world coordinates
            world_pos = obj.matrix_world @ pos

            min_x = min(min_x, world_pos.x)
            min_y = min(min_y, world_pos.y)
            min_z = min(min_z, world_pos.z)

            max_x = max(max_x, world_pos.x)
            max_y = max(max_y, world_pos.y)
            max_z = max(max_z, world_pos.z)

            has_points = True

    if not has_points:
        print("No points found in the current frame's drawing.")
        return None

    height = max_z - min_z
    width = max_x - min_x
    depth = max_y - min_y

    data = {
        "height": round(height, 4),
        "width": round(width, 4),
        "depth": round(depth, 4),
        "bounding_box": {
            "min": [round(min_x, 4), round(min_y, 4), round(min_z, 4)],
            "max": [round(max_x, 4), round(max_y, 4), round(max_z, 4)]
        }
    }

    # Save to the_brain_character.json next to the .blend file
    dir_path = os.path.dirname(bpy.data.filepath)
    if not dir_path:
        dir_path = os.path.abspath(".")

    out_path = os.path.join(dir_path, "the_brain_character.json")

    try:
        with open(out_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Saved character proportions to {out_path}")
    except Exception as e:
        print(f"Failed to save {out_path}: {e}")

    return height
