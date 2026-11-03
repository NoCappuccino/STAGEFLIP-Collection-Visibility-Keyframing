# STAGEFLIP 1.0.0 - User Guide

**Made by Cappuccino Digital**

## One-click visibility keyframing

Open the 3D View sidebar with **N → STAGEFLIP**. Choose a local Collection linked
to the current Scene and click **Add**. At the first frame choose **Both** and
click **Hide + Key**; move to a later frame and click **Show + Key**. Each button
sets the channel value and inserts or updates its native constant key immediately.
A Show key extends backwards before the first key, so author an initial Hide when
needed. STAGEFLIP does not invent initial keys or durations.

## Channels and batch operations

**Viewport** affects Collection `hide_viewport` (monitor restriction), **Render**
affects `hide_render` (camera restriction), and **Both** authors the two independent
channels together. Checked rows are batch targets; with none checked, the highlighted
active row is the sole target. Select-all and clear controls manage the checkboxes.
Remove always acts on the highlighted row, irrespective of checked rows.

**Insert / Update** keys the current Scene channel property values at this frame;
it does not sample arbitrary Outliner changes. **Delete Key** deletes current-frame
keys only in the chosen channels/targets. Deleting a channel's final key retains
its current static value. The panel reports none, some, or all target channels
keyed. Monitor/camera indicators describe local Collection flags; they do not
promise effective visibility through all parents and View Layers.

## Playback and native editing

Scrub or play normally. Scene Action F-Curves store the animation under stable
`stageflip.entries["UUID"].viewport_visible` and `render_visible` paths.
Use the Dope Sheet or Graph Editor; turn off selection-only filtering to locate
Scene channels. Move/delete keys with native tools and use native Undo/Redo.
Use STAGEFLIP buttons for insertion: generic nested RNA insertion can create
numeric-index paths, which are not the supported UUID channels.

STAGEFLIP inserts constant interpolation and sets the target curve's key
interpolation to constant. It reads values below 0.5 as hidden and values at least
0.5 as visible. Manually authored interpolation/handles survive save and upgrade,
but subsequent STAGEFLIP insertion resets interpolation on that target curve.

## Removal and disable safety

**Remove** stops managing the highlighted Collection, restores its captured flags
and deletes its own active visibility curves. Animated bindings now require a
dialog with an explicit deletion checkbox. Cancel to preserve them. Unconfirmed
scripted removal is rejected too. Undo restores a completed removal. Bindings
with matching curves in inactive Actions or other slots cannot be removed until
you explicitly resolve those curves; this avoids invalidating retained animation.
Shared or read-only Actions are protected. Unrelated Scene channels are preserved.

Deleting a Collection through Blender leaves a missing managed row and its keys;
STAGEFLIP warns and skips it without automatically deleting animation. Removing
that row still requires confirmation if animated. Keep a backup before deliberate
animation deletion. Disabling the extension restores captured flags but retains
bindings and keys for re-enable. Playback/render evaluation requires it enabled.

## Blender limitations

Collection visibility flags are global across Scenes. Shared Collections warn;
second managed owners are blocked. Duplicating a Scene can create competing
bindings, which pause evaluation until resolved. Collections, objects, parents,
View Layer exclusions and local eye restrictions can still prevent visibility.
STAGEFLIP does not override these or write individual object flags.

Use local editable Scenes/Collections and a single-user active Scene Action with
one layer and one keyframe strip. NLA blending/tweak mode, STAGEFLIP drivers,
F-Curve modifiers, linked targets and overrides are unsupported. Evaluation pauses for unsupported animation;
resolve the warning before relying on playback or renders.

Render workers require the extension installed/enabled. Use **Lock Interface for
Rendering** for foreground renders. Concurrent multi-Scene rendering, macOS,
Linux, and Blender versions other than 5.2.3 are untested for this release.

Copyright 2026 Cappuccino Digital. GPL-3.0-or-later; see [LICENSE](LICENSE).
