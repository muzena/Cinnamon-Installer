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
        folder_files = glob.glob(os.path.join(MODULE_PATH, "*.py"))
        folder_files.sort()
        mod_files = []
        for i in range(len(folder_files)):
            folder_files[i] = os.path.basename(os.path.normpath(folder_files[i]))
            folder_files[i] = folder_files[i].split(".")[0]
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
    def __init__(self, supported_collections):
        self.services = {}
        self.service = None
        self.collect_type = None
        self.initialized_modules = {}
        self.loop = GObject.MainLoop()
        self.importer = Modules_Importer()
        self.modules = self.importer.get_modules()
        self.register_collections(supported_collections)
        self.signals = []

    def register_collections(self, supported_collections):
        for collect_type in supported_collections:
            if not self.register_collection(collect_type):
                return False
        self.importerError = []
        return True

    def register_collection(self, collect_type):
        if len(self.modules) == 0:
            self.importerError = self.importer.get_importer_errors()
            return False
        is_satisfy = False
        for module in self.modules: 
            if module in self.initialized_modules:
                mod = self.initialized_modules[module]
            else:
                mod = module.InstallerModule()
                self.initialized_modules[module] = mod
            if (mod.priority_for_collection(collect_type) > 0):
                is_satisfy = True
                if collect_type in self.services:
                    if mod.get_service() not in self.services[collect_type]:
                        self.services[collect_type].append(mod.get_service())
                else:
                    self.services[collect_type] = []
                    self.services[collect_type].append(mod.get_service())
        if not is_satisfy:
            self.importerError = self.importer.get_importer_errors()
            return False
        self.collect_type = collect_type
        self.importerError = []
        return True

    def register_external_moduler(moduler):
        self.modules.append(moduler)
        self.register_collections(self.services.keys())

    def get_importer_errors(self):
        return self.importerError

    def set_service_for_collection(self, collect_type):
        self.collect_type = collect_type
        if self.service is not None:
            self.disconnect_all_signals()
        if collect_type in self.services:
            self.service = self.services[collect_type][0]
        else:
            self.service = None 

    def connect(self, signal_name, client_handle):
        if self.service:
            self.signals.append(self.service.connect(signal_name, client_handle))

    def disconnect_all_signals(self):
        for signal in self.signals:
            self.service.disconnect(signal)
        self.signals = []

    def need_root_access(self):
        if self.service:
            return self.service.need_root_access()
        return False

    def have_terminal(self):
        if self.service:
            return self.service.have_terminal()
        return False

    def set_terminal(self, ttyname):
        if self.service:
            self.service.set_terminal(ttyname)

    def is_service_idle(self):
        if self.service:
            return self.service.is_service_idle()
        return True

    def get_cache_folder(self, collect_type=None):
        if self.service:
            return self.service.get_cache_folder(collect_type)
        return ""

    def search_files(self, path):
        if self.service:
            result = []
            thread = Thread(target = self.service.search_files, args=(path, self.loop, result,))
            thread.start()
            self.loop.run()
            return result[0]
        return ""

    def get_all_local_packages(self, collect_type=None):
        if self.service:
            result = []
            thread = Thread(target = self.service.get_all_local_packages, args=(self.loop, result, collect_type,))
            thread.start()
            self.loop.run()
            return result[0]
        return []

    def get_all_remote_packages(self, collect_type=None):
        if self.service:
            result = []
            thread = Thread(target = self.service.get_all_remote_packages, args=(self.loop, result, collect_type,))
            thread.start()
            self.loop.run()
            return result[0]
        return []

    def get_local_packages(self, packages, collect_type=None):
        if self.service:
            result = []
            thread = Thread(target = self.service.get_local_packages, args=(packages, self.loop, result, collect_type,))
            thread.start()
            self.loop.run()
            return result[0]
        return []

    def get_remote_packages(self, packages, collect_type=None):
        if self.service:
             result = []
             thread = Thread(target = self.service.get_remote_packages, args=(packages, self.loop, result, collect_type,))
             thread.start()
             self.loop.run()
             return result[0]
        return []

    def get_local_search(self, patterns, collect_type=None):
        if self.service:
             result = []
             thread = Thread(target = self.service.get_local_search, args=(patterns, self.loop, result, collect_type,))
             thread.start()
             self.loop.run()
             return result[0]
        return []

    def get_remote_search(self, patterns, collect_type=None):
        if self.service:
             result = []
             thread = Thread(target = self.service.get_remote_search, args=(patterns, self.loop, result, collect_type,))
             thread.start()
             self.loop.run()
             return result[0]
        return []

    def prepare_transaction_install(self, pkgs_names, collect_type=None):
        if self.service:
             thread = Thread(target = self.service.prepare_transaction_install, args=(pkgs_names, collect_type,))
             thread.start()

    def prepare_transaction_remove(self, pkgs_names, collect_type=None):
        if self.service:
             thread = Thread(target = self.service.prepare_transaction_remove, args=(pkgs_names, collect_type,))
             thread.start()

    def commit(self):
        if self.service:
             thread = Thread(target = self.service.commit, args=())
             thread.start()

    def cancel(self):
        if self.service:
             thread = Thread(target = self.service.cancel, args=())
             thread.start()

    def resolve_config_file_conflict(self, replace, old, new):
        if self.service:
             thread = Thread(target = self.service.resolve_config_file_conflict, args=(replace, old, new,))
             thread.start()

    def resolve_medium_required(self, medium):
        if self.service:
             thread = Thread(target = self.service.resolve_medium_required, args=(medium,))
             thread.start()

    def resolve_package_providers(self, provider_select):
        if self.service:
             thread = Thread(target = self.service.resolve_package_providers, args=(provider_select,))
             thread.start()

    def check_updates(self, collect_type=None):
        if self.service:
             thread = Thread(target = self.service.check_updates, args=(None, None, collect_type))
             thread.start()

    def system_upgrade(self, show_updates = True, downgrade = False, collect_type=None):
        if self.service:
             thread = Thread(target = self.service.system_upgrade, args=(downgrade, self.loop, collect_type,))
             thread.start()

    def write_config(self, array, collect_type=None):
        if self.service:
             thread = Thread(target = self.service.write_config, args=(array, collect_type,))
             thread.start()

    '''  this need to be see  '''
    def load_cache(self, async, collect_type=None):
        if self.service:
             thread = Thread(target = self.service.load_cache, args=(async, collect_type,))
             thread.start()

    def refresh_cache(self, force_update, collect_type=None):#Test if this can removed latter.
        if self.service:
             thread = Thread(target = self.service.refresh_cache, args=(force_update, collect_type,))
             thread.start()

    def have_cache(self, collect_type=None):
        if self.service:
            return self.service.have_cache(collect_type)
        return False

    def release(self):#Test if this can removed latter.
        if self.service:
             thread = Thread(target = self.service.release_all, args=())
             thread.start()

