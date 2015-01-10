#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Cinnamon Installer
#
# Authors: Lester Carballo Pérez <lestcape@gmail.com>
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

import os, glob, sys
from gi.repository import GObject
from threading import Thread

ABS_PATH = os.path.abspath(__file__)
MODULE_PATH = os.path.dirname(os.path.dirname(ABS_PATH)) + "/installer_modules/"

class Modules_Importer():
    def __init__(self):
        folder_files = glob.glob(MODULE_PATH + '*.py')
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

    def get_default(self):
        if len(self.modules) > 0:
            return self.modules[0]
        return None

    def get_importer_errors(self):
        return self.importerError

class Transaction(object):
    def __init__(self):
        importer = Modules_Importer()
        module = importer.get_default()
        if module is None:
            self.importerError = importer.get_importer_errors()
            self.service = None
        else:
            self.importerError = []
            self.service = module.InstallerService()
        self.loop = GObject.MainLoop()

    def get_importer_errors(self):
        return self.importerError

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
    def refresh(self, force_update):#Test if this can removed latter.
        thread = Thread(target = self.service.refresh_service, args=(force_update,))
        thread.start()

    def release(self):#Test if this can removed latter.
        thread = Thread(target = self.service.release_all, args=())
        thread.start()

