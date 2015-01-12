#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Cinnamon Installer
#
# Authors: Lester Carballo Pérez <lestcape@gmail.com>
#
#
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

import os, sys, glob, signal
from threading import Thread
from gi.repository import GObject

try:
    import ApplicationGUI
    import SpiceHarvesterCinnamon
except Exception:
    e = sys.exc_info()[1]
    print(str(e))
    sys.exit(1)

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(os.path.dirname(ABS_PATH))
MODULE_PATH = os.path.join(DIR_PATH, "installer_modules/")

ABORT_NONE = 0
ABORT_ERROR = 1
ABORT_USER = 2

class Modules_Importer():
    def __init__(self):
        folder_files = glob.glob(os.path.join(MODULE_PATH, '*.py'))
        folder_files.sort()
        mod_files = []
        for i in range(len(folder_files)):
            folder_files[i] = os.path.basename(os.path.normpath(folder_files[i]))
            folder_files[i] = folder_files[i].split('.')[0]
            if folder_files[i][0:3] == "ci_":
                mod_files.append(folder_files[i])
        if len(mod_files) is 0:
            raise Exception("No settings modules found!!" + str(len(folder_files)))
        self.modules = []
        self.importerError = []
        for i in range(len(mod_files)):
            try:
                module = __import__(mod_files[i])
                self.modules.append(module)
            except ImportError:
                e = sys.exc_info()[1]
                self.importerError.append([mod_files[i], e])
        if len(self.modules) is 0:
            raise Exception("No settings modules found!!")

    def get_modules(self):
        return self.modules

    def get_importer_errors(self):
        return self.importerError