class Installer():
    def __init__(self):
        self.supported_collections = []
        self.trans = Transaction(self.supported_collections)
        self.mainApp = ApplicationGUI.MainApp()
        self.mainWind = ApplicationGUI.ControlWindow(self.mainApp)
        self.paren_window = None
        self.paren_builder = None

    def setParentRef(self, window, builder):
        '''We need to set the main windows to
        show the instaler as modal if we have one
        this is call from cs_installer and could be
        not needed, we can get it from the register
        module?'''
        self.paren_window = window
        self.paren_builder = builder
        print("Not implemented setParentRef")

    def register_module(self, module):
        self.trans.register_collection(module.sidePage.collection_type)
        module.sidePage.set_installer(self)
        self.set_service_for_collection(module.sidePage.collection_type)

    def register_collection(self, collect_type):
        self.trans.register_collection(collect_type)
        self.set_service_for_collection(collect_type)

    def register_installer(self, installer):
        self.trans.register_external_moduler(installer.get_parent_module())

    def load_module(self, module):
        print("Not implemented load_module") # remove to sc_installer
        #if self.single_mode:
        #    self.providers[0].load_module(module.sidePage.collection_type, False)
        #self.modules[mod_name].sidePage.load_extensions()

    def set_service_for_collection(self, collect_type):
        self.trans.set_service_for_collection(collect_type)
        self.mainWind.set_transaction(self.trans)

    def get_importer_errors(self):
        self.trans.get_importer_errors()

    def need_root_access(self, collect_type):
        self.register_collection(collect_type)
        self.trans.need_root_access()
    '''
    def check_update_silent(self):
        if self.single_mode:
            self.providers[0].check_update_silent()
        else:
            print("Not implemented, provide a way to update modules for different installer")
        return True
    '''
    def execute_install(self, collect_type, pkgs_name, callback=None):
        pkgs_list = self._create_packages_list(pkgs_name)
        if len(pkgs_list) > 0:
            self.mainWind.show()
            self.trans.prepare_transaction_install(pkgs_list)
            self.mainWind.run()
        else:
            print("Error, not packages founds")

    def execute_uninstall(self, collect_type, pkgs_name, callback=None):
        pkgs_list = self._create_packages_list(pkgs_name)
        if len(pkgs_list) > 0:
            self.mainWind.show()
            self.trans.prepare_transaction_remove(pkgs_list)
            self.mainWind.run()
        else:
            print("Error, not packages founds")
    '''
    def execute_uninstall_program(self, programName, callback=None):
        self.register_collection("package")
        self.mainWind.preformUninstall(programName);
    '''
    def execute_upgrade(self, collect_type, pkgs_namee, callback=None):
        self.register_collection(collect_type)
        #self.mainWind.run()
        #self.trans.upgrade_system(safe_mode=False, 
        #                          reply_handler=self._simulate_trans,
        #                          error_handler=self._on_error)

    def execute_update(self, collect_type, packageName, callback=None):
        self.register_collection(collect_type)
        #self.mainWind.run()
        #self.trans.update_cache(repaly_handler=self._run_transaction,
        #                        error_handler=self._on_error)

    def search_uninstall(self, collect_type, pattern, callback=None):
        self.register_collection(collect_type)
        result = self.trans.get_remote_search(pattern, collect_type)
        return result

    def find_package_by_path(self, collect_type, path, callback=None):
        self.register_collection(collect_type)
        result = self.trans.search_files(path)
        if len(result) > 0:
            return result[0]
        return None

    def load_cache(self, force=False, collect_type=None, callback=None):
        self.register_collection(collect_type)
        if force or not self.have_cache(collect_type):
            self.trans.load_cache(True, collect_type)
            if callback and callable(callback):
                self.trans.connect("EmitTransactionDone", callback)
        elif callback and callable(callback):
            callback(self.trans.service, "Done")

    def refresh_cache(self, show_window, collect_type, callback=None):
        self.register_collection(collect_type)
        if show_window:
            self.mainWind.show()
        self.trans.refresh_cache(True, collect_type)
        if callback and callable(callback):
            self.trans.connect("EmitTransactionDone", callback)
        if show_window:
            self.mainWind.run()

    def have_cache(self, collect_type):
        return self.trans.have_cache(collect_type)

    def get_all_local_packages(self, collect_type):
        self.register_collection(collect_type)
        return self.trans.get_all_local_packages(collect_type)

    def get_all_remote_packages(self, collect_type):
        self.register_collection(collect_type)
        return self.trans.get_all_remote_packages(collect_type)

        
    #def load(self, mod_name, on_spice_load, force):
        '''
        if not mod_name == "theme":
            self.scrubConfigDirs(mod_name, self.modules[mod_name].sidePage.enabled_extensions)
        self.installer[mod_name].load(on_spice_load, force)
        # this code it's for test
        self.installer[mod_name].abort_download = ABORT_NONE
        if (self.installer[mod_name].has_cache and not force):
            self.installer[mod_name].load_cache()
        elif force:
            #self.emit("EmitTransactionStart", _("Refreshing index..."))
            #self.installer[mod_name].refresh_cache()
            #self.emit("EmitTransactionDone", "")
            try:
                self.run()
                self.trans.set_service_for_collection("applet")
                self.trans.load_cache(True)
            except Exception:
                e = sys.exc_info()[1]
                print(str(e))
        on_spice_load(self.installer[mod_name].index_cache)
        '''

    def show_detail(self, collect_type, uuid, callback):
        print("Not implemented show_detail")
        #self.installer[collect_type].show_detail(uuid, callback)

    def get_cache_folder(self, collect_type):
        self.register_collection(collect_type)
        return self.trans.get_cache_folder(collect_type)

    def _create_packages_list(self, pkgs_name):
        unfilter_pkg_list = pkgs_name.split(",")
        pkg_list = []
        for pkg in unfilter_pkg_list:
            if ((pkg != "") and (pkg not in pkg_list)):
                pkg_list.append(pkg)
        return pkg_list

    '''
    def check_update_silent(self):
        for mod in self.modules:
            thread = Thread(target = self.check_update_collection_type, args=(self.modules[mod].sidePage.collection_type,))
            thread.start()
        #wait for notify

    def check_update_collection_type(self, mod_name):
        self.installer[mod_name].refresh_cache_silent()

    def scrubConfigDirs(self, mod_name, enabled_list):
        self.installer[mod_name].scrubConfigDirs(enabled_list)

    def uninstall(self, mod_name, uuid, name, schema_filename, on_uninstall_finished):
        self.installer[mod_name].uninstall(uuid, name, schema_filename, on_uninstall_finished)

    def preformInstallFile(self):
        chooser = Gtk.FileChooserDialog(parent=self.mainWindow,
                                        action=Gtk.FileChooserAction.OPEN,
                                        buttons=(Gtk.STOCK_CANCEL,
                                                 Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OPEN,
                                                 Gtk.ResponseType.OK))
        chooser.set_local_only(True)
        chooser.run()
        chooser.hide()
        path = chooser.get_filename()
        self.trans.install_file(path, reply_handler=self._simulate_trans,
                             error_handler=self._on_error)
        self.run()
    '''
    def errorMessage(title, desc):
        print("Not implemented errorMessage")
       

class Spice_Harvester_Composed(GObject.GObject):
    __gsignals__ = {
        "EmitTransactionStart": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitTransactionDone": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitTarget": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitPercent": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_FLOAT,)),
        "EmitTransactionCancellable": (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_BOOLEAN,)),
        "EmitTransactionError": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING,))
    }
    def __init__(self):
        GObject.GObject.__init__(self)
        self.name = "Spice_Harvester"
        self.supported_modules = ["applet", "desklet", "extension", "theme", "package"]
        self.installer = {}
        self.modules = {}

        self.trans = Transaction(self.supported_modules)
        self.trans.set_service_for_collection("applet")
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

__default_installer__ = None

def get_default():
    global __default_installer__ 
    if __default_installer__ is None:
        __default_installer__ = Installer()
    return __default_installer__
