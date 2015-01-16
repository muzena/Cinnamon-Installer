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

import sys, os

try:
    import tempfile, time, zipfile, string, shutil, cgi, subprocess, signal
    #from datetime import datetime
    from gi.repository import Gtk, GObject
    from threading import Thread
    from multiprocessing import Lock#, Queue 
except Exception:
    e = sys.exc_info()[1]
    print(str(e))
    sys.exit(1)

try:
    import json
except ImportError:
    import simplejson as json

import SpicesPackages

from gi.repository import GObject

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"

# i18n
import gettext, locale
LOCALE_PATH = DIR_PATH + "locale"
DOMAIN = "cinnamon-installer"
locale.bindtextdomain(DOMAIN , LOCALE_PATH)
locale.bind_textdomain_codeset(DOMAIN , "UTF-8")
gettext.bindtextdomain(DOMAIN, LOCALE_PATH)
gettext.bind_textdomain_codeset(DOMAIN , "UTF-8")
gettext.textdomain(DOMAIN)
_ = gettext.gettext

home = os.path.expanduser("~")
locale_inst = "%s/.local/share/locale" % home
settings_dir = "%s/.cinnamon/configs/" % home

URL_SPICES_HOME = "http://cinnamon-spices.linuxmint.com"

ABORT_NONE = 0
ABORT_ERROR = 1
ABORT_USER = 2

CI_STATUS = {
    "RESOLVING_DEPENDENCIES": "Resolving dep",
    "SETTING_UP": "Setting up",
    "LOADING_CACHE": "Loading cache",
    "AUTHENTICATING": "authenticating",
    "DOWNLOADING": "Downloading",
    "DOWNLOADING_REPO": "Downloading repo",
    "RUNNING": "Running",
    "COMMITTING": "Committing",
    "INSTALLING": "Installing",
    "REMOVING": "Removing",
    "CHECKING": "Checking",
    "FINISHED": "Finished",
    "WAITING": "Waiting",
    "WAITING_LOCK": "Waiting lock",
    "WAITING_MEDIUM": "Waiting medium",
    "WAITING_CONFIG_FILE": "Waiting config file",
    "CANCELLING": "Cancelling",
    "CLEANING_UP": "Cleaning up",
    "QUERY": "Query",
    "DETAILS": "Details",
    "UNKNOWN": "Unknown"
}
'''
CI_STATUS = {
    "status-resolving-dep": "RESOLVING_DEPENDENCIES",
    "status-setting-up": "SETTING-UP",
    "status-loading-cache": "LOADING_CACHE",
    "status-authenticating": "AUTHENTICATING",
    "status-downloading": "DOWNLOADING",
    "status-downloading-repo": "DOWNLOADING_REPO",
    "status-running": "RUNNING",
    "status-committing": "COMMITTING",
    #"status-installing": "INSTALLING",
    #"status-removing": "REMOVING",
    "status-finished": "FINISHED",
    "status-waiting": "WAITING",
    "status-waiting-lock": "WAITING_LOCK",
    "status-waiting-medium": "WAITING_MEDIUM",
    "status-waiting-config-file-prompt": "WAITING_CONFIG_FILE",
    "status-cancelling": "CANCELLING",
    "status-cleaning-up": "CLEANING_UP",
    "status-query": "QUERY",
    "status-details": "DETAILS",
    "status-unknown": "UNKNOWN"
}
'''

def rec_mkdir(path):
    if os.path.exists(path):
        return
    
    rec_mkdir(os.path.split(path)[0])

    if os.path.exists(path):
        return
    os.mkdir(path)

def removeEmptyFolders(path):
    if not os.path.isdir(path):
        return

    # remove empty subfolders
    files = os.listdir(path)
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                removeEmptyFolders(fullpath)

    # if folder empty, delete it
    files = os.listdir(path)
    if len(files) == 0:
        print("Removing empty folder:" + path)
        os.rmdir(path)

class InstallerModule():
    def __init__(self):
        self.validTypes = ["applet", "desklet", "extension", "theme"]
        self.service = None

    def priority_for_collection(self, collect_type):
        if collect_type in self.validTypes:
            return 1
        return 0
    
    def get_service(self):
        if self.service is None:
            self.service = InstallerService()
        self.service.set_parent_module(self)
        return self.service

