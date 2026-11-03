# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Cappuccino Digital.
"""Central Collection visibility evaluator.

No cached RNA references: undo/load can replace datablocks. Compare before writing.
"""
import logging
import bpy
from bpy.app.handlers import persistent
from . import storage

log = logging.getLogger(__package__)
_busy = False
_issues = {}
stats = {'evaluations': 0, 'writes': 0, 'load': 0, 'undo': 0, 'redo': 0}
TAG = 'cappuccino.stageflip.extension.v1'


def issue(scene):
    return _issues.get(scene.as_pointer(), '')


def set_issue(scene, message):
    identity = scene.as_pointer()
    previous = _issues.get(identity, '')
    if message:
        _issues[identity] = message
        if previous != message:
            log.warning('STAGEFLIP: %s', message)
    else:
        _issues.pop(identity, None)


def evaluate(scene):
    global _busy
    if _busy or not scene or not hasattr(scene, 'stageflip') or not scene.stageflip.entries:
        return
    _busy = True
    try:
        stats['evaluations'] += 1
        problem = storage.animation_problem(scene)
        if problem:
            set_issue(scene, problem)
            return
        warnings = []
        linked = storage.scene_collections(scene)
        ownership = storage.ownership_map()
        bag = storage.channelbag(scene)
        curves = {fc.data_path: fc for fc in bag.fcurves} if bag else {}
        for entry in scene.stageflip.entries:
            c = entry.collection
            if not c:
                warnings.append('A Collection was deleted. Remove its missing entry')
                continue
            if c not in linked or c.library or c.override_library:
                warnings.append(f'{c.name}: unavailable or read-only; visibility evaluation paused')
                continue
            if len(ownership.get(c, ())) > 1:
                warnings.append(f'{c.name}: competing Scene owners; visibility evaluation paused')
                continue
            for channel in storage.CHANNELS:
                fc = curves.get(storage.path(entry, channel))
                value = (fc.evaluate(scene.frame_current_final)
                         if fc and len(fc.keyframe_points) and not fc.mute
                         else getattr(entry, channel + '_visible'))
                hidden = value < 0.5
                attr = 'hide_' + channel
                if getattr(c, attr) != hidden:
                    setattr(c, attr, hidden)
                    stats['writes'] += 1
        set_issue(scene, '; '.join(dict.fromkeys(warnings)))
    except Exception as exc:
        # Handler exceptions must be visible in both the panel and the console.
        message = f'Visibility evaluation failed: {exc}'
        if issue(scene) != message:
            log.exception('STAGEFLIP evaluator failed')
        set_issue(scene, message)
    finally:
        _busy = False


@persistent
def frame_pre(scene, *args):
    evaluate(scene)


@persistent
def graph_post(scene, *args):
    evaluate(scene)


@persistent
def render_pre(scene, *args):
    evaluate(scene)


def reconcile(event):
    stats[event] += 1
    _issues.clear()
    evaluate(bpy.context.scene)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type in {'VIEW_3D', 'DOPESHEET_EDITOR', 'GRAPH_EDITOR'}:
                area.tag_redraw()


@persistent
def load_post(*args):
    reconcile('load')


@persistent
def undo_post(*args):
    reconcile('undo')


@persistent
def redo_post(*args):
    reconcile('redo')


HANDLERS = (('frame_change_pre', frame_pre), ('depsgraph_update_post', graph_post),
            ('render_pre', render_pre), ('load_post', load_post),
            ('undo_post', undo_post), ('redo_post', redo_post))
for _, fn in HANDLERS:
    fn._stageflip_handler_tag = TAG


def unregister():
    if bpy.app.timers.is_registered(_on_enable):
        bpy.app.timers.unregister(_on_enable)
    for name, _ in HANDLERS:
        callbacks = getattr(bpy.app.handlers, name)
        for fn in list(callbacks):
            if getattr(fn, '_stageflip_handler_tag', None) == TAG:
                callbacks.remove(fn)
    _issues.clear()


def register():
    unregister()
    for name, fn in HANDLERS:
        getattr(bpy.app.handlers, name).append(fn)
    # Blender restricts context/data access during extension register().
    # Reconcile at the next event-loop tick; load_post covers startup file load.
    bpy.app.timers.register(_on_enable, first_interval=0.0)


def _on_enable():
    evaluate(bpy.context.scene)
    return None
