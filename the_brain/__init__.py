import bpy
import json
import os
import threading
from . import scene_reader
from . import proportion_extractor
from . import ai_client

bl_info = {
    "name": "The Brain",
    "author": "Jules",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > The Brain",
    "description": "Blender Grease Pencil AI Co-Pilot Addon Phase 1",
    "category": "3D View",
}

class BRAIN_PT_panel(bpy.types.Panel):
    bl_label = "The Brain"
    bl_idname = "BRAIN_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'The Brain'

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "brain_api_key")
        layout.prop(context.scene, "brain_prompt_text")

        row = layout.row()
        row.operator("brain.send_to_ai", text="Send")
        row.label(text=f"Status: {context.scene.brain_status}")

        layout.separator()
        layout.operator("brain.draw_skeleton", text="Draw Test Skeleton")
        layout.operator("brain.read_scene", text="Read Scene")
        layout.operator("brain.set_character_reference", text="Set Character Reference")

        height = context.scene.brain_character_height
        if height > 0.0:
            layout.label(text=f"Locked Character Height: {height:.2f}m")

class BRAIN_OT_draw_skeleton(bpy.types.Operator):
    bl_idname = "brain.draw_skeleton"
    bl_label = "Draw Test Skeleton"
    bl_description = "Draws a hardcoded T-pose skeleton on a GP layer called AI_Guide"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Create or find a Grease Pencil object
        gp_obj = None
        for obj in context.scene.objects:
            if obj.type == 'GREASEPENCIL':
                gp_obj = obj
                break

        if not gp_obj:
            gp_data = bpy.data.grease_pencils_v3.new("Brain_GP")
            gp_obj = bpy.data.objects.new("Brain_GP", gp_data)
            context.collection.objects.link(gp_obj)

        # Ensure it's the active object
        context.view_layer.objects.active = gp_obj

        # Material for Cyan color
        mat_name = "Brain_Cyan"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)

        # Ensure material is in object slots
        if mat.name not in [m.name for m in gp_obj.data.materials if m]:
            gp_obj.data.materials.append(mat)

        mat_index = gp_obj.data.materials.find(mat.name)

        # Layer AI_Guide
        layer_name = "AI_Guide"
        layer = gp_obj.data.layers.get(layer_name)
        if not layer:
            layer = gp_obj.data.layers.new(layer_name)

        # Frame 1
        frame = None
        for f in layer.frames:
            if f.frame_number == 1:
                frame = f
                break
        if not frame:
            frame = layer.frames.new(1)

        # Draw T-Pose Skeleton
        # Coordinates for a simple stick figure
        lines = [
            # Spine
            ((0.0, 0.0, 1.0), (0.0, 0.0, 1.5)),
            # Arms
            ((-1.0, 0.0, 1.3), (1.0, 0.0, 1.3)),
            # Lower spine
            ((0.0, 0.0, 1.0), (0.0, 0.0, 0.5)),
            # Left leg
            ((0.0, 0.0, 0.5), (-0.5, 0.0, 0.0)),
            # Right leg
            ((0.0, 0.0, 0.5), (0.5, 0.0, 0.0)),
        ]

        for p1, p2 in lines:
            frame.drawing.add_strokes([2])
            stroke = frame.drawing.strokes[-1]
            stroke.points[0].position = p1
            stroke.points[1].position = p2
            # Assign material
            stroke.material_index = mat_index

        return {'FINISHED'}

class BRAIN_OT_read_scene(bpy.types.Operator):
    bl_idname = "brain.read_scene"
    bl_label = "Read Scene"
    bl_description = "Reads scene information and prints to console"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene_reader.read_scene(context)
        return {'FINISHED'}

