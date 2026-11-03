# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Cappuccino Digital.
"""Native STAGEFLIP sidebar. Presentation reads animation; it never evaluates it."""
import textwrap
import bpy
from bpy.props import EnumProperty, StringProperty
from . import storage, evaluator


def text_width(context):
    """Approximate label capacity at the current sidebar width and UI scale."""
    region = context.region
    width = region.width if region and region.type == 'UI' else 280
    scale = context.preferences.system.ui_scale
    return max(18, min(64, int((width / scale - 36) / 6.8)))


def wrapped(layout, context, message, icon='NONE'):
    lines = textwrap.wrap(message, width=text_width(context)) or ['']
    for index, line in enumerate(lines):
        layout.label(text=line, icon=icon if index == 0 else 'NONE')


def keyframe_status(scene):
    """Read exact-frame keys for the existing checked/active target semantics."""
    entries = storage.targets(scene)
    channels = storage.selected_channels(scene)
    keyed = 0
    for entry in entries:
        for channel in channels:
            fc = storage.curve(scene, entry, channel)
            if fc and any(abs(point.co.x - scene.frame_current_final) < 1e-5
                          for point in fc.keyframe_points):
                keyed += 1
    total = len(entries) * len(channels)
    state = 'NONE' if keyed == 0 else ('ALL' if keyed == total else 'PARTIAL')
    return {'state': state, 'keyed': keyed, 'total': total}


def collection_status_text(scene, entry_name, channel):
    entry = scene.stageflip.entries.get(entry_name)
    if not entry or not entry.collection:
        return 'This Collection was deleted. Remove its missing entry.'
    collection = entry.collection
    state = 'hidden' if getattr(collection, 'hide_' + channel.lower()) else 'visible'
    return (f'{collection.name}: {channel.lower()} {state}. This is the local Collection flag; '
            'parent Collections, View Layers and object restrictions may also affect visibility.')


class STAGEFLIP_OT_visibility_info(bpy.types.Operator):
    """Read-only status affordance: hover or click, never toggle Collection flags."""
    bl_idname = 'stageflip.visibility_info'
    bl_label = 'Collection Visibility Status'
    entry_name: StringProperty(options={'SKIP_SAVE'})
    channel: EnumProperty(items=[('VIEWPORT', 'Viewport', ''), ('RENDER', 'Render', '')])

    @classmethod
    def description(cls, context, properties):
        return collection_status_text(context.scene, properties.entry_name, properties.channel)

    def execute(self, context):
        self.report({'INFO'}, collection_status_text(context.scene, self.entry_name, self.channel))
        return {'FINISHED'}


class STAGEFLIP_UL_collections(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, 'selected', text='')
        collection = item.collection
        row.label(text=collection.name if collection else 'Missing Collection',
                  icon='OUTLINER_COLLECTION' if collection else 'ERROR')
        if collection:
            for channel, visible_icon, hidden_icon in (
                ('VIEWPORT', 'RESTRICT_VIEW_OFF', 'RESTRICT_VIEW_ON'),
                ('RENDER', 'RESTRICT_RENDER_OFF', 'RESTRICT_RENDER_ON')):
                hidden = getattr(collection, 'hide_' + channel.lower())
                button = row.operator('stageflip.visibility_info', text='',
                                      icon=hidden_icon if hidden else visible_icon, emboss=False)
                button.entry_name = item.name
                button.channel = channel


def draw_collections(layout, context, settings):
    heading = layout.row(align=True)
    heading.label(text='Collections', icon='OUTLINER_COLLECTION')
    if settings.entries:
        count = heading.row()
        count.alignment = 'RIGHT'
        count.label(text=str(len(settings.entries)))
    row = layout.split(factor=0.78, align=True)
    row.prop(settings, 'candidate', text='')
    add = row.row(align=True)
    add.enabled = bool(settings.candidate)
    add.operator('stageflip.add_collection', text='Add', icon='ADD')
    if not settings.entries:
        box = layout.box()
        box.label(text='No Collections managed', icon='OUTLINER_COLLECTION')
        wrapped(box, context, 'Choose a Collection above, then click Add.')
        return
    layout.template_list('STAGEFLIP_UL_collections', '', settings, 'entries',
                         settings, 'active_index', rows=4, maxrows=7)
    row = layout.row(align=True)
    selection = row.row(align=True)
    selection.operator('stageflip.select_all', text='All', icon='CHECKBOX_HLT').selected = True
    selection.operator('stageflip.select_all', text='None', icon='CHECKBOX_DEHLT').selected = False
    row.separator()
    row.operator('stageflip.remove_collection', text='Remove', icon='REMOVE')
    selected = sum(entry.selected for entry in settings.entries)
    layout.label(text=f'{selected} selected for keying' if selected else 'Keying the active Collection',
                 icon='CHECKMARK' if selected else 'RADIOBUT_ON')


