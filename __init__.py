# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Cappuccino Digital.
"""STAGEFLIP 1.0.0. Made by Cappuccino Digital. Blender extension entry point."""
import bpy
from . import properties, storage, evaluator, operators, ui, ui_state

_classes = properties.CLASSES + ui_state.CLASSES + operators.CLASSES + ui.CLASSES
_registered = False


def register():
    global _registered
    if _registered:
        return
    completed = []
    try:
        for cls in _classes:
            bpy.utils.register_class(cls)
            completed.append(cls)
        bpy.types.Scene.stageflip = bpy.props.PointerProperty(type=properties.STAGEFLIP_PG_settings)
        bpy.types.WindowManager.stageflip_feedback = bpy.props.PointerProperty(
            type=ui_state.STAGEFLIP_PG_feedback, options={'SKIP_SAVE'})
        evaluator.register()
    except Exception:
        evaluator.unregister()
        if hasattr(bpy.types.Scene, 'stageflip'):
            del bpy.types.Scene.stageflip
        if hasattr(bpy.types.WindowManager, 'stageflip_feedback'):
            del bpy.types.WindowManager.stageflip_feedback
        for cls in reversed(completed):
            bpy.utils.unregister_class(cls)
        raise
    _registered = True


def unregister():
    global _registered
    evaluator.unregister()
    if not _registered:
        return
    # Restore only Collection flags. Serialized bindings/keys are retained for re-enable.
    for scene in bpy.data.scenes:
        for entry in scene.stageflip.entries:
            storage.restore_entry(entry)
    del bpy.types.Scene.stageflip
    del bpy.types.WindowManager.stageflip_feedback
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
    _registered = False
