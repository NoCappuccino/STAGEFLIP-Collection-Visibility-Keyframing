# STAGEFLIP 1.0.0 — Installation

**Made by Cappuccino Digital**

## Fresh installation

1. Use Blender 5.2.3 LTS. Keep `stageflip_v1.0.0.zip` zipped.
2. Open **Edit → Preferences → Get Extensions**, then choose **Install from Disk**
   from the menu. Select the ZIP and enable STAGEFLIP.
3. Save Preferences if automatic preference saving is disabled.
4. In the 3D View press **N** and open **STAGEFLIP**.
5. The footer shows **STAGEFLIP 1.0.0** and **Made by Cappuccino Digital**.

This is a Blender extension archive with its manifest at the archive root.
The ZIP contains all runtime source and documentation; no separate dependency
installation or online account is needed.

## Upgrade

Back up your projects before upgrading. Install the new ZIP into the same
extension repository as the existing installation, save Preferences, and restart
Blender. Avoid duplicate installations across repositories. Existing bindings and
native key paths are retained, with no migration or automatic animation cleanup.

## Disable and uninstall

Disable STAGEFLIP in **Preferences → Add-ons**. Disabling restores the Collection
flags captured when each Collection was added. Bindings and animation keys remain
in the project for re-enable. Uninstall through Preferences when required.

Disabling/uninstalling does not bake the animation: playback and rendered
visibility require STAGEFLIP enabled. If saving a changed project for delivery,
use a separate copy. Reinstall and enable STAGEFLIP to resume evaluation.

## Rendering

Install and enable STAGEFLIP in each render worker's profile and save Preferences.
Opening a .blend alone does not install or enable its extensions.
For foreground renders, enable **Options & Help → Lock Interface for Rendering**.

## Platform coverage and license

Tested on Windows x64 with Blender 5.2.3 LTS. macOS, Linux and other Blender
versions are untested. See [USER_GUIDE.md](USER_GUIDE.md) for supported animation
and visibility limitations.

Copyright 2026 Cappuccino Digital. GPL-3.0-or-later; see [LICENSE](LICENSE).
