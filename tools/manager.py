#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#
# Authors: Lester Carballo Pérez <lestcape@gmail.com>
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

import sys, os
from gi.repository import Gtk, Gdk, GObject
GObject.threads_init()

try:
    import urllib2
except:
    import urllib.request as urllib2

'''Important Constants'''
VERSION_FILE = "ver"
ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(os.path.dirname(ABS_PATH)) + "/"
sys.path.append(DIR_PATH + "lib")
sys.path.append(DIR_PATH + "installer_modules")
sys.path.append(DIR_PATH + "settings_modules")
Gtk.IconTheme.get_default().append_search_path(DIR_PATH + "gui/img")

import gettext, locale
import CApiInstaller
import ProxyGSettingsInstaller

LOCALE_PATH = DIR_PATH + "locale"
DOMAIN = "cinnamon-installer"
#locale.bindtextdomain(DOMAIN , LOCALE_PATH)
#locale.bind_textdomain_codeset(DOMAIN , "UTF-8")
#gettext.bindtextdomain(DOMAIN, LOCALE_PATH)
#gettext.bind_textdomain_codeset(DOMAIN , "UTF-8")
#gettext.textdomain(DOMAIN)
#_ = gettext.gettext

# i18n
gettext.install("cinnamon", "/usr/share/locale")

import cs_installer

class MainApp():
    """Graphical Manager for Cinnamon Installer"""

    def __init__(self):
        ps = ProxyGSettingsInstaller.get_proxy_settings()
        if ps:
            proxy = urllib2.ProxyHandler(ps)
        else:
            proxy = urllib2.ProxyHandler()
        urllib2.install_opener(urllib2.build_opener(proxy))
        self.currentVersion = self.readVersionFromFile(DIR_PATH + VERSION_FILE)
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(DOMAIN)
        self.builder.add_from_file(DIR_PATH + "gui/mainManager.ui")
        self.mainWindow = self.builder.get_object("main_window")
        self.content_box = self.builder.get_object("content_box")
        self.mainWindow.connect("destroy", self.closeWindows)
        self.loop = GObject.MainLoop()
        self.c_manager = CApiInstaller.CManager()
        self.content_box.c_manager = self.c_manager
        self.installer = cs_installer.Module(self.content_box)
        self.installer._setParentRef(self.mainWindow, self.builder)

    def show(self):
        #self.mainWindow.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
        #self.refresh()
        self.mainWindow.show_all()
        self.installer.sidePage.build()
        self.loop.run()

    def _on_clicked_cancelButton(self, button, transaction):
        self.loop.quit()

    def closeWindows(self, windows):
        self.loop.quit()

    def refresh(self, force_update = False):
        while Gtk.events_pending():
            Gtk.main_iteration()
        while Gtk.events_pending():
            Gtk.main_iteration()

    def _custom_dialog(self, dialog_type, title, message):
        '''
        This is a generic Gtk Message Dialog function.
        dialog_type = this is a Gtk type.
        '''
        dialog = Gtk.MessageDialog(self.mainWindow, 0, dialog_type,
            Gtk.ButtonsType.OK, "")
        dialog.set_markup("<b>%s</b>" % title)
        dialog.format_secondary_markup(message)
        dialog.run()
        dialog.destroy()

    def _question_dialog(self, title, message):
        '''
        This is a generic Gtk Message Dialog function
        for questions.
        '''
        dialog = Gtk.MessageDialog(self.mainWindow, 0, Gtk.MessageType.QUESTION,
            Gtk.ButtonsType.YES_NO, "")
        dialog.set_markup("<b>%s</b>" % title)
        dialog.format_secondary_markup(message)
        response = dialog.run()
        dialog.destroy()
        return response

    def readVersionFromFile(self, path):
        try:
            if os.path.isfile(path):
                infile = open(path, "r")
                result = infile.readline().rstrip("\r\n")
                float(result) #Test info
                return result
        except Exception:
            pass
        return "0.0"

if __name__ == '__main__':
    main = MainApp()
    main.show()