class BRAIN_OT_send_to_ai(bpy.types.Operator):
    bl_idname = "brain.send_to_ai"
    bl_label = "Send to AI"
    bl_description = "Sends scene and prompt to AI for pose generation"

    _timer = None
    _thread = None
    _result = None
    _error = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            if not self._thread.is_alive():
                context.window_manager.event_timer_remove(self._timer)
                if self._error:
                    context.scene.brain_status = "Error"
                    self.report({'ERROR'}, f"API Error: {self._error}")
                    print(f"Error: {self._error}")
                else:
                    context.scene.brain_status = "Response Received"
                    print("=== THE BRAIN: AI RESPONSE (JOINT COORDINATES) ===")
                    print(json.dumps(self._result, indent=4))
                    print("==================================================")
                return {'FINISHED'}
        return {'PASS_THROUGH'}

    def execute(self, context):
        api_key = context.scene.brain_api_key
        if not api_key:
            self.report({'ERROR'}, "API Key is missing.")
            return {'CANCELLED'}

        prompt_text = context.scene.brain_prompt_text
        if not prompt_text:
            self.report({'ERROR'}, "Prompt text is missing.")
            return {'CANCELLED'}

        # Read Scene Snapshot
        scene_data = scene_reader.read_scene(context)

        # Read Character Proportions
        proportions_data = {}
        dir_path = os.path.dirname(bpy.data.filepath)
        if not dir_path:
            dir_path = os.path.abspath(".")
        prop_file_path = os.path.join(dir_path, "the_brain_character.json")
        if os.path.exists(prop_file_path):
            with open(prop_file_path, 'r') as f:
                try:
                    proportions_data = json.load(f)
                except Exception as e:
                    print(f"Error reading proportions file: {e}")

        system_prompt = "You are a 2D animation pose assistant. You receive a character's locked proportions and a camera setup. Your ONLY job is to return joint positions for the requested action. Return ONLY valid JSON, no text, no explanation. The JSON must contain these joints: head_top, head_center, neck, left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist, hip_center, left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle. Each joint is [x, y, z] in world space. Maintain the locked proportions exactly."

        user_message_dict = {
            "scene": scene_data,
            "proportions": proportions_data,
            "prompt": prompt_text
        }
        user_message = json.dumps(user_message_dict, indent=4)

        context.scene.brain_status = "Thinking"

        # Background worker for API
        def worker():
            try:
                response = ai_client.call_openrouter(api_key, system_prompt, user_message)
                # The response object should be parsed
                if "choices" in response and len(response["choices"]) > 0:
                    message_content = response["choices"][0]["message"]["content"]
                    try:
                        self._result = json.loads(message_content)
                    except json.JSONDecodeError:
                        self._error = "Invalid JSON returned by AI"
                else:
                    self._error = "Invalid response format from OpenRouter"
            except Exception as e:
                self._error = str(e)

        self._thread = threading.Thread(target=worker)
        self._thread.start()

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}


class BRAIN_OT_set_character_reference(bpy.types.Operator):
    bl_idname = "brain.set_character_reference"
    bl_label = "Set Character Reference"
    bl_description = "Extracts height from active Grease Pencil layer and saves proportions"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        height = proportion_extractor.extract_and_save(context)
        if height is not None:
            context.scene.brain_character_height = height
            self.report({'INFO'}, f"Character height locked at {height:.2f}m")
        else:
            self.report({'WARNING'}, "Could not extract character height. Make sure a GP object with strokes is active.")
        return {'FINISHED'}

classes = (
    BRAIN_PT_panel,
    BRAIN_OT_draw_skeleton,
    BRAIN_OT_read_scene,
    BRAIN_OT_send_to_ai,
    BRAIN_OT_set_character_reference,
)

def register():
    bpy.types.Scene.brain_character_height = bpy.props.FloatProperty(
        name="Character Height",
        description="The locked height of the character",
        default=0.0
    )
    bpy.types.Scene.brain_api_key = bpy.props.StringProperty(
        name="API Key",
        description="OpenRouter API Key",
        default="",
        subtype='PASSWORD'
    )
    bpy.types.Scene.brain_prompt_text = bpy.props.StringProperty(
        name="Prompt",
        description="Action to generate (e.g., 'Character is jumping')",
        default=""
    )
    bpy.types.Scene.brain_status = bpy.props.StringProperty(
        name="Status",
        description="Current status of AI",
        default="Idle"
    )
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    del bpy.types.Scene.brain_status
    del bpy.types.Scene.brain_prompt_text
    del bpy.types.Scene.brain_api_key
    del bpy.types.Scene.brain_character_height
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
