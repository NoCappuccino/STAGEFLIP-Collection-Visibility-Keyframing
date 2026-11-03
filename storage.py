# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Cappuccino Digital.
"""Bindings and native Action keys. No visibility writes to individual objects.

Named CollectionProperty paths survive list reorder/removal and Collection renames.
Scene Action slots hold the native visibility channels.
"""
import uuid
import bpy
from bpy_extras.anim_utils import (action_get_channelbag_for_slot,
                                 action_ensure_channelbag_for_slot)

CHANNELS = ('viewport', 'render')


def scene_collections(scene):
    found = set()
    pending = list(scene.collection.children)
    while pending:
        collection = pending.pop()
        if collection in found:
            continue
        found.add(collection)
        pending.extend(collection.children)
    return found


def owners(collection):
    return [scene for scene in bpy.data.scenes if hasattr(scene, 'stageflip')
            and any(e.collection == collection for e in scene.stageflip.entries)]


def ownership_map():
    result = {}
    for scene in bpy.data.scenes:
        if not hasattr(scene, 'stageflip'):
            continue
        for entry in scene.stageflip.entries:
            if entry.collection:
                result.setdefault(entry.collection, set()).add(scene)
    return result


def shared_scenes(collection):
    return [scene for scene in bpy.data.scenes if collection in scene_collections(scene)]


def path(entry, channel):
    if channel not in CHANNELS:
        raise ValueError('Unknown visibility channel')
    # path_from_id() uses indices even when the entry has a name. Explicit name
    # lookup keeps remaining curves stable when an earlier row is removed.
    return f'stageflip.entries["{entry.name}"].{channel}_visible'


def channelbag(scene):
    ad = scene.animation_data
    return action_get_channelbag_for_slot(ad.action, ad.action_slot) if ad else None


def curve(scene, entry, channel):
    bag = channelbag(scene)
    return bag.fcurves.find(path(entry, channel)) if bag else None


def animation_problem(scene):
    """Reject animation mixing whose semantics direct F-Curve sampling cannot honor."""
    ad = scene.animation_data
    if not ad:
        return ''
    if ad.use_tweak_mode or any(not track.mute for track in ad.nla_tracks):
        return 'STAGEFLIP requires an active Action without NLA blending or tweak mode'
    if any(fc.data_path.startswith('stageflip.') for fc in ad.drivers):
        return 'Drivers on STAGEFLIP channels are not supported by STAGEFLIP'
    action = ad.action
    if not action:
        return ''
    if action.library or action.override_library:
        return 'Use a local Scene Action for STAGEFLIP keys'
    if not ad.action_slot:
        return 'The Scene Action needs an assigned Scene slot'
    if len(action.layers) != 1 or len(action.layers[0].strips) != 1:
        return 'STAGEFLIP supports one Action layer with one keyframe strip'
    bag = channelbag(scene)
    if bag:
        for fc in bag.fcurves:
            if fc.data_path.startswith('stageflip.') and len(fc.modifiers):
                return 'F-Curve modifiers on STAGEFLIP channels are not supported by STAGEFLIP'
    return ''


def require_editable_animation(scene):
    problem = animation_problem(scene)
    if problem:
        raise ValueError(problem)
    ad = scene.animation_data
    if ad and ad.action and action_is_shared(ad.action):
        raise ValueError('Make the Scene Action single-user before editing STAGEFLIP keys')


def action_is_shared(action):
    return action.users - int(action.use_fake_user) > 1


def add(scene, collection):
    if scene.library or scene.override_library:
        raise ValueError('Use a local editable Scene for STAGEFLIP')
    if not collection:
        raise ValueError('Choose a Collection to manage')
    if collection.library or collection.override_library:
        raise ValueError('Choose a local Collection; linked data and overrides are not supported yet')
    if collection not in scene_collections(scene):
        raise ValueError('The Collection must be linked to the current Scene')
    if any(e.collection == collection for e in scene.stageflip.entries):
        raise ValueError('This Collection is already managed in this Scene')
    if any(owner != scene for owner in owners(collection)):
        raise ValueError('This Collection is already managed by another Scene; global flags cannot be independent')
    entries = scene.stageflip.entries
    for entry in entries:
        entry.selected = False
    entry = entries.add()
    entry.name = uuid.uuid4().hex
    entry.collection = collection
    entry.selected = True
    entry.original_viewport_hidden = collection.hide_viewport
    entry.original_render_hidden = collection.hide_render
    entry.viewport_visible = not collection.hide_viewport
    entry.render_visible = not collection.hide_render
    scene.stageflip.active_index = len(entries) - 1
    return entry


