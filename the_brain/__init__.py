import bpy

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
        layout.operator("brain.draw_skeleton", text="Draw Test Skeleton")

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

classes = (
    BRAIN_PT_panel,
    BRAIN_OT_draw_skeleton,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
