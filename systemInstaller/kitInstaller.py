#! /usr/bin/python3
# -*- coding: utf-8 -*-
#
# Cinnamon Installer
#
# Authors: Lester Carballo Pérez <lestcape@gmail.com>
#
# Original version from: PackageKit
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

from gi.repository import PackageKitGlib as packagekit
from gi.repository import GObject, Gtk, GLib

# uncomment to use GTK 2.0
#import gi
#gi.require_version('Gtk', '2.0')

import os, subprocess, sys, stat
from time import sleep

MODULES = 'lib'
ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"
sys.path.append(DIR_PATH + MODULES)

import transactionkit

# i18n
import gettext, locale
LOCALE_PATH = DIR_PATH + 'locale'
DOMAIN = 'cinnamon-installer'
locale.bindtextdomain(DOMAIN , LOCALE_PATH)
locale.bind_textdomain_codeset(DOMAIN , 'UTF-8')
gettext.bindtextdomain(DOMAIN, LOCALE_PATH)
gettext.bind_textdomain_codeset(DOMAIN , 'UTF-8')
gettext.textdomain(DOMAIN)
_ = gettext.gettext

def configure():
    return True

def findPackageByPath(path):
    try:
        client = packagekit.Client();
        print(path)
        result = client.search_files(packagekit.FilterEnum.INSTALLED, [path,], None, progress_cb, None)
        pkgs = result.get_package_array()
        if ((pkgs) and (len(pkgs) > 0)):
           return pkgs[0].get_name()
    except GLib.GError as e:
        print(e)

    return None

def searchUnistalledPackages(pattern):
    try:
        client = packagekit.Client();
        unInstalledPackages = []
        result = client.search_names(packagekit.FilterEnum.NONE, [pattern,], None, progress_cb, None);
        pkgs = result.get_package_array()
        if pkgs:
            for pkg in pkgs:
                if ((not (pkg.get_name() in unInstalledPackages)) and (not (_isVersionInstalled(pkg.get_name(), pkgs)))):
                    unInstalledPackages.append(pkg.get_name())
    except GLib.GError as e:
        print(e)
    return unInstalledPackages

def progress_cb(status, typ, data=None):
    pass
    #if status.get_property('package'):
        #print "Pachet ", status.get_property('package'), status.get_property('package-id')
        #if status.get_property('package'):
            #print status.get_property('package').get_name()
    #print typ, status.get_property('package')

def _isVersionInstalled(name, pkgs):
    for pkg in pkgs:
        if (pkg.get_name() == name) and (pkg.get_info() == packagekit.InfoEnum.INSTALLED):
            return True
    return False

