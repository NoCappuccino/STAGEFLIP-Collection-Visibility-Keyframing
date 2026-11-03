# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Cappuccino Digital.
"""Persistent, versioned Scene storage. Entry names are stable animation IDs."""
import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       IntProperty, PointerProperty)


def candidate_poll(self, collection):
    from .storage import scene_collections
    return (not collection.library and not collection.override_library
            and collection in scene_collections(self.id_data))


class STAGEFLIP_PG_entry(bpy.types.PropertyGroup):
    collection: PointerProperty(type=bpy.types.Collection, name="Collection")
    selected: BoolProperty(name="Select for Keying", description="Include this Collection in batch keys; with no checks, keys use the highlighted active row", default=False)
    viewport_visible: BoolProperty(name="Viewport Visible", default=True)
    render_visible: BoolProperty(name="Render Visible", default=True)
    original_viewport_hidden: BoolProperty(default=False, options={'HIDDEN'})
    original_render_hidden: BoolProperty(default=False, options={'HIDDEN'})


class STAGEFLIP_PG_settings(bpy.types.PropertyGroup):
    schema_version: IntProperty(default=1, options={'HIDDEN'})
    entries: CollectionProperty(type=STAGEFLIP_PG_entry)
    active_index: IntProperty(name="Active Collection", default=0, min=0)
    candidate: PointerProperty(type=bpy.types.Collection, name="Collection", poll=candidate_poll,
                               description="Choose a local Collection linked to this Scene")
    channels: EnumProperty(name="Channels", items=[
        ('BOTH', 'Both', 'Key viewport and render visibility independently'),
        ('VIEWPORT', 'Viewport', 'Key viewport visibility only'),
        ('RENDER', 'Render', 'Key render visibility only')], default='BOTH')


CLASSES = (STAGEFLIP_PG_entry, STAGEFLIP_PG_settings)
