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

from ExtensionInstallerCore import ExtensionSidePage
from gi.repository import GObject, Gtk
from SettingsInstallerWidgets import *

class Module:
    def __init__(self, content_box):
        keywords = _("desklet, desktop, slideshow")
        self.name = "desklets"
        self.comment = _("Manage your Cinnamon desklets")       
        sidePage = DeskletsViewSidePage(_("Desklets"), "cs-desklets", keywords, content_box, "desklet", self)
        self.sidePage = sidePage
        self.category = "prefs"

    def on_module_selected(self):
        if not self.loaded:
            print("Loading Desklets module")
            self.sidePage.load()
        #GObject.idle_add(self.refresh_windows)

    def refresh_windows(self):
        width, height = self.sidePage.window.get_size()
        self.sidePage.window.resize(width + 1, height + 1)

    def _setParentRef(self, window, builder):
        self.sidePage.window = window
        self.sidePage.builder = builder

class DeskletsViewSidePage (ExtensionSidePage):
    def __init__(self, name, icon, keywords, content_box, collection_type, module):
        self.RemoveString = _("You can remove specific instances from the desktop via that desklet's context menu")
        ExtensionSidePage.__init__(self, name, icon, keywords, content_box, collection_type, module)

    def toSettingString(self, uuid, instanceId):
        return ("%s:%d:0:100") % (uuid, instanceId)

    def fromSettingString(self, string):
        uuid, instanceId, x, y = string.split(":")
        return uuid

    def getAdditionalPage(self):
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.label = Gtk.Label.new(_("General Desklets Settings"))
        config_vbox = Gtk.VBox()
        scrolled_window.add_with_viewport(config_vbox)
        config_vbox.set_border_width(5)

        dec = [[0, _("No decoration")], [1, _("Border only")], [2, _("Border and header")]]
        dec_combo = GSettingsIntComboBox(_("Decoration of desklets"), "org.cinnamon", "desklet-decorations", None, dec)

        label = Gtk.Label()
        label.set_markup("<i><small>%s\n%s</small></i>" % (_("Note: Some desklets require the border/header to be always present"), _("Such requirements override the settings selected here")))
        label.set_alignment(0.1,0)
        

        desklet_snap = GSettingsCheckButton(_("Snap desklets to grid"), "org.cinnamon", "desklet-snap", None)
        desklet_snap_interval = GSettingsSpinButton(_("Width of desklet snap grid"), "org.cinnamon", "desklet-snap-interval", "org.cinnamon/desklet-snap", 0, 100, 1, 5, "")

        config_vbox.pack_start(dec_combo, False, False, 2)
        config_vbox.pack_start(label, False, False, 2)
        config_vbox.pack_start(desklet_snap, False, False, 2)
        config_vbox.pack_start(desklet_snap_interval, False, False, 2)

        return scrolled_window