class Transaction(object):
    def __init__(self, actions_requiered):
        self.services = {}
        self.loop = GObject.MainLoop()
        importer = Modules_Importer()
        modules = importer.get_modules()
        if self._satisfy_conditions(modules, actions_requiered):
            self.importerError = []
        else:
            self.importerError = importer.get_importer_errors()

    def _satisfy_conditions(self, modules, actions_requiered):
        if len(modules) == 0:
            return False
        for action in actions_requiered:
            is_satisfy = False
            for module in modules:
                mod = module.InstallerModule()
                is_satisfy = (mod.priority_for_action(action) > 0)
                if is_satisfy:
                    self.services[action] = mod.get_service()
                    break
            if not is_satisfy:
                return False
        return True

    def get_importer_errors(self):
        return self.importerError

    def set_service_for_action(self, action):
        if action in self.services:
            self.service = self.services[action]
        else:
            self.service = None 

    def connect(self, signal_name, client_handle):
        self.service.connect(signal_name, client_handle)

    def need_root_access(self):
        return self.service.need_root_access()

    def have_terminal(self):
        return self.service.have_terminal()

    def set_terminal(self, ttyname):
        self.service.set_terminal(ttyname)

    def is_service_idle(self):
        return self.service.is_service_idle()

    def search_files(self, path):
        result = []
        thread = Thread(target = self.service.search_files, args=(path, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0]

    def get_all_local_packages(self):
        result = []
        thread = Thread(target = self.service.get_all_local_packages, args=(self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0]

    def get_all_remote_packages(self):
        result = []
        thread = Thread(target = self.service.get_all_remote_packages, args=(self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0]

    def get_local_packages(self, packages):
        result = []
        thread = Thread(target = self.service.get_local_packages, args=(packages, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0]

    def get_remote_packages(self, packages):
        result = []
        thread = Thread(target = self.service.get_remote_packages, args=(packages, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0]

    def get_local_search(self, patterns):
        result = []
        thread = Thread(target = self.service.get_local_search, args=(patterns, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0]

    def get_remote_search(self, patterns):
        result = []
        thread = Thread(target = self.service.get_remote_search, args=(patterns, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0]

    def prepare_transaction_install(self, pkgs_names):
        thread = Thread(target = self.service.prepare_transaction_install, args=(pkgs_names,))
        thread.start()

    def prepare_transaction_remove(self, pkgs_names):
        thread = Thread(target = self.service.prepare_transaction_remove, args=(pkgs_names,))
        thread.start()

    def commit(self):
        thread = Thread(target = self.service.commit, args=())
        thread.start()

    def cancel(self):
        thread = Thread(target = self.service.cancel, args=())
        thread.start()

    def resolve_config_file_conflict(self, replace, old, new):
        thread = Thread(target = self.service.resolve_config_file_conflict, args=(replace, old, new,))
        thread.start()

    def resolve_medium_required(self, medium):
        thread = Thread(target = self.service.resolve_medium_required, args=(medium,))
        thread.start()

    def resolve_package_providers(self, provider_select):
        thread = Thread(target = self.service.resolve_package_providers, args=(provider_select,))
        thread.start()

    def check_updates(self):
        thread = Thread(target = self.service.check_updates, args=(None, None))
        thread.start()

    def system_upgrade(self, downgrade):
        thread = Thread(target = self.service.Sysupgrade, args=(downgrade, self.loop))
        thread.start()

    def write_config(self, array, sender=None, connexion=None):
        thread = Thread(target = self.service.write_config, args=(array))
        thread.start()

    '''  this need to be see  '''
    def load_cache(self, async):
        thread = Thread(target = self.service.load_cache, args=(async,))
        thread.start()

    def refresh(self, force_update):#Test if this can removed latter.
        thread = Thread(target = self.service.refresh_service, args=(force_update,))
        thread.start()

    def release(self):#Test if this can removed latter.
        thread = Thread(target = self.service.release_all, args=())
        thread.start()

class Installer():
    def __init__(self):
        self.installer_providers = {}
        self.providers = []
        self.single_mode = True
        sp_har = Spice_Harvester_Composed()
        self.installer_providers[sp_har.name] = sp_har

    def select_installer_provider(self, window, builder):
         #try to load first cinnamon installer....
         for provider_name in self.installer_providers:
             self.installer_providers[provider_name].set_parent_ref(window, builder)
         # order the modules by scores...

    def register_module(self, module):
        for provider in self.installer_providers:
            if self.installer_providers[provider].register_module(module):
                if not self.installer_providers[provider] in self.providers:
                    self.providers.append(self.installer_providers[provider])
                break
        self.single_mode = len(self.providers) == 1

    def load_module(self, module):
        if self.single_mode:
            self.providers[0].load_module(module.sidePage.collection_type, False)

    def set_service_for_collection(self, collect_type):
        self.providers[0].set_service_for_collection(collect_type)

    def get_importer_errors(self):
        self.providers[0].get_importer_errors()

    def need_root_access(self):
        self.providers[0].need_root_access()

    def check_update_silent(self):
        if self.single_mode:
            self.providers[0].check_update_silent()
        else:
            print("Not implemented, provide a way to update modules for different installer")
        return True

    ##############

    def execute_install(self, packageName):
       self.providers[0].execute_install(packageName)

    def execute_uninstall(self, packageName):
       self.providers[0].execute_uninstall(packageName)
    '''
    def execute_uninstall_program(self, programName):
       self.providers[0].execute_uninstall_program(programName)
    '''
    def execute_upgrade(self, packageName):
       self.providers[0].execute_upgrade(packageName)

    def execute_update(self, packageName):
       self.providers[0].execute_update(packageName)

    def search_uninstall(self, packageName):
       return self.providers[0].search_uninstall(packageName)

    def find_package_by_path(self, path):
       return self.providers[0].find_package_by_path(path)

class Spice_Harvester_Composed(GObject.GObject):
    __gsignals__ = {
        'EmitTransactionStart': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitTransactionDone': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitTarget': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitPercent': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_FLOAT,)),
        'EmitTransactionCancellable': (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_BOOLEAN,)),
        'EmitTransactionError': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING,))
    }
    def __init__(self):
        GObject.GObject.__init__(self)
        self.name = "Spice_Harvester"
        self.supported_modules = ["applet", "desklet", "extension", "theme"]
        self.installer = {}
        self.modules = {}

        self.trans = Transaction(self.supported_modules)
        self.trans.set_service_for_action("applet")
        self.trans.load_cache(True)
        self.importerError = self.trans.get_importer_errors()
        self.mainApp = ApplicationGUI.MainApp()
        self.mainWind = ApplicationGUI.ControlWindow(self.mainApp, self.trans)

    def set_parent_ref(self, window, builder):
        self.builder = builder
        self.window = window

    def score(self):
        return 0

    def register_module(self, module):
        collect_type = module.sidePage.collection_type
        if (collect_type in self.supported_modules):
            try:
                module.sidePage.set_installer(self)
                self.installer[collect_type] = SpiceHarvesterCinnamon.Spice_Harvester_Cinnamon(collect_type, self.window, self.builder, self)
                self.modules[collect_type] = module
                return True
            except Exception:
                e = sys.exc_info()[1]
                print("Error " + str(e))
                return False
        return False

    def check_update_silent(self):
        for mod in self.modules:
            thread = Thread(target = self.check_update_collection_type, args=(self.modules[mod].sidePage.collection_type,))
            thread.start()
        #wait for notify

    def load_module(self, mod_name, force):
        self.modules[mod_name].sidePage.load_extensions()

    def check_update_collection_type(self, mod_name):
        self.installer[mod_name].refresh_cache_silent()

    def scrubConfigDirs(self, mod_name, enabled_list):
        self.installer[mod_name].scrubConfigDirs(enabled_list)

    def show_detail(self, mod_name, uuid, callback):
        self.installer[mod_name].show_detail(uuid, callback)

    def load(self, mod_name, on_spice_load, force):
        if not mod_name == "theme":
            self.scrubConfigDirs(mod_name, self.modules[mod_name].sidePage.enabled_extensions)
        self.installer[mod_name].load(on_spice_load, force)

        '''
        # this code it's for test
        self.installer[mod_name].abort_download = ABORT_NONE
        if (self.installer[mod_name].has_cache and not force):
            self.installer[mod_name].load_cache()
        elif force:
            #self.emit('EmitTransactionStart', _("Refreshing index..."))
            #self.installer[mod_name].refresh_cache()
            #self.emit('EmitTransactionDone', "")
            try:
                self.run()
                self.trans.set_service_for_action("applet")
                self.trans.load_cache(True)
            except Exception:
                e = sys.exc_info()[1]
                print(str(e))
        on_spice_load(self.installer[mod_name].index_cache)
        '''

    def set_service_for_collection(self, collect_type):
         self.trans.set_service_for_action(collect_type)

    def get_importer_errors(self):
        self.trans.get_importer_errors()

    def need_root_access(self):
        self.trans.need_root_access()

    def get_cache_folder(self, mod_name):
        return self.installer[mod_name].get_cache_folder()

    def install_all(self, mod_name, install_list, install_finished):
        self.installer[mod_name].install_all(install_list, install_finished)

    def uninstall(self, mod_name, uuid, name, schema_filename, on_uninstall_finished):
        self.installer[mod_name].uninstall(uuid, name, schema_filename, on_uninstall_finished)

    def uninstall_all(self, mod_name, list_uninstall, on_uninstall_finished):
        self.installer[mod_name].uninstall_all(list_uninstall, on_uninstall_finished)

    #########
    def execute_install(self, packageName):
       self.mainApp._mainWindow.set_title(_("Cinnamon Installer"))
       self.mainApp._appNameLabel.set_text(_("Cinnamon Installer"))
       self.mainWind.preformInstall(packageName);

    def execute_uninstall(self, packageName):
       self.mainApp._mainWindow.set_title(_("Cinnamon Installer"))
       self.mainApp._appNameLabel.set_text(_("Cinnamon Installer"))
       self.mainWind.preformUninstall(packageName);
    '''
    def execute_uninstall_program(self, programName):
       self.mainApp._mainWindow.set_title(_("Cinnamon Installer"))
       self.mainApp._appNameLabel.set_text(_("Cinnamon Installer"))
       self.mainWind.preformUninstall(programName);
    '''
    def execute_upgrade(self, packageName):
       self.mainApp._mainWindow.set_title(_("Cinnamon Installer"))
       self.mainApp._appNameLabel.set_text(_("Cinnamon Installer"))
       self.mainWind.preformUpgrade(packageName);

    def execute_update(self, packageName):
       self.mainApp._mainWindow.set_title(_("Cinnamon Installer"))
       self.mainApp._appNameLabel.set_text(_("Cinnamon Installer"))
       self.mainWind.preformUpdate(packageName);

    def search_uninstall(self, packageName):
       self.mainApp._mainWindow.set_title(_("Cinnamon Installer"))
       self.mainApp._appNameLabel.set_text(_("Cinnamon Installer"))
       return self.mainWind.searchUnistalledPackages(packageName)

    def find_package_by_path(self, path):
       return self.mainWind.findPackageByPath(path);

defaultInstaller = Installer()

def get_default():
    return defaultInstaller