class InstallerService(GObject.GObject):
    __gsignals__ = {
        "EmitTransactionDone": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitTransactionError": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING,)),
        "EmitAvailableUpdates": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN, GObject.TYPE_BOOLEAN,)),
        "EmitStatus": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING,)),
        "EmitRole": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitNeedDetails": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN,)),
        "EmitIcon": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitTarget": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitPercent": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_FLOAT,)),
        "EmitDownloadPercentChild": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_FLOAT, GObject.TYPE_STRING,)),
        "EmitDownloadChildStart": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN,)),
        "EmitLogError": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitLogWarning": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitTransactionStart": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitReloadConfig": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        "EmitTransactionConfirmation": (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_PYOBJECT,)),
        "EmitTransactionCancellable": (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_BOOLEAN,)),
        "EmitTerminalAttached": (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_BOOLEAN,)),
        "EmitConflictFile": (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING,)),
        "EmitChooseProvider": (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_PYOBJECT,)),
        "EmitMediumRequired": (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING))
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.cache = SpicesPackages.SpiceCache()
        self.index_cache = {}
        self.error = None
        self.has_cache = False
        self.collection_type = None
        self.module = None
        self.max_process = 3
        self.lock = Lock()
        self.validTypes = self.cache.get_valid_types();
        self.cacheTypesLength = len(self.validTypes)

    def need_root_access(self):
        return False

    def have_terminal(self):
        return False

    def set_terminal(self, ttyname):
        pass

    def is_service_idle(self):
        return True

    def load_cache(self, async, collect_type=None):
        self.EmitTransactionStart("Start")
        if (not collect_type):
            if (async):
                for collect_type in self.validTypes:
                    thread = Thread(target = self.cache.load_collection_type, args=(collect_type, self.cache_load_finished))
                    thread.start()
            else:
                self.cache.load(self.cache_load_finished)
        elif collect_type:
            if (async):
                thread = Thread(target = self.cache.load_collection_type, args=(collect_type, self.cache_load_finished))
                thread.start()
            else:
                self.cache.load_collection_type(collect_type, self.cache_load_finished)
        #self.executer.load_cache(async)

    def cache_load_finished(self):
        self.EmitTransactionDone("Finished")
        print("finished on_refresh_assets_finished")

    def have_cache(self, collect_type=None):
        return self.cache.is_load(collect_type)

    def set_parent_module(self, module):
        self.module = module

    def get_parent_module(self):
        return self.module

    def get_cache_folder(self, collect_type=None):
        return self.cache.get_cache_folder(collect_type)

    def search_files(self, path, loop, result):
        pass

    def get_all_local_packages(self, loop, result, collect_type=None):
        try:
            result.append(self.cache.get_local_packages(collect_type))
        except Exception:
            result.append([])
            e = sys.exc_info()[1]
            print(str(e))
        time.sleep(0.1)
        loop.quit()

    def get_all_remote_packages(self, loop, result, collect_type=None):
        try:
            result.append(self.cache.get_remote_packages(collect_type))
        except Exception:
            result.append([])
            e = sys.exc_info()[1]
            print(str(e))
        time.sleep(0.1)
        loop.quit()

    def get_local_packages(self, packages, loop, result, collect_type=None):
        get_local_packages

    def get_remote_packages(self, packages, loop, result, collect_type=None):
        pass

    def get_local_search(self, pattern, loop, result, collect_type=None):
        pass

    def get_remote_search(self, pattern, loop, result, collect_type=None):
        pass

    def prepare_transaction_install(self, packages, collect_type=None):
        pass

    def prepare_transaction_remove(self, packages, collect_type=None):
        pass

    def commit(self):
        pass

    def cancel(self):
        pass

    def resolve_config_file_conflict(replace, old, new):
        pass

    def resolve_medium_required(self, medium):
        pass

    def resolve_package_providers(self, provider_select):
        pass

    def check_updates(self, success=None, nosuccess=None, collect_type=None):
        pass

    def system_upgrade(self, show_updates, downgrade, collect_type=None):
        pass

    def write_config(self, array, collect_type=None):
        pass

    def release_all(self):
        pass

    def refresh_cache(self, force_update=False, collect_type=None): #See if this can be moved or removed
        load_assets = force_update
        self.EmitTransactionStart("Start")
        if  collect_type == None:
            self._refresh_all_cache()
            #elif (self.cache.is_valid_type(collect_type)):
            #   self.refresh_cache_type(collect_type, load_assets)
            #self.abort_download = ABORT_NONE
            #self.cache.refresh_cache_type(collect_type, load_assets)
        else:
            total_count = 1
            install_errors = {}
            valid_task = {}
            self.EmitStatus("DOWNLOADING", _("Downloading"))
            valid_task[collect_type] = [Thread(target = self._refresh_cache_type, args=(collect_type, total_count,
                                        valid_task,)), -1, install_errors]
            self._try_start_task(valid_task, self.max_process)

    def _refresh_all_cache(self):
        total_count = len(self.validTypes)
        install_errors = {}#Queue()
        valid_task = {}
        self.EmitDownloadChildStart(False)
        for collect_type in self.validTypes:
            self.EmitStatus("DOWNLOADING", _("Downloading"))
            valid_task[collect_type] = [Thread(target = self._refresh_cache_type, args=(collect_type, total_count,
                                        valid_task,)), -1, install_errors]
        self._try_start_task(valid_task, self.max_process)
        #for collect_type in self.validTypes:
        #    refresh_cache_type(collect_type, load_assets)

    def _refresh_cache_type(self, collect_type, total_count, valid_task):
        self.EmitRole(_("Refreshing index for %ss" % collect_type))
        self.EmitDownloadPercentChild(collect_type, "%s index" % collect_type, 0, "")
        self.cache.refresh_cache_type([collect_type, total_count, valid_task], self.reporthook_refresh)
        self._on_refresh_finished(collect_type, total_count, valid_task, "")

    def reporthook_refresh(self, count, block_size, total_size, user_param):
        [collect_type, total_count, valid_task] = user_param
        percent = int((float(count*block_size)/total_size)*100)
        self.EmitDownloadPercentChild(collect_type, "%ss index" % collect_type, percent, "")
        procc_count = 0
        for uuid in valid_task:
            if valid_task[uuid][1] < 0:
                procc_count += 1
        count = float(total_count - procc_count - 1)/total_count
        self.EmitPercent(100*count)
        targent = "%s" % (str(int(100*count)) + "%")
        self.EmitTarget(targent)

    def _on_refresh_finished(self, collect_type, total_count, valid_task, error):
        self.lock.acquire()
        valid_task[collect_type][1] = 1
        procc_count = self._try_start_task(valid_task, self.max_process)
        if(procc_count == 0):
            print("refresh_finished")
            self._refresh_assets()
        '''
        if (self.has_cache and not force):
            self.load_cache()
        else:
            precentText = ("{transferred}/{size}").format(transferred = self.noun, size = self.cacheTypesLength)
            target = _("Refreshing %s index...") % (precentText)
            self.EmitTarget(target)
            self.refresh_cache()
        '''
        self.lock.release()

    def _refresh_assets(self):
        total_count = len(self.validTypes)
        valid_task = {}
        install_errors = {}
        max_process = 1
        self.EmitStatus("DOWNLOADING", _("Downloading"))
        for collect_type in self.validTypes:
            valid_task[collect_type] = [Thread(target = self._refresh_assets_type,
                                        args=(collect_type, total_count, valid_task,)), -1, install_errors]
        self._try_start_task(valid_task, max_process)

    def _refresh_assets_type(self, collect_type, total_count, valid_task):
        self.EmitRole(_("Refreshing cache for %ss" % collect_type))
        self.EmitDownloadChildStart(False)
        assets = self.cache.get_assets_type_to_refresh(collect_type)
        internal_total_count = len(assets.keys())
        if internal_total_count > 0:
            internal_valid_task = {}
            install_errors = {}
            for download_url in assets:
                internal_valid_task[download_url] = [Thread(target = self._refresh_assets_type_async,
                    args=(assets[download_url], collect_type, download_url, total_count, internal_total_count, valid_task,
                    internal_valid_task,)), -1, install_errors]
            self._try_start_task(internal_valid_task, self.max_process)
        else:
            self._on_refresh_assets_finished(None, collect_type, "", total_count, valid_task, None)

    def _refresh_assets_type_async(self, package, collect_type, download_url, total_count, internal_total_count, valid_task, internal_valid_task):
        self.EmitDownloadPercentChild(str(package["uuid"]), str(package["name"]), 0, str(package["last_edited"]))
        self.cache.refresh_asset([package, total_count, internal_total_count, valid_task, internal_valid_task], download_url, self.reporthook_assets)
        error = None
        is_really_finished = self._on_refresh_assets_type_finished(package, download_url, total_count, internal_valid_task, error)
        if (is_really_finished):
            self._on_refresh_assets_finished(package, collect_type, download_url, total_count, valid_task, error)
        return True

    def reporthook_assets(self, count, block_size, total_size, user_param):
        [package, total_count, internal_total_count, valid_task, internal_valid_task] = user_param
        percent = int((float(count*block_size)/total_size)*100)
        self.EmitDownloadPercentChild(str(package["uuid"]), str(package["name"]), percent, str(package["last_edited"]))
        internal_procc_count = 0
        for uuid in internal_valid_task:
            if internal_valid_task[uuid][1] < 0:
                internal_procc_count += 1
        procc_count = 0
        for uuid in valid_task:
            if valid_task[uuid][1] < 0:
                procc_count += 1
        out_count = float(total_count - procc_count - 1)/total_count
        int_count = float(internal_total_count - internal_procc_count - 1)/internal_total_count
        self.EmitPercent(100*(out_count + int_count/total_count))
        targent = "%s" % (str(int(100*(out_count + int_count/total_count))) + "%")
        self.EmitTarget(targent)

    def _on_refresh_assets_type_finished(self, package, download_url, total_count, valid_task, error):
        self.lock.acquire()
        is_really_finished = False
        valid_task[download_url][1] = 1
        procc_count = self._try_start_task(valid_task, self.max_process)
        #del valid_task[download_url][1]
        if (procc_count == 0):
            print("finished on_refresh_assets_type_finished")
            is_really_finished = True
        self.lock.release()
        return is_really_finished

    def _on_refresh_assets_finished(self, package, collect_type, download_url, total_count, valid_task, error):
        self.lock.acquire()
        max_process = 1
        valid_task[collect_type][1] = 1
        procc_count = self._try_start_task(valid_task, max_process)
        #del valid_task[collect_type]
        if(procc_count == 0):
            self.EmitTransactionDone("Finished")
            print("finished on_refresh_assets_finished")
        self.lock.release()

    def _try_start_task(self, valid_task, max_process):
        procc_count = 0
        for uuid in valid_task:
            if valid_task[uuid][1] == 0:
                procc_count += 1
        for uuid in valid_task:
           if (valid_task[uuid][1] < 0) and (procc_count < max_process):
               valid_task[uuid][1] = 0
               valid_task[uuid][0].start()
               procc_count += 1
        return procc_count

    def install_all(self, collect_type, uuid_list):
        self.abort_download = False
        total_count = len(uuid_list)
        install_errors = {}#Queue()
        valid_task = {}
        for uuid in uuid_list:
            pkg = self.cache.get_package_from_collection(collect_type, uuid)
            if not pkg:
                #install_errors.put([uuid, _("%s not found") % uuid])
                install_errors[uuid] = _("%s not found") % uuid
                self.on_install_finished(pkg, total_count, install_errors)
            else:
                 #valid_task[uuid] = [Process(target = self._install_single, args=(pkg, total_count, self.on_install_finished, valid_task,)), -1, install_errors]
                 valid_task[uuid] = [Thread(target = self._install_single, args=(pkg, total_count, self.on_install_finished, valid_task,)), -1, install_errors]
        self._try_start_task(valid_task, self.max_process)

    def on_install_finished(self, pkg, total_count, valid_task, error):
        self.lock.acquire()
        uuid = pkg["uuid"]
        install_errors = valid_task[uuid][2]
        install_errors[uuid] = error
        print("listo")
        if len(install_errors.keys()) == total_count:
            error_format = ""
            for uuid in install_errors:
                if install_errors[uuid]:
                    error_format += install_errors[uuid] + "\n"
                    print(error_format)
        valid_task[uuid][1] = 1
        procc_count = self._try_start_task(valid_task, self.max_process)
        if(procc_count == 0):##End or error
            self.EmitTransactionDone("Finished")
            self.abort_download = False
            need_restart = False
            print("end pool")
        self.lock.release()

    def _install_single(self, pkg, total_count, on_install_finished, valid_task):
        #print("Start downloading and installation")
        error = None
        uuid = pkg["uuid"]
        title = pkg["name"]
        error_title = uuid
        try:
            edited_date = pkg["last_edited"]
            collect_type = pkg["collection"]

            #self.progress_window.show()
            #self.progresslabel.set_text(_("Installing %s...") % (title))
            #self.progressbar.set_fraction(0)
            fd, filename = tempfile.mkstemp()
            dirname = tempfile.mkdtemp()
            f = os.fdopen(fd, "wb")
            self.cache.download_packages(pkg, f, filename, self.reporthook)
            zip = zipfile.ZipFile(filename)
            if collect_type == "theme":
                error_title = title
                dest = self.cache.get_install_folder(collect_type)
                zip.extractall(dirname)

                # Check dir name - it may or may not be the same as the theme name from our spices data
                # Regardless, this will end up being the installed theme name, whether it matched or not
                temp_path = os.path.join(dirname, title)
                if not os.path.exists(temp_path):
                    title = os.listdir(dirname)[0] # We assume only a single folder, the theme name
                    temp_path = os.path.join(dirname, title)

                # Test for correct folder structure - look for cinnamon.css
                file = open(os.path.join(temp_path, "cinnamon", "cinnamon.css"), "r")
                file.close()

                md = {}
                md["last-edited"] = edited_date
                md["uuid"] = uuid
                raw_meta = json.dumps(md, indent=4)
                final_path = os.path.join(dest, title)
                file = open(os.path.join(temp_path, "cinnamon", "metadata.json"), "w+")
            else:
                error_title = uuid
                dest = os.path.join(self.cache.get_install_folder(collect_type), uuid)
                schema_filename = ""
                zip.extractall(dirname, self.get_members(zip))
                for file in self.get_members(zip):
                    if not (file.filename.endswith("/")): #and ((file.external_attr >> 16L) & 0o755) == 0o755:
                        os.chmod(os.path.join(dirname, file.filename), 0o755)
                    elif file.filename[:3] == "po/":
                        parts = os.path.splitext(file.filename)
                        if parts[1] == ".po":
                           this_locale_dir = os.path.join(locale_inst, parts[0][3:], "LC_MESSAGES")
                           #self.progresslabel.set_text(_("Installing translations for %s...") % title)
                           rec_mkdir(this_locale_dir)
                           #print("/usr/bin/msgfmt -c %s -o %s" % (os.path.join(dest, file.filename), os.path.join(this_locale_dir, "%s.mo" % uuid)))
                           subprocess.call(["msgfmt", "-c", os.path.join(dirname, file.filename), "-o", os.path.join(this_locale_dir, "%s.mo" % uuid)])
                           #self.progresslabel.set_text(_("Installing %s...") % (title))
                    elif "gschema.xml" in file.filename:
                        sentence = _("Please enter your password to install the required settings schema for %s") % (uuid)
                        if os.path.exists("/usr/bin/gksu") and os.path.exists("/usr/lib/cinnamon-settings/bin/installSchema.py"):
                            launcher = "gksu  --message \"<b>%s</b>\"" % sentence
                            tool = "/usr/lib/cinnamon-settings/bin/installSchema.py %s" % (os.path.join(dirname, file.filename))
                            command = "%s %s" % (launcher, tool)
                            os.system(command)
                            schema_filename = file.filename
                        else:
                            error = _("Could not install the settings schema for %s.  You will have to perform this step yourself.") % (uuid)
                            #self.errorMessage(error)
                file = open(os.path.join(dirname, "metadata.json"), "r")
                raw_meta = file.read()
                file.close()
                md = json.loads(raw_meta)
                md["last-edited"] = edited_date
                if schema_filename != "":
                    md["schema-file"] = schema_filename
                raw_meta = json.dumps(md, indent=4)
                temp_path = dirname
                final_path = dest
                file = open(os.path.join(dirname, "metadata.json"), "w+")
            file.write(raw_meta)
            file.close()

            if os.path.exists(final_path):
                shutil.rmtree(final_path)
            shutil.copytree(temp_path, final_path)
            shutil.rmtree(dirname)
            os.remove(filename)

        except Exception:
            #self.progress_window.hide()
            e = sys.exc_info()[1]
            print("Error: " + str(e))
            try:
                shutil.rmtree(dirname)
                os.remove(filename)
            except:
                pass
            if not self.abort_download:
                error = _("An error occurred during installation or updating.  You may wish to report this incident to the\
                          developer of %s.\n\nIf this was an update, the previous installation is unchanged") % (error_title), str(detail)
                #self.errorMessage(error)
            return False

        #self.progress_button_abort.set_sensitive(False)
        #self.progress_window.show()
        #install_errors.put([pkg["uuid"], error])
        self.on_install_finished(pkg, total_count, valid_task, error)
        return True

    def show_detail(self, uuid, onSelect=None, onClose=None):
        self.on_detail_select = onSelect
        self.on_detail_close = onClose
        if not self.has_cache:
            self.refresh_cache(False)
        elif len(self.index_cache) == 0:
            self.load_cache()
        if uuid not in self.index_cache:
            self.EmitNeedDetails()
            #self.load(lambda x: self.show_detail(uuid))
            return
        appletData = self.index_cache[uuid] 

        # Browsing the info within the app would be great (ala mintinstall) but until it is fully ready 
        # and it gives a better experience (layout, comments, reviewing) than 
        # browsing online we will open the link with an external browser 
        os.system("xdg-open '%s/%ss/view/%s'" % (URL_SPICES_HOME, self.collection_type, appletData["spices-id"]))
        return
        
        screenshot_filename = os.path.basename(appletData["screenshot"])
        screenshot_path = os.path.join(self.get_cache_folder(), screenshot_filename)
        appletData["screenshot_path"] = screenshot_path
        appletData["screenshot_filename"] = screenshot_filename

        if not os.path.exists(screenshot_path):
            f = open(screenshot_path, "w")
            self.download_url = URL_SPICES_HOME + appletData["screenshot"]
            self.download_with_progressbar(f, screenshot_path, _("Downloading screenshot"), False)

        template = open(os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + "/../data/spices/applet-detail.html")).read()
        subs = {}
        subs["appletData"] = json.dumps(appletData, sort_keys=False, indent=3)
        html = string.Template(template).safe_substitute(subs)

        # Prevent flashing previously viewed
        self._sigLoadFinished = self.browser.connect("document-load-finished", lambda x, y: self.real_show_detail())
        self.browser.load_html_string(html, "file:///")

    def real_show_detail(self):
        self.browser.show()
        self.spiceDetail.show()
        self.browser.disconnect(self._sigLoadFinished)

    def browser_title_changed(self, view, frame, title):
        if title.startswith("nop"):
            return
        elif title.startswith("install:"):
            uuid = title.split(":")[1]
            #self.install(uuid)
        elif title.startswith("uninstall:"):
            uuid = title.split(":")[1]
            #self.uninstall(uuid, "")
        return

    def browser_console_message(self, view, msg, line, sourceid):
        return
        #print(msg)

    def get_members(self, zip):
        parts = []
        for name in zip.namelist():
            if not name.endswith("/"):
                parts.append(name.split("/")[:-1])
        prefix = os.path.commonprefix(parts) or ""
        if prefix:
            prefix = "/".join(prefix) + "/"
        offset = len(prefix)
        for zipinfo in zip.infolist():
            name = zipinfo.filename
            if len(name) > offset:
                zipinfo.filename = name[offset:]
                yield zipinfo

    def uninstall(self, uuid, name, schema_filename, onFinished=None):
        self.progresslabel.set_text(_("Uninstalling %s...") % name)
        self.progress_window.show()
        
        self.progress_bar_pulse()
        try:
            if collect_type != "theme":
                if schema_filename != "":
                    sentence = _("Please enter your password to remove the settings schema for %s") % (uuid)
                    if os.path.exists("/usr/bin/gksu") and os.path.exists("/usr/lib/cinnamon-settings/bin/removeSchema.py"):
                        launcher = "gksu  --message \"<b>%s</b>\"" % sentence
                        tool = "/usr/lib/cinnamon-settings/bin/removeSchema.py %s" % (schema_filename)
                        command = "%s %s" % (launcher, tool)
                        os.system(command)
                    else:
                        self.errorMessage(_("Could not remove the settings schema for %s.  You will have to perform this step yourself.  This is not a critical error.") % (uuid))
                shutil.rmtree(os.path.join(self.install_folder, uuid))

                # Uninstall spice localization files, if any
                if (os.path.exists(locale_inst)):
                    i19_folders = os.listdir(locale_inst)
                    for i19_folder in i19_folders:
                        if os.path.isfile(os.path.join(locale_inst, i19_folder, "LC_MESSAGES", "%s.mo" % uuid)):
                            os.remove(os.path.join(locale_inst, i19_folder, "LC_MESSAGES", "%s.mo" % uuid))
                        # Clean-up this locale folder
                        removeEmptyFolders(os.path.join(locale_inst, i19_folder))

                # Uninstall settings file, if any
                if (os.path.exists(os.path.join(settings_dir, uuid))):
                    shutil.rmtree(os.path.join(settings_dir, uuid))
            else:
                shutil.rmtree(os.path.join(self.install_folder, name))
        except Exception:
            e = sys.exc_info()[1]
            self.progress_window.hide()
            self.errorMessage(_("Problem uninstalling %s.  You may need to manually remove it.") % (uuid), str(e))

        self.progress_window.hide()

        if callable(onFinished):
            onFinished(uuid)

    def on_abort_clicked(self, button):
        self.abort_download = ABORT_USER
        self.progress_window.hide()
        return

    def on_refresh_clicked(self):
        self.load_index()

    def download_with_progressbar(self, outfd, outfile, caption="Please wait..", waitForClose=True):
        self.progressbar.set_fraction(0)
        self.progressbar.set_text("0%")        
        self.progresslabel.set_text(caption)
        self.progress_window.show()

        while Gtk.events_pending():
            Gtk.main_iteration()
        
        self.progress_bar_pulse()
        self.download(outfd, outfile)

        if not waitForClose:
            time.sleep(0.5)
            self.progress_window.hide()
        else:
            self.progress_button_abort.set_sensitive(False)

    def progress_bar_pulse(self):       
        count = 0
        self.progressbar.set_pulse_step(0.1)
        while count < 1:
            time.sleep(0.1)
            self.progressbar.pulse()
            count += 1
            while Gtk.events_pending():
                Gtk.main_iteration()

    def reporthook(self, count, block_size, total_size, user_param):
        # for install user_param = pkg
        if totalSize > 0:
            fraction = float((count*block_size)/total_size);
        #targent = "%s - %d / %d files" % (str(int(fraction*100)) + "%", self.download_current_file, self.download_total_files)
        targent = "%s - %d / %d files"% (str(int(fraction*100)) + "%", 1, 1)
        self.EmitTarget(targent)
        print(str(block_size/total_size))
        '''
        if self.download_total_files > 1:
            fraction = (float(self.download_current_file) / float(self.download_total_files));
            self.progressbar.set_text("%s - %d / %d files" % (str(int(fraction*100)) + "%", self.download_current_file, self.download_total_files))
        else:
            fraction = count * blockSize / float((totalSize / blockSize + 1) *
                (blockSize))
            self.progressbar.set_text(str(int(fraction * 100)) + "%")

        if fraction > 0:
            self.progressbar.set_fraction(fraction)
        else:
            self.progress_bar_pulse()

        while Gtk.events_pending():
            Gtk.main_iteration()
        '''

    def scrubConfigDirs(self, enabled_list):
        active_list = {}
        for enabled in enabled_list:
            if self.collection_type == "applet":
                panel, align, order, uuid, id = enabled.split(":")
            elif self.collection_type == "desklet":
                uuid, id, x, y = enabled.split(":")
            else:
                uuid = enabled
                id = 0
            if uuid not in active_list:
                id_list = []
                active_list[uuid] = id_list
                active_list[uuid].append(id)
            else:
                active_list[uuid].append(id)

        for uuid in active_list.keys():
            if (os.path.exists(os.path.join(settings_dir, uuid))):
                dir_list = os.listdir(os.path.join(settings_dir, uuid))
                for id in active_list[uuid]:
                    fn = str(id) + ".json"
                    if fn in dir_list:
                        dir_list.remove(fn)
                fn = str(uuid) + ".json"
                if fn in dir_list:
                    dir_list.remove(fn)
                for jetsam in dir_list:
                    try:
                        os.remove(os.path.join(settings_dir, uuid, jetsam))
                    except:
                        pass

    def errorMessage(self, msg, detail = None):
        dialog = Gtk.MessageDialog(transient_for = None,
                                   modal = True,
                                   message_type = Gtk.MessageType.ERROR,
                                   buttons = Gtk.ButtonsType.OK)
        markup = msg
        if detail is not None:
            markup += _("\n\nDetails:  %s") % (str(detail))
        esc = cgi.escape(markup)
        dialog.set_markup(esc)
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()

    def on_progress_close(self, widget, event):
        self.abort_download = True
        return widget.hide_on_delete()

    def EmitStatus(self, status, status_translation):
        if status == "":
            status = "DETAILS"
        self.emit("EmitStatus", status, status_translation)

    def EmitRole(self, role):
        self.emit("EmitRole", role)

    def EmitNeedDetails(self, need):
        self.emit("EmitNeedDetails", need)

    def EmitIcon(self, icon):
        self.emit("EmitIcon", icon)

    def EmitTarget(self, target):
        self.emit("EmitTarget", target)

    def EmitPercent(self, percent):
        self.emit("EmitPercent", percent)

    def EmitDownloadPercentChild(self, id, name, percent, details):
        self.emit("EmitDownloadPercentChild", id, name, percent, details)

    def EmitDownloadChildStart(self, restar_all):
        self.emit("EmitDownloadChildStart", restar_all)

    def EmitLogError(self, message):
        self.emit("EmitLogError", message)

    def EmitLogWarning(self, message):
        self.emit("EmitLogWarning", message)

    def EmitAvailableUpdates(self, syncfirst, updates):
        self.emit("EmitAvailableUpdates", syncfirst, updates)

    def EmitTransactionStart(self, message):
        self.emit("EmitTransactionStart", message)

    def EmitTransactionDone(self, message):
        self.emit("EmitTransactionDone", message)

    def EmitTransactionError(self, title, message):
        self.emit("EmitTransactionError", title, message)

    def EmitTransactionConfirmation(self, info_config):
        self.emit("EmitTransactionConfirmation", info_config)

    def EmitTransactionCancellable(self, cancellable):
        self.emit("EmitTransactionCancellable", cancellable)

    def EmitTerminalAttached(self, attached):
        self.emit("EmitTerminalAttached", attached)

    def EmitConflictFile(self, old, new):
        self.emit("EmitConflictFile", old, new)

    def EmitMediumRequired(self, medium, title, desc):
        self.emit("EmitMediumRequired", medium, title, desc)

    def EmitChooseProvider(self, info_prov):
        self.emit("EmitChooseProvider", info_prov)
        #self.client_response = False
        #self.client_condition.acquire()
        #while not self._client_confirm_trans():
        #    self.client_condition.wait()
        #self.client_condition.release()

    def EmitReloadConfig(self, message):
        # recheck aur updates next time
        self.aur_updates_checked = False
        # reload config
        config.installer_conf.reload()
        self.emit("EmitReloadConfig", message)
