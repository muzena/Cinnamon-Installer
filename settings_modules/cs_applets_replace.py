#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Cinnamon Installer
#
# Authors: Lester Carballo Pérez <lestcape@gmail.com>
# Froked from Cinnamon code at:
# https://github.com/linuxmint/Cinnamon
#
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

from gi.repository import GObject
from ExtensionInstallerCore import ExtensionSidePage

class Module:
    def __init__(self, content_box):
        keywords = _("applet")
        self.name = "applets"       
        self.comment = _("Manage Cinnamon applets")
        sidePage = AppletsViewSidePage(_("Applets"), "cs-applets", keywords, content_box, "applet", self)
        self.sidePage = sidePage
        self.category = "prefs"

    def on_module_selected(self):
        if not self.loaded:
            print("Loading Applets module")
            self.sidePage.load()
        #GObject.idle_add(self.refresh_windows)

    def refresh_windows(self):
        width, height = self.sidePage.window.get_size()
        self.sidePage.window.resize(width + 1, height + 1)

    def _setParentRef(self, window, builder):
        self.sidePage.window = window
        self.sidePage.builder = builder

class AppletsViewSidePage (ExtensionSidePage):
    def __init__(self, name, icon, keywords, content_box, collection_type, module):
        self.RemoveString = _("You can remove specific instances in panel edit mode via the context menu.")
        ExtensionSidePage.__init__(self, name, icon, keywords, content_box, collection_type, module)

    def toSettingString(self, uuid, instanceId):
        return ("panel1:right:0:%s:%d") % (uuid, instanceId)

    def fromSettingString(self, string):
        panel, side, position, uuid, instanceId = string.split(":")
        return uuid

    def getAdditionalPage(self):
        return None
