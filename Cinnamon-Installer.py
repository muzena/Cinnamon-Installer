#! /usr/bin/python3
# -*- coding: utf-8 -*-
#
# Cinnamon Installer
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

__author__ = "Lester Carballo <lestcape@gmail.com>" 

import os, argparse, sys
from gi.repository import Gtk, Gdk, GObject, GLib
GObject.threads_init()

MODULES = 'systemInstaller'
ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"
sys.path.append(DIR_PATH + MODULES)

Gtk.IconTheme.get_default().append_search_path(DIR_PATH + "gui/img")

import gettext, locale
LOCALE_PATH = DIR_PATH + 'locale'
DOMAIN = 'cinnamon-installer'
locale.bindtextdomain(DOMAIN , LOCALE_PATH)
locale.bind_textdomain_codeset(DOMAIN , 'UTF-8')
gettext.bindtextdomain(DOMAIN, LOCALE_PATH)
gettext.bind_textdomain_codeset(DOMAIN , 'UTF-8')
gettext.textdomain(DOMAIN)
_ = gettext.gettext

WEB_SITE_URL = "https://github.com/lestcape/Cinnamon-Installer"

importerError = []
try:
    import aptInstaller as Installer
except ImportError as e:
    importerError.append(e)
    try:
        import pacInstaller as Installer
        importerError = []
    except ImportError as e:
        print("error " + str(e))
        importerError.append(e)

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
        self._cancelButton = self.interface.get_object('cancelButton')
        self._closeButton = self.interface.get_object('closeButton')
        self._terminalExpander = self.interface.get_object('terminalExpander')
        self._terminalTextView = self.interface.get_object('terminalTextView')
        self._terminalScrolled = self.interface.get_object('terminalScrolledWindow')
        self._terminalBox = self.interface.get_object('terminalBox')

        self._progressBar = self.interface.get_object('progressBar')
        self._roleLabel = self.interface.get_object('roleLabel')
        self._statusLabel = self.interface.get_object('statusLabel')
        self._actionImage = self.interface.get_object('actionImage')
        self._sumTopLabel = self.interface.get_object('sum_top_label')
        self._sumBottomLabel = self.interface.get_object('sum_bottom_label')

        self._errorDialog = self.interface.get_object('ErrorDialog')
        self._confDialog = self.interface.get_object('ConfDialog')
        self._warningDialog = self.interface.get_object('WarningDialog')
        self._chooseDialog = self.interface.get_object('ChooseDialog')
        self._preferencesWindow = self.interface.get_object('PreferencesWindow')

        self._transactionSum = self.interface.get_object('transaction_sum')

        self._chooseLabel = self.interface.get_object('choose_label')
        self._chooseList = self.interface.get_object('choose_list')
        self._chooseRendererToggle = self.interface.get_object('choose_renderertoggle')
        self._enableAURButton = self.interface.get_object('EnableAURButton')
        self._removeUnrequiredDepsButton = self.interface.get_object('RemoveUnrequiredDepsButton')
        self._refreshPeriodSpinButton = self.interface.get_object('RefreshPeriodSpinButton')
        #RefreshPeriodLabel = interface.get_object('RefreshPeriodLabel')
        #self._mainWindow.connect("delete-event", self.closeWindows)

    def show(self):
        self._mainWindow.show()
        self._mainWindow.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
        #self.refresh()
        Gtk.main()

    def closeWindows(self, windows, event):
        Gtk.main_quit()

    def refresh(self, force_update = False):
        while Gtk.events_pending():
            Gtk.main_iteration()
        while Gtk.events_pending():
            Gtk.main_iteration()
        #Refresh(force_update)

def readVersionFromFile():
    try:
        path = DIR_PATH + "ver"
        if os.path.isfile(path):
            infile = open(path, 'r')
            result = infile.readline().rstrip('\r\n')
            float(result) #Test info
            return result
    except Exception:
        pass
    return "0.0"

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
    if path is not None:
        print("Program " + program + " was find in path:" + path)
        packageName = Installer.findPackageByPath(path);
        if packageName is not None:
            print("Program " + program + " was find in package:" + packageName)
            return packageName
    return ""

