# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Cappuccino Digital.
"""Undoable user actions; validate every batch before writing keys."""
import logging
import bpy
from bpy.props import BoolProperty, EnumProperty
from . import storage, evaluator, ui_state


def guarded(operator, context, operation):
    try:
        return operation()
    except (ValueError, RuntimeError) as exc:
        ui_state.notify(operator, context, str(exc), 'ERROR')
        return {'CANCELLED'}
    except Exception as exc:
        logging.getLogger(__package__).exception('STAGEFLIP operator failed')
        ui_state.notify(operator, context, f'STAGEFLIP failed: {exc}. See the system console', 'ERROR')
        return {'CANCELLED'}


class STAGEFLIP_OT_add_collection(bpy.types.Operator):
    bl_idname = 'stageflip.add_collection'
    bl_label = 'Add Collection'
    bl_description = 'Manage the chosen Collection; its global visibility affects all Scenes using it'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        def run():
            scene = context.scene
            entry = storage.add(scene, scene.stageflip.candidate)
            scene.stageflip.candidate = None
            shared = storage.shared_scenes(entry.collection)
            if len(shared) > 1:
                ui_state.notify(self, context, f'Added {entry.collection.name}. Shared visibility affects all Scenes using it.', 'WARNING')
            else:
                ui_state.notify(self, context, f'Added {entry.collection.name}')
            return {'FINISHED'}
        return guarded(self, context, run)


class STAGEFLIP_OT_remove_collection(bpy.types.Operator):
    bl_idname = 'stageflip.remove_collection'
    bl_label = 'Remove Active Collection'
    bl_description = 'Stop managing the highlighted row and restore its original flags; animated bindings require deletion confirmation'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene and bool(context.scene.stageflip.entries)

    confirm_delete_animation: BoolProperty(
        name='Delete this binding and its visibility animation', default=False,
        options={'SKIP_SAVE'})

    def invoke(self, context, event):
        scene = context.scene
        index = min(scene.stageflip.active_index, len(scene.stageflip.entries) - 1)
        self.confirm_delete_animation = False
        if storage.removal_has_animation(scene, scene.stageflip.entries[index]):
            return context.window_manager.invoke_props_dialog(self, width=440)
        return self.execute(context)

    def draw(self, context):
        self.layout.label(text='Removing this binding deletes its visibility curves.', icon='ERROR')
        self.layout.label(text='Cancel to keep the animation. Undo can restore removal.')
        self.layout.prop(self, 'confirm_delete_animation')

    def execute(self, context):
        def run():
            scene = context.scene
            index = min(scene.stageflip.active_index, len(scene.stageflip.entries) - 1)
            collection = scene.stageflip.entries[index].collection
            name = collection.name if collection else 'missing Collection'
            storage.remove(scene, index, confirm_delete_animation=self.confirm_delete_animation)
            evaluator.evaluate(scene)
            ui_state.notify(self, context, f'Removed {name}')
            return {'FINISHED'}
        return guarded(self, context, run)


class STAGEFLIP_OT_select_all(bpy.types.Operator):
    bl_idname = 'stageflip.select_all'
    bl_label = 'Select Managed Collections'
    bl_description = 'Choose checked rows for batch keys; with no checks, keys affect the active row'
    bl_options = {'REGISTER', 'UNDO'}
    selected: BoolProperty(default=True)

    @classmethod
    def description(cls, context, properties):
        return ('Check all managed Collections for batch keying' if properties.selected
                else 'Clear all checks; key operations will use only the highlighted active row')

    def execute(self, context):
        for entry in context.scene.stageflip.entries:
            entry.selected = self.selected
        message = (f'Selected {len(context.scene.stageflip.entries)} Collections' if self.selected
                   else 'Selection cleared; keying the active Collection')
        ui_state.notify(self, context, message)
        return {'FINISHED'}


class STAGEFLIP_OT_key_visibility(bpy.types.Operator):
    bl_idname = 'stageflip.key_visibility'
    bl_label = 'Key Collection Visibility'
    bl_description = 'Show or hide and key checked Collections, or the active row when no rows are checked'
    bl_options = {'REGISTER', 'UNDO'}
    action: EnumProperty(items=[('SHOW', 'Show + Key', ''), ('HIDE', 'Hide + Key', ''),
                                ('INSERT', 'Insert / Update Key', '')], default='INSERT')

    @classmethod
    def description(cls, context, properties):
        action = {'SHOW': 'Show and insert or update constant visibility keys',
                  'HIDE': 'Hide and insert or update constant visibility keys',
                  'INSERT': 'Insert or update keys from the current Scene visibility channel values'}[properties.action]
        return action + '. Uses the chosen channels and checked rows, or the active row when none are checked.'

    @classmethod
    def poll(cls, context):
        return context.scene and bool(context.scene.stageflip.entries)

    def execute(self, context):
        def run():
            scene = context.scene
            entries = storage.targets(scene)
            storage.validate_targets(scene, entries)
            channels = storage.selected_channels(scene)
            # Scene channels are the authoring source of truth. The evaluator
            # can restore externally changed Outliner flags before an operator runs.
            values = [(entry, channel, (getattr(entry, channel + '_visible')
                       if self.action == 'INSERT' else self.action == 'SHOW'))
                      for entry in entries for channel in channels]
            for entry, channel, visible in values:
                storage.insert_key(scene, entry, channel, visible)
            evaluator.evaluate(scene)
            context.view_layer.update()
            action = {'SHOW': 'Show keyed', 'HIDE': 'Hide keyed', 'INSERT': 'Keys updated'}[self.action]
            channel_label = {'BOTH': 'both channels', 'VIEWPORT': 'viewport', 'RENDER': 'render'}[scene.stageflip.channels]
            ui_state.notify(self, context, f'{action}: {len(entries)} Collection(s), {channel_label}, frame {scene.frame_current_final:g}')
            return {'FINISHED'}
        return guarded(self, context, run)


class STAGEFLIP_OT_delete_key(bpy.types.Operator):
    bl_idname = 'stageflip.delete_key'
    bl_label = 'Delete Key'
    bl_description = 'Delete keys at this frame in the chosen channels; deleting the final key keeps its current value'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene and bool(context.scene.stageflip.entries)

    def execute(self, context):
        def run():
            scene = context.scene
            entries = storage.targets(scene)
            storage.validate_targets(scene, entries)
            deleted = sum(storage.delete_key(scene, e, ch)
                          for e in entries for ch in storage.selected_channels(scene))
            evaluator.evaluate(scene)
            context.view_layer.update()
            message = (f'Deleted {deleted} key(s) at frame {scene.frame_current_final:g}' if deleted
                       else f'No target keys at frame {scene.frame_current_final:g}')
            ui_state.notify(self, context, message, 'INFO' if deleted else 'WARNING')
            return {'FINISHED'}
        return guarded(self, context, run)


CLASSES = (STAGEFLIP_OT_add_collection, STAGEFLIP_OT_remove_collection,
           STAGEFLIP_OT_select_all, STAGEFLIP_OT_key_visibility, STAGEFLIP_OT_delete_key)