def draw_keyframes(layout, context, settings):
    scene = context.scene
    heading = layout.row()
    heading.label(text='Visibility Keys', icon='KEY_HLT')
    heading.label(text=f'Frame {scene.frame_current_final:g}')
    controls = layout.column(align=True)
    controls.enabled = bool(settings.entries)
    controls.row(align=True).prop(settings, 'channels', expand=True)
    row = controls.row(align=True)
    row.scale_y = 1.4
    row.operator('stageflip.key_visibility', text='Show + Key', icon='HIDE_OFF').action = 'SHOW'
    row.operator('stageflip.key_visibility', text='Hide + Key', icon='HIDE_ON').action = 'HIDE'
    row = controls.row(align=True)
    row.operator('stageflip.key_visibility', text='Insert / Update', icon='KEY_HLT').action = 'INSERT'
    row.operator('stageflip.delete_key', text='Delete Key', icon='KEY_DEHLT')
    if settings.entries:
        status = keyframe_status(scene)
        if status['state'] == 'ALL':
            text, icon = 'All target channels keyed', 'KEY_HLT'
        elif status['state'] == 'PARTIAL':
            text, icon = f"{status['keyed']} of {status['total']} target channels keyed", 'KEY_HLT'
        else:
            text, icon = 'No target keys at this frame', 'KEY_DEHLT'
        layout.label(text=text, icon=icon)


def draw_notices(layout, context):
    scene = context.scene
    feedback = context.window_manager.stageflip_feedback
    if feedback.message:
        box = layout.box()
        box.alert = feedback.level == 'ERROR'
        box.label(text='Last operation', icon={'INFO': 'CHECKMARK', 'WARNING': 'INFO', 'ERROR': 'ERROR'}[feedback.level])
        wrapped(box, context, feedback.message)
    problem = storage.animation_problem(scene) or evaluator.issue(scene)
    if problem:
        box = layout.box()
        box.alert = True
        box.label(text='Evaluation needs attention', icon='ERROR')
        wrapped(box, context, problem)
    if any(entry.collection and len(storage.shared_scenes(entry.collection)) > 1
           for entry in scene.stageflip.entries):
        box = layout.box()
        box.label(text='Collection shared across Scenes', icon='ERROR')
        wrapped(box, context, 'Global visibility affects every Scene using it. Competing managed owners are paused.')


def draw_advanced(layout, context):
    header, body = layout.panel('stageflip_options_help', default_closed=True)
    header.label(text='Options & Help', icon='PREFERENCES')
    if body:
        body.prop(context.scene.render, 'use_lock_interface', text='Lock Interface for Rendering')
        wrapped(body, context, 'Checked rows are batch targets. With none checked, keys use the active row.')
        body.separator(factor=0.5)
    layout.label(text='STAGEFLIP 1.0.0')
    layout.label(text='Made by Cappuccino Digital')


class STAGEFLIP_PT_collections(bpy.types.Panel):
    bl_label = 'STAGEFLIP'
    bl_idname = 'STAGEFLIP_PT_collections'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'STAGEFLIP'
    bl_ui_units_x = 18

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = False
        settings = context.scene.stageflip
        draw_collections(layout, context, settings)
        layout.separator(factor=1.2)
        draw_keyframes(layout, context, settings)
        draw_notices(layout, context)
        layout.separator(factor=0.7)
        draw_advanced(layout, context)


CLASSES = (STAGEFLIP_OT_visibility_info, STAGEFLIP_UL_collections, STAGEFLIP_PT_collections)
