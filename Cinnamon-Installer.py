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

import os, argparse, sys, gettext
from gi.repository import Gtk, Gdk, GObject, GLib

MODULES = 'systemInstaller'
ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"
sys.path.append(DIR_PATH + MODULES)

_ = lambda msg: gettext.dgettext("aptdaemon", msg)

WEB_SITE_URL = "https://github.com/lestcape/Cinnamon-Installer"

try:
    import aptInstaller as Installer
    IMPORTER = True
except ImportError:
    IMPORTER = False

class MainApp():
    """Graphical progress for installation/fetch/operations.

    This widget provides a progress bar, a terminal and a status bar for
    showing the progress of package manipulation tasks.
    """

    def __init__(self):
        self.interface = Gtk.Builder()
        self.interface.set_translation_domain('cinnamon-installer')
        self.interface.add_from_file(DIR_PATH + 'gui/main.ui')
        self._mainWindow = self.interface.get_object('Installer')
        self._appNameLabel = self.interface.get_object('appNameLabel')
        #self._mainWindow.connect("delete-event", self.closeWindows)

    def show(self):
        self._mainWindow.show()
        self._mainWindow.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
        self.refresh()
        Gtk.main()

    def closeWindows(self, windows, event):
        Gtk.main_quit()

    def refresh(self, force_update = False):
	while Gtk.events_pending():
	    Gtk.main_iteration()
	while Gtk.events_pending():
	    Gtk.main_iteration()
	#Refresh(force_update)

def startGUI(install, packageName):
    mainAppWindows = MainApp()
    mainWind = Installer.ControlWindow(mainAppWindows)
    if(install):
        mainAppWindows._mainWindow.set_title(_("Cinnamon Installer"))
        mainAppWindows._appNameLabel.set_text(_("Cinnamon Installer"))
        mainWind.preformInstall(packageName);
    else:
        mainAppWindows._mainWindow.set_title(_("Cinnamon Uninstaller"))
        mainAppWindows._appNameLabel.set_text(_("Cinnamon Uninstaller"))
        mainWind.preformUninstall(packageName);

def findPackageForProgram(program):
    path = GLib.find_program_in_path(program);
    print path
    packageName = Installer.findPackageByPath(path);
    print packageName
    return packageName

def printPackageByName(packageName):
    listPackage = Installer.searchUnistalledPackages(packageName)
    for p in listPackage:
       print p.name
    return len(listPackage) > 0

def _custom_dialog(dialog_type, title, message):
    '''
    This is a generic Gtk Message Dialog function.
    dialog_type = this is a Gtk type.
    '''
    dialog = Gtk.MessageDialog(None, 0, dialog_type,
        Gtk.ButtonsType.OK, "")
    dialog.set_markup("<b>%s</b>" % title)
    dialog.format_secondary_markup(message)
    dialog.run()
    dialog.destroy()

def validateImport(arg):
    if IMPORTER:
        resultOk = True
        if arg == "cinnamon":
            try:
                resultOk = printPackageByName("cinnamon")
                if not resultOk:
                    title = "Can not find any Cinnamon package on your system."
                    message = "You are using Cinnamon desktop?"
                    _custom_dialog(Gtk.MessageType.INFO, title, message)
            except Exception:
                resultOk = False
                title = "Some unexpected problem has occurred."
                message = "Your Linux distribution is supported, but this can be a bug.\n" + \
                          "If you want to contribute to fix the problem,\n" + \
                          "please visit: <a href='" + WEB_SITE_URL + "'>" + \
                          "Cinnamon Installer</a>." 
                _custom_dialog(Gtk.MessageType.ERROR, title, message)
        if resultOk:
            print "run"
            title = "Appear that the application can run on your OS."
            message = "If you detect any problem or want to contribute,\n" + \
                      "please visit: <a href='" + WEB_SITE_URL + "'>" + \
                      "Cinnamon Installer</a>."
            _custom_dialog(Gtk.MessageType.INFO, title, message)
    else:
        print "error"
        title = "Imposible to run Cinnamon Installer on your OS."
        message = "Your Linux distribution is unsupported or missing some packages.\n" + \
                  "If you want to contribute to fix the problem,\n" + \
                  "please visit: <a href='" + WEB_SITE_URL + "'>" + \
                  "Cinnamon Installer</a>." 
        _custom_dialog(Gtk.MessageType.ERROR, title, message)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process the installer options.')
    group_action = parser.add_mutually_exclusive_group(required=True)
    group_action.add_argument('--ipackage', nargs='?', action='store', type=str, help='Install package by name')
    group_action.add_argument('--upackage', nargs='?', action='store', type=str, help='Uninstall package by name')
    group_action.add_argument('--uprogram', nargs='?', action='store', type=str, help='Uninstall program by name')
    group_action.add_argument('--qpackage', nargs='?', action='store', type=str, help='Query package by name')
    group_action.add_argument('--qtest', nargs='?', action='store', type=str, help='Query for (imports / cinnamon)')
    args = parser.parse_args()
    if(args.qtest):
       validateImport(args.qtest)
    elif(args.ipackage):
       startGUI(True, args.ipackage)
    elif(args.upackage):
       startGUI(False, args.upackage)
    elif(args.uprogram):
       packageName = findPackageForProgram(args.uprogram)
       startGUI(False, packageName)
    elif(args.qpackage):
       printPackageByName(args.qpackage)
