#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#
# Authors: Lester Carballo Pérez <lestcape@gmail.com>
#
# Froked from Cinnamon code at:
# https://github.com/linuxmint/Cinnamon
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
#  USA

from __future__ import print_function

import sys

try:
    import os
    import shutil
except Exception:
    e = sys.exc_info()[1]
    print(str(e))
    sys.exit(1)

PATH_INSTALLER_MODULES = "/usr/lib/cinnamon-settings/installer_modules"
PATH_MODULES = "/usr/lib/cinnamon-settings/modules/"
PATH_BIN = "/usr/lib/cinnamon-settings/bin/"
PATH_ICONS = "/usr/share/icons/hicolor/scalable/categories/"

MODULES = ["cs_installer.py"]
LIBS = ["ExtensionInstallerCore.py", "XletInstallerSettings.py", "XletInstallerSettingsWidgets.py", "XletInstallerModules.py"]
BUILDERS = ["manager.ui"]
ICONS = ["cs-cinnamon-installer.svg"]


if os.path.exists(PATH_INSTALLER_MODULES):
   shutil.rmtree(PATH_INSTALLER_MODULES)

for module in MODULES:
    out = os.path.join(PATH_MODULES, module)
    if os.path.isfile(out):
        os.remove(out)
    out = os.path.join(PATH_MODULES, module + "c")
    if os.path.isfile(out):
        os.remove(out)

for lib in LIBS:
    out = os.path.join(PATH_BIN, lib)
    if os.path.isfile(out):
        os.remove(out)
    out = os.path.join(PATH_BIN, lib + "c")
    if os.path.isfile(out):
        os.remove(out)

for builder in BUILDERS:
    out = os.path.join(PATH_BIN, builder)
    if os.path.isfile(out):
        os.remove(out)

for icon in ICONS:
    out = os.path.join(PATH_ICONS + icon)
    if os.path.isfile(out):
        os.remove(out)

#now test that
#os.system("python /usr/lib/cinnamon-settings/cinnamon-settings.py")
#os.system("python /usr/lib/cinnamon-settings/cinnamon-settings.py applets configurableMenu@lestcape configurableMenu@lestcape")

