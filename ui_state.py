# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Cappuccino Digital.
"""Transient presentation feedback. Never stored with Scene animation data."""
import bpy
from bpy.props import EnumProperty, StringProperty


class STAGEFLIP_PG_feedback(bpy.types.PropertyGroup):
    message: StringProperty(options={'SKIP_SAVE'})
    level: EnumProperty(items=[('INFO', 'Success', ''), ('WARNING', 'Notice', ''),
                               ('ERROR', 'Error', '')], default='INFO', options={'SKIP_SAVE'})


def notify(operator, context, message, level='INFO'):
    feedback = context.window_manager.stageflip_feedback
    feedback.message = message
    feedback.level = level
    operator.report({level}, message)


CLASSES = (STAGEFLIP_PG_feedback,)