class ControlWindow(object):
    def __init__(self, mainApp):
        self.mainApp = mainApp
        self.trans = transactionkit.Transaction(self.mainApp)
        '''Begin PackageKit'''
        self.signals = {'on_ChooseButton_clicked' : self.trans.on_ChooseButton_clicked,
                        'on_progress_textview_size_allocate' : self.trans.on_progress_textview_size_allocate,
                        'on_choose_renderertoggle_toggled'   : self.trans.on_choose_renderertoggle_toggled,
                        'on_PreferencesCloseButton_clicked'  : self.trans.on_PreferencesCloseButton_clicked,
                        'on_PreferencesWindow_delete_event'  : self.trans.on_PreferencesWindow_delete_event,
                        'on_PreferencesValidButton_clicked'  : self.trans.on_PreferencesValidButton_clicked,
                        'on_TransValidButton_clicked'    : self.on_TransValidButton_clicked,
                        'on_TransCancelButton_clicked'   : self.on_TransCancelButton_clicked,
                        'on_ProgressCloseButton_clicked' : self.on_ProgressCloseButton_clicked,
                        'on_ProgressCancelButton_clicked': self.on_ProgressCancelButton_clicked}

    def preformUninstall(self, packageName):
        '''if (os.geteuid() != 0):
            if (not reloadAsRoot(["--upackage", packageName])):
                print("fail on install:" + str(packageName))
            else:
                print("reload as root")
        else:
        '''
        print("uninstall: " + str(packageName))
        self.trans.mainApp._roleLabel.set_text("Uninstall: " + str(packageName))
        self.trans.mainApp.interface.connect_signals(self.signals)
        self.trans.config_signals()
        self.config_signals()
        self.transaction_done = False
        result = []
        self.mainApp._mainWindow.show_all()
        if self.get_pkgs_remove([packageName]):
            self.prepare_transaction([packageName])
        Gtk.main()

    def preformInstall(self, packageName):
        '''if (os.geteuid() != 0):
            if (not reloadAsRoot(["--ipackage", packageName])):
                print("fail on install:" + str(packageName))
            else:
                print("reload as root")
        else:
        '''
        print("install:" + str(packageName))
        self.trans.mainApp._roleLabel.set_text("Install: " + str(packageName))
        self.trans.mainApp.interface.connect_signals(self.signals)
        self.trans.config_signals()
        self.config_signals()
        self.transaction_done = False
        result = []
        self.mainApp._mainWindow.show_all()
        if self.get_pkgs_install([packageName]):
            self.prepare_transaction([packageName])
        Gtk.main()

    def prepare_transaction(self, pkgs):
        self.trans.action_handler(None, _('Preparing')+'...')
        self.trans.icon_handler(None, 'package-setup.png')
        self.updateGtk()
        error = self.trans.prepare_transaction()
        self.updateGtk()
        if error:
            self.handle_error(None, error)

    def get_pkgs_remove(self, pkgs):
        liststore = Gtk.ListStore(object)
        self.trans.to_remove = []
        result = self.trans.get_local_packages(pkgs)
        notFound = []
        for name in pkgs:
            if not name in result:
                notFound.append(name)
            else:
                self.trans.to_remove.append(name)

        for name in notFound:
            error = _('{pkgname} is not a valid path or package name').format(pkgname = name)
            self.handle_error(None, error)

        if len(self.trans.to_remove) > 0:
            return True
        return False

    def get_pkgs_install(self, pkgs):
        liststore = Gtk.ListStore(object)
        self.trans.to_add = []
        result = self.trans.get_remote_packages(pkgs)
        notFound = []
        for name in pkgs:
            if not name in result:
                notFound.append(name)
            else:
                self.trans.to_add.append(name)

        for name in notFound:
            error = _('The package {pkgname} is already installed').format(pkgname = name)
            self.handle_error(None, error)

        if len(self.trans.to_add) > 0:
            return True
        return False

    def exec_transaction(self):
        error = self.trans.commit()
        if(error):
            self.handle_error(None, error) 
            

    '''Begin PackageKit'''
    def _on_expanded(self, expander, param):
        # Make the dialog resizable if the expander is expanded
        # try to restore a previous size
        if not expander.get_expanded():
            self._expanded_size = (self.terminal.get_visible(),
                                   self.mainWindow.get_size())
            self.mainWindow.set_resizable(False)
        elif self._expanded_size:
            self.mainWindow.set_resizable(True)
            term_visible, (stored_width, stored_height) = self._expanded_size
            # Check if the stored size was for the download details or
            # the terminal widget
            if term_visible != self.terminal.get_visible():
                # The stored size was for the download details, so we need
                # get a new size for the terminal widget
                self._resize_to_show_details()
            else:
                self.mainWindow.resize(stored_width, stored_height)
        else:
            self.mainWindow.set_resizable(True)
            self._resize_to_show_details()

    def _resize_to_show_details(self):
        win_width, win_height = self.mainWindow.get_size()
        exp_width = self.expander.get_allocation().width
        exp_height = self.expander.get_allocation().height
        if self.terminal and self.terminal.get_visible():
            terminal_width = self.terminal.get_char_width() * 80
            terminal_height = self.terminal.get_char_height() * 24
            self.mainWindow.resize(terminal_width - exp_width ,
                               terminal_height - exp_height )
        else:
            print(str(win_height))
            self.mainWindow.resize(win_width + 100, win_height)

    def _on_status_changed(self, trans, status):
        # Also resize the window if we switch from download details to
        # the terminal window
        print(status)
        #if (status == STATUS_COMMITTING and self.terminal and 
        #        self.terminal.get_visible()):
        #    self._resize_to_show_details()

    def exiting(self, msg):
        print(msg)
        Gtk.main_quit()

    def handle_error(self, obj, error):
        GObject.idle_add(self.show_Error, (error))
        sleep(0.1)

    def handle_reply(self, obj, replay):
        GObject.idle_add(self.exec_replay, (replay,))
        sleep(0.1)

    def handle_updates(self, obj, syncfirst, updates):
        #GObject.idle_add(self.exec_update, (syncfirst, updates,))
        sleep(0.1)

    def show_Error(self, error):
        self.trans.mainApp._mainWindow.hide()
        self.updateGtk()
        if error:
            self.trans.mainApp._errorDialog.format_secondary_text(error)
            response = self.trans.mainApp._errorDialog.run()
            if response:
                self.trans.mainApp._errorDialog.hide()
        self.exiting(error)

    def exec_replay(self, reply):
        self.trans.mainApp._closeButton.set_visible(True)
        self.trans.mainApp._actionImage.set_from_icon_name('dialog-information', Gtk.IconSize.BUTTON)
        self.trans.mainApp._roleLabel.set_text(str(reply))
        self.trans.mainApp._statusLabel.set_text(str(reply))
        self.trans.mainApp._progressBar.set_text('')
        end_iter = self.trans._terminalTextBuffer.get_end_iter()
        self.trans._terminalTextBuffer.insert(end_iter, str(reply))
        self.updateGtk()

    def on_TransValidButton_clicked(self, *args):
        GObject.idle_add(self.exec_Transaction)
        sleep(0.1)

    def exec_Transaction(self):
        self.trans.mainApp._confDialog.hide()
        self.updateGtk()
        self.exec_transaction()
        self.updateGtk()
        if not self.trans.details:
           self.trans.release()
           self.exiting('')

    def on_TransCancelButton_clicked(self, *args):
        self.trans.release()
        self.trans.mainApp._confDialog.hide()
        self.updateGtk()
        self.exiting('')

    def on_ProgressCloseButton_clicked(self, *args):
        self.trans.mainApp._mainWindow.hide()
        self.updateGtk()
        self.transaction_done = True

    def on_ProgressCancelButton_clicked(self, *args):
        self.trans.release()
        self.trans.mainApp._mainWindow.hide()
        self.updateGtk()

    def config_signals(self):
        self.trans.service.connect("EmitTransactionDone", self.handle_reply)
        self.trans.service.connect("EmitTransactionError", self.handle_error)
        self.trans.service.connect("EmitAvailableUpdates", self.handle_updates)

    def updateGtk(self):
        while Gtk.events_pending():
            Gtk.main_iteration()