def targets(scene):
    settings = scene.stageflip
    selected = [e for e in settings.entries if e.selected]
    if selected:
        return selected
    if settings.entries:
        return [settings.entries[min(settings.active_index, len(settings.entries) - 1)]]
    return []


def validate_targets(scene, entries):
    if not entries:
        raise ValueError('Add a managed Collection first')
    require_editable_animation(scene)
    linked = scene_collections(scene)
    for entry in entries:
        if not entry.collection:
            raise ValueError('A selected Collection was deleted; remove its missing entry first')
        if entry.collection not in linked:
            raise ValueError(f'{entry.collection.name} is no longer linked to this Scene; remove its entry')
        if entry.collection.library or entry.collection.override_library:
            raise ValueError('Linked or override Collections cannot be edited')
        if len(owners(entry.collection)) > 1:
            raise ValueError('Competing Scene owners detected; remove one binding before keying')


def selected_channels(scene):
    mode = scene.stageflip.channels
    return CHANNELS if mode == 'BOTH' else (mode.lower(),)


def insert_key(scene, entry, channel, visible):
    setattr(entry, channel + '_visible', bool(visible))
    ad = scene.animation_data_create()
    if not ad.action:
        action = bpy.data.actions.new('STAGEFLIP Visibility')
        slot = action.slots.new('SCENE', scene.name)
        ad.action = action
        ad.action_slot = slot
    bag = action_ensure_channelbag_for_slot(ad.action, ad.action_slot)
    fc = curve(scene, entry, channel)
    if fc is None:
        # Scene.keyframe_insert canonicalizes CollectionProperty paths to indices.
        # Direct native F-Curve creation preserves the UUID name lookup instead.
        fc = bag.fcurves.new(data_path=path(entry, channel),
                            group_name='STAGEFLIP / ' + entry.collection.name)
    fc.keyframe_points.insert(scene.frame_current_final, float(bool(visible)))
    fc.extrapolation = 'CONSTANT'
    for point in fc.keyframe_points:
        point.interpolation = 'CONSTANT'
    fc.update()
    fc.update_autoflags(scene)


def delete_key(scene, entry, channel):
    fc = curve(scene, entry, channel)
    if not fc:
        return False
    for point in fc.keyframe_points:
        if abs(point.co.x - scene.frame_current_final) < 1e-5:
            fc.keyframe_points.remove(point)
            fc.update()
            return True
    return False


def restore_entry(entry):
    c = entry.collection
    if not c or c.library or c.override_library or len(owners(c)) > 1:
        return
    for channel in CHANNELS:
        attr = 'hide_' + channel
        original = getattr(entry, 'original_' + channel + '_hidden')
        if getattr(c, attr) != original:
            setattr(c, attr, original)


def removal_has_animation(scene, entry):
    paths = {path(entry, ch) for ch in CHANNELS}
    # Include stashed Actions and every slot: removing an RNA binding would
    # invalidate those paths even when its Action is not currently active.
    for action in bpy.data.actions:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    if any(fc.data_path in paths for fc in bag.fcurves):
                        return True
    ad = scene.animation_data
    return bool(ad and any(fc.data_path in paths for fc in ad.drivers))


def remove(scene, index, *, confirm_delete_animation=False):
    entry = scene.stageflip.entries[index]
    paths = {path(entry, ch) for ch in CHANNELS}
    if removal_has_animation(scene, entry) and not confirm_delete_animation:
        raise ValueError('Removal deletes visibility animation. Confirm deletion in the Remove dialog')
    if scene.library or scene.override_library:
        raise ValueError('Use a local editable Scene for STAGEFLIP')
    ad = scene.animation_data
    # Reject removal when any matching curves would be left with invalid paths.
    for action in bpy.data.actions:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    if any(fc.data_path in paths for fc in bag.fcurves):
                        if (not ad or action != ad.action or bag.slot_handle != ad.action_slot_handle):
                            raise ValueError('Visibility keys exist in an inactive Action or another slot; retain this binding or remove those keys explicitly first')
    # Preserve unrelated Scene animation, including channels in other slots.
    if ad and ad.action:
        if ad.action.library or ad.action.override_library or action_is_shared(ad.action):
            raise ValueError('Make the Scene Action local and single-user before removing bindings')
        for layer in ad.action.layers:
            for strip in layer.strips:
                bag = strip.channelbag(ad.action_slot) if ad.action_slot else None
                if bag:
                    for fc in list(bag.fcurves):
                        if fc.data_path in paths:
                            bag.fcurves.remove(fc)
    if ad:
        for fc in list(ad.drivers):
            if fc.data_path in paths:
                ad.drivers.remove(fc)
    restore_entry(entry)
    scene.stageflip.entries.remove(index)
    scene.stageflip.active_index = max(0, min(index, len(scene.stageflip.entries) - 1))