def printPackageByName(packageName):
    listPackage = []
    try:
       listPackage = Installer.searchUnistalledPackages(packageName)
       for p in listPackage:
          print(p.name)
    except Exception as e:
       return str(e)
    if len(listPackage) == 0:
       return packageName
    return "run"
    

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

def tryUninstall(program):
    packageName = findPackageForProgram(program)
    if packageName != "":
        startGUI(False, packageName)
    else:
        title = _("Not found any package associated with the program '%s'.") % program
        message = _("If you detect any problem or you want to contribute,\n" + \
                  "please visit: <a href='%s'>Cinnamon Installer</a>.") % WEB_SITE_URL
        _custom_dialog(Gtk.MessageType.INFO, title, message)

def validateImport(arg):
    ver = "?"
    try:
        ver = readVersionFromFile()
        if len(importerError) == 0:
            if (arg == "package")or(arg == "install"):
                if (arg == "package") and (findPackageForProgram("cinnamon-settings") != "cinnamon"):
                    print("error")
                    title = _("<i>Cinnamon Installer %s</i>, can not find any Cinnamon package on your system.") % ver
                    message = _("You are using Cinnamon desktop?")
                    _custom_dialog(Gtk.MessageType.INFO, title, message)
                if (Installer.configure()):
                    print("run")
                    title = _("Appear that <i>Cinnamon Installer %s</i> can run on your OS.") % ver
                    message = _("If you detect any problem or you want to contribute,\n" + \
                             "please visit: <a href='%s'>Cinnamon Installer</a>.") % WEB_SITE_URL
                    _custom_dialog(Gtk.MessageType.INFO, title, message)
                else:
                    print("error")
                    title = _("You need to install <i>Cinnamon Installer %s</i> for the first used.") % ver
                    message = _("Appear that your Linux distribution is supported.\n" +\
                              "If you detect any problem or you want to contribute,\n" + \
                              "please visit: <a href='%s'>Cinnamon Installer</a>.") % WEB_SITE_URL
                    _custom_dialog(Gtk.MessageType.INFO, title, message)
        else:
            print("error")
            title = _("Imposible to run <i>Cinnamon Installer %s</i> on your OS.") % ver
            message = _("Your Linux distribution is unsupported or are missing some packages.\n" + \
                      "If you want to contribute to fix the problem, please visit:\n" + \
                      "<a href='%s'>Cinnamon Installer</a>.\n\n") % WEB_SITE_URL

            message += _("<i><u>Error Message:</u></i>")
            for error in importerError:
                message += "\n" + str(error)
 
            _custom_dialog(Gtk.MessageType.ERROR, title, message)
    except Exception as e:
        print(str(e))
        title = _("Some unexpected problem has occurred on <i>Cinnamon Installer %s</i>.") % ver
        message = _("Appear that your Linux distribution is unsupported.\n" +\
                  "If you want to contribute to fix the problem,\n" + \
                  "please visit: <a href='%s'>Cinnamon Installer</a>.\n\n") % WEB_SITE_URL

        _custom_dialog(Gtk.MessageType.ERROR, title, message)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=_("Process the installer options."))
    group_action = parser.add_mutually_exclusive_group(required=True)
    group_action.add_argument('--ipackage', nargs='?', action='store', type=str, help=_("Install package by name"))
    group_action.add_argument('--upackage', nargs='?', action='store', type=str, help=_("Uninstall package by name"))
    group_action.add_argument('--uprogram', nargs='?', action='store', type=str, help=_("Uninstall program by name"))
    group_action.add_argument('--qpackage', nargs='?', action='store', type=str, help=_("Query package by name"))
    group_action.add_argument('--qtest', nargs='?', action='store', type=str, help=_("Query for (imports/cinnamon/install)"))
    args = parser.parse_args()
    if(args.qtest):
        validateImport(args.qtest)
    elif(args.ipackage):
        startGUI(True, args.ipackage)
    elif(args.upackage):
        startGUI(False, args.upackage)
    elif(args.uprogram):
        tryUninstall(args.uprogram)
    elif(args.qpackage):
        printPackageByName(args.qpackage)
