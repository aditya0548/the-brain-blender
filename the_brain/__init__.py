import bpy
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
        scene = context.scene

        layout.prop(scene, "brain_api_key", text="API Key")
        layout.prop(scene, "brain_user_message", text="Prompt")

        layout.operator("brain.ask_ai", text="Ask AI")
        layout.label(text=f"Status: {scene.brain_ai_status}")

        layout.separator()

        layout.operator("brain.draw_skeleton", text="Draw Test Skeleton")
        layout.operator("brain.read_scene", text="Read Scene")
        layout.operator("brain.set_character_reference", text="Set Character Reference")

        height = scene.brain_character_height
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


class BRAIN_OT_ask_ai(bpy.types.Operator):
    bl_idname = "brain.ask_ai"
    bl_label = "Ask AI"
    bl_description = "Sends the user message to OpenRouter API"
    bl_options = {'REGISTER'}

    _timer = None
    def modal(self, context, event):
        if event.type == 'TIMER':
            if hasattr(self, 'status') and self.status is not None:
                # Thread has finished
                context.window_manager.event_timer_remove(self._timer)
                if self.status.startswith("Error:"):
                    self.report({'ERROR'}, f"API {self.status}")
                    context.scene.brain_ai_status = "Error"
                else:
                    self.report({'INFO'}, "Received response from AI.")
                    context.scene.brain_ai_status = "Response Received"

                # Request a redraw to update the UI
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()

                return {'FINISHED'}
        return {'PASS_THROUGH'}

    def execute(self, context):
        api_key = context.scene.brain_api_key
        user_message = context.scene.brain_user_message

        if not api_key:
            self.report({'WARNING'}, "API Key is required.")
            return {'CANCELLED'}
        if not user_message:
            self.report({'WARNING'}, "Prompt is required.")
            return {'CANCELLED'}

        context.scene.brain_ai_status = "Thinking..."

        self.status = None

        def handle_response(content, error):
            if error:
                self.status = f"Error: {error}"
            else:
                self.status = "Response Received"
                print("AI Response:", content)

        # Start background thread
        ai_client.call_openrouter(api_key, user_message, handle_response)

        # Start timer for polling
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


classes = (
    BRAIN_PT_panel,
    BRAIN_OT_draw_skeleton,
    BRAIN_OT_read_scene,
    BRAIN_OT_set_character_reference,
    BRAIN_OT_ask_ai,
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
    bpy.types.Scene.brain_user_message = bpy.props.StringProperty(
        name="User Message",
        description="Prompt for the AI",
        default=""
    )
    bpy.types.Scene.brain_ai_status = bpy.props.StringProperty(
        name="AI Status",
        description="Status of the AI request",
        default="Ready"
    )

    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    del bpy.types.Scene.brain_character_height
    del bpy.types.Scene.brain_api_key
    del bpy.types.Scene.brain_user_message
    del bpy.types.Scene.brain_ai_status
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
