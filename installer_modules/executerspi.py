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

try:
    import gettext
    from datetime import datetime
    from gi.repository import Gio, Gtk, GObject, Gdk, GdkPixbuf
    from threading import Thread
    from multiprocessing import Process, Lock, Queue
    import locale
    import tempfile
    import os
    import sys
    import time
    try:
        import urllib2
    except:
        import urllib.request as urllib2
    import zipfile
    import string
    import shutil
    import cgi
    import subprocess
except Exception:
    e = sys.exc_info()[1]
    print(str(e))
    sys.exit(1)

try:
    import json
except ImportError:
    import simplejson as json

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"
sys.path.append(DIR_PATH)

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

home = os.path.expanduser("~")
locale_inst = '%s/.local/share/locale' % home
settings_dir = '%s/.cinnamon/configs/' % home

URL_SPICES_HOME = "http://cinnamon-spices.linuxmint.com"
URL_SPICES_APPLET_LIST = URL_SPICES_HOME + "/json/applets.json"
URL_SPICES_THEME_LIST = URL_SPICES_HOME + "/json/themes.json"
URL_SPICES_DESKLET_LIST = URL_SPICES_HOME + "/json/desklets.json"
URL_SPICES_EXTENSION_LIST = URL_SPICES_HOME + "/json/extensions.json"

ABORT_NONE = 0
ABORT_ERROR = 1
ABORT_USER = 2

SETTING_TYPE_NONE = 0
SETTING_TYPE_INTERNAL = 1
SETTING_TYPE_EXTERNAL = 2

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

class SpiceCache(GObject.GObject):
    '''
    __gsignals__ = {
        'EmitCacheUpdate': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN, GObject.TYPE_BOOLEAN,)),
        'EmitCacheUpdateError': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN, GObject.TYPE_BOOLEAN,)),
    }
    '''
    def __init__(self):
        GObject.GObject.__init__(self)
        self.valid_types = ['applet','desklet','extension', 'theme'];
        self.cache_object = { 'applet': {}, 'desklet': {}, 'extension': {}, 'theme': {} }
        self.cache_actived = { 'applet': {}, 'desklet': {}, 'extension': {}, 'theme': {} }
        self.cache_installed = { 'applet': {}, 'desklet': {}, 'extension': {}, 'theme': {} }
        self.cache_types_length = len(self.valid_types)
        self.settings = Gio.Settings.new("org.cinnamon")
        self.settingsTheme = Gio.Settings.new("org.cinnamon.theme")

    def get_valid_types(self):
        return self.valid_types

    def is_valid_type(self, collect_type):
        return (self.valid_types.index(collect_type) != -1)

    def get_package_from_collection(self, collect_type, package_uuid):
        if (collect_type in self.cache_installed) and (package_uuid in self.cache_installed[collect_type]):
            return self.cache_installed[collect_type][package_uuid]
        if (collect_type in self.cache_object) and (package_uuid in self.cache_object[collect_type]):
            return self.cache_object[collect_type][package_uuid]
        return self.cache_object[collect_type][package_uuid]

    def load(self):
        for collect_type in self.cache_object:
            self.load_collection_type(collect_type)
        print("init cache")

    def load_collection_type(self, collect_type):
        self._load_cache_actived_type(collect_type)
        self._load_cache_online_type(collect_type)
        self._update_data_cache_type(collect_type)
        self._load_extensions(collect_type)

    def _load_cache_actived_type(self, collect_type):
        if collect_type == "theme":
            self.cache_actived[collect_type] = [self.settingsTheme.get_string("name")]
            #self.settingsTheme.connect("changed::name", lambda x, y: self._enabled_extensions_changed())
            self.settingsTheme.connect("changed::name", self._enabled_extensions_changed, collect_type)
        else:
            self.cache_actived[collect_type] = self.settings.get_strv("enabled-%ss" % (collect_type))
            #self.settings.connect(("changed::enabled-%ss") % (collect_type), lambda x, y: self._enabled_extensions_changed())
            self.settings.connect(("changed::enabled-%ss") % (collect_type), self._enabled_extensions_changed, collect_type)

    def _load_cache_online_type(self, collect_type):
        cache_folder = self.get_cache_folder(collect_type)
        install_folder = self.get_install_folder(collect_type)
        cache_file = os.path.join(cache_folder, "index.json")
        if os.path.exists(cache_file):
            has_cache = True
        else:
            has_cache = False

        if has_cache:
            f = open(cache_file, 'r')
            try:
                self.cache_object[collect_type] = json.load(f)
            except ValueError:
                pass
                try:
                    self.cache_object[collect_type] = {}
                    os.remove(cache_file)
                except:
                    pass
                e = sys.exc_info()[1]
                #self.errorMessage(_("Something went wrong with the spices download.  Please try refreshing the list again."), str(e))

    def _update_data_cache_type(self, collect_type):
        cache_data = self.cache_object[collect_type]
        for uuid in cache_data:
            extensionData = cache_data[uuid]
            if not "uuid" in extensionData:
                extensionData["uuid"] = uuid
            extensionName = extensionData['name'].replace('&', '&amp;')
            extensionDesc = extensionData['description'].replace('&', '&amp;')
            is_active = False
            is_update = True
            installed = False
            if not extensionData["last_edited"]:
                if extensionData["last-edited"]:
                    extensionData["last_edited"] = int(extensionData["last-edited"])
                else:
                    extensionData["last_edited"] = -1
            else:
                extensionData['last_edited'] = int(extensionData['last_edited'])
            if collect_type in self.cache_actived:
                if collect_type == 'theme':
                    if extensionName in self.cache_actived[collect_type]:
                        is_active = True
                elif uuid in self.cache_installed[collect_type]:
                    is_active = True
            if collect_type in self.cache_installed:
                if collect_type == 'theme':
                    if extensionName in self.cache_installed[collect_type]:
                        if self.cache_installed[collect_type][extensionName]['last_edited'] < extensionData["last_edited"]:
                            self.cache_installed[collect_type][extensionName]['is_update'] = False
                            is_update = False
                        else:
                            self.cache_installed[collect_type][extensionName]['is_update'] = True
                        self.cache_installed[collect_type][extensionName]['is_active'] = is_active
                        installed = True
                else:
                    if uuid in self.cache_installed[collect_type]:
                        if self.cache_installed[collect_type][uuid]['last_edited'] < extensionData["last_edited"]:
                            self.cache_installed[collect_type][uuid]['is_update'] = False
                            is_update = False
                        else:
                            self.cache_installed[collect_type][uuid]['is_update'] = True
                        self.cache_installed[collect_type][uuid]['is_active'] = is_active
                        installed = True
            extensionData['is_active'] = is_active
            extensionData["installed"] = installed
            extensionData["is_update"] = is_update

            extensionData['name'] = extensionName
            extensionData['description'] = extensionDesc
            extensionData['enable'] = 0
            extensionData['score'] = int(extensionData['score'])
            extensionData['collection'] = collect_type
        self.load_assets_type(collect_type)
        

    def on_cache_refresh(self, collect_type, cache_data):
        #print("total spices loaded: %d" % len(cache_data))
        self._load_online_cache_type(collect_type)

    def _can_update(self, collect_type, uuid, installed_date):
        object_cache = self.cache_object[collect_type]
        date = -1
        if uuid in object_cache:
            date = object_cache[uuid]["last_edited"]
        can_update = date > installed_date
        return can_update

    def _get_empty_installed(self):
       instance = { 'uuid': "", 'description': "", 'enabled': 0, 'max_instances': 1,
                    'icon': "", 'name': "", 'read_only': True, 'hide-configuration': True,
                    'ext_setting_app': "", 'last_edited': -1, 'read_only_icon': "",
                    'active_icon': "", 'schema_file_name': "", 'settings_type': 0,
                    'is_update': True, 'installed': False, 'is_active': False, 
                    'file': "", 'collection': "" }
       return instance

    def _load_extensions(self, collect_type):
        self.cache_installed = { 'applet': {}, 'desklet': {}, 'extension': {}, 'theme': {} }
        if collect_type == "theme":
            self._load_extensions_in(collect_type, ('%s/.themes') % (home))
            self._load_extensions_in(collect_type, '/usr/share', True)
            self._load_extensions_in(collect_type, '/usr/share/themes')
        else:
            self._load_extensions_in(collect_type, ('%s/.local/share/cinnamon/%ss') % (home, collect_type))
            self._load_extensions_in(collect_type, ('/usr/share/cinnamon/%ss') % (collect_type))

    def _load_extensions_in(self, collect_type, directory, stock_theme = False):
        enabled_extensions = self.cache_actived[collect_type]
        if collect_type == "theme":  # Theme handling
            if os.path.exists(directory) and os.path.isdir(directory):
                if stock_theme:
                    themes = ["cinnamon"]
                else:
                    themes = os.listdir(directory)
                themes.sort()
                for theme in themes:
                    if theme in self.cache_installed[collect_type]:
                        continue
                    try:
                        if stock_theme:
                            path = os.path.join(directory, theme, "theme")
                        else:
                            path = os.path.join(directory, theme, "cinnamon")
                        if os.path.exists(path) and os.path.isdir(path):
                            theme_last_edited = -1
                            theme_uuid = ""
                            metadata = os.path.join(path, "metadata.json")
                            theme_last_edited = "-1"
                            if os.path.exists(metadata):
                                json_data=open(metadata).read()
                                data = json.loads(json_data)  
                                try: theme_last_edited = data["last-edited"]
                                except KeyError: theme_last_edited = "-1"
                                except ValueError: theme_last_edited = "-1"
                                if theme_last_edited == "-1":
                                    try: theme_last_edited = data["last_edited"]
                                    except KeyError: theme_last_edited = "-1"
                                    except ValueError: theme_last_edited = "-1"
                                try: theme_uuid = data["uuid"]
                                except KeyError: theme_uuid = theme
                                except ValueError: theme_uuid = theme
                            theme_last_edited_value = int(theme_last_edited)
                            if stock_theme:
                                theme_name = "Cinnamon"
                                theme_uuid = "STOCK"
                            else:
                                theme_name = theme
                            theme_description = ""
                            found = 0
                            for enabled_theme in enabled_extensions:
                                if enabled_theme == theme_name:
                                    found = 1
                                elif enabled_theme == "" and theme_uuid == "STOCK":
                                    found = 1
                            icon_path = ""
                            if os.path.exists(os.path.join(path, "thumbnail.png")):
                                icon_path = os.path.join(path, "thumbnail.png")
                            else:
                                icon_path = "/usr/lib/cinnamon-settings/data/icons/themes.svg"
                            read_only = os.access(directory, os.W_OK)
                            icon_system = ""
                            if (not read_only):
                                icon_system = "cs-xlet-system"
                            icon = ""
                            if (found):
                                icon = "cs-xlet-installed"
                            is_update = not self._can_update(collect_type, theme_uuid, theme_last_edited_value)
                            if theme_name in self.cache_actived[collect_type]:
                                is_active = True
                            else:
                                is_active = False
                            file_url = ""
                            if theme_name in self.cache_object[collect_type]:
                                file_url = self.cache_object[collect_type][theme_name]["file"]
                            self.cache_installed[collect_type][theme_name] = self._get_empty_installed()
                            self.cache_installed[collect_type][theme_name]["uuid"] = theme_uuid
                            self.cache_installed[collect_type][theme_name]["description"] = theme_name
                            self.cache_installed[collect_type][theme_name]["enabled"] = found
                            self.cache_installed[collect_type][theme_name]["max_instances"] = 1
                            self.cache_installed[collect_type][theme_name]["icon"] = icon_path
                            self.cache_installed[collect_type][theme_name]["name"] = theme_name
                            self.cache_installed[collect_type][theme_name]["read_only"] = read_only
                            self.cache_installed[collect_type][theme_name]["hide-configuration"] = True
                            self.cache_installed[collect_type][theme_name]["ext_setting_app"] = ""
                            self.cache_installed[collect_type][theme_name]["last_edited"] = theme_last_edited_value
                            self.cache_installed[collect_type][theme_name]["read_only_icon"] = icon_system
                            self.cache_installed[collect_type][theme_name]["active_icon"] = icon
                            self.cache_installed[collect_type][theme_name]["schema_file_name"] = ""
                            self.cache_installed[collect_type][theme_name]["settings_type"] = SETTING_TYPE_NONE
                            self.cache_installed[collect_type][theme_name]["installed"] = True
                            self.cache_installed[collect_type][theme_name]["is_update"] = is_update
                            self.cache_installed[collect_type][theme_name]["is_active"] = is_active
                            self.cache_installed[collect_type][theme_name]["file"] = file_url
                            self.cache_installed[collect_type][theme_name]["collection"] = collect_type
                    except Exception:
                        e = sys.exc_info()[1]
                        #print("Failed to load extension %s: %s" % (theme, str(e)))
        else: # Applet, Desklet, Extension handling
            if os.path.exists(directory) and os.path.isdir(directory):
                extensions = os.listdir(directory)
                extensions.sort()
                for extension in extensions:
                    try:
                        if extension in self.cache_installed[collect_type]:
                            continue
                        if os.path.exists("%s/%s/metadata.json" % (directory, extension)):
                            json_data=open("%s/%s/metadata.json" % (directory, extension)).read()
                            setting_type = 0
                            data = json.loads(json_data)  
                            extension_uuid = data["uuid"]
                            extension_name = data["name"]                                        
                            extension_description = data["description"]                          
                            try: extension_max_instances = int(data["max-instances"])
                            except KeyError: extension_max_instances = 1
                            except ValueError: extension_max_instances = 1

                            try: extension_role = data["role"]
                            except KeyError: extension_role = None
                            except ValueError: extension_role = None

                            try: hide_config_button = data["hide-configuration"]
                            except KeyError: hide_config_button = False
                            except ValueError: hide_config_button = False

                            try:
                                ext_config_app = os.path.join(directory, extension, data["external-configuration-app"])
                                setting_type = SETTING_TYPE_EXTERNAL
                            except KeyError: ext_config_app = ""
                            except ValueError: ext_config_app = ""

                            if os.path.exists("%s/%s/settings-schema.json" % (directory, extension)):
                                setting_type = SETTING_TYPE_INTERNAL

                            try: last_edited = data["last-edited"]
                            except KeyError: last_edited = "-1"
                            except ValueError: last_edited = "-1"
                            if last_edited == -1:
                                try: last_edited = data["last_edited"]
                                except KeyError: last_edited = "-1"
                                except ValueError: last_edited = "-1"
                            last_edited_value = int(last_edited)

                            try: schema_filename = data["schema-file"]
                            except KeyError: schema_filename = ""
                            except ValueError: schema_filename = ""

                            if ext_config_app != "" and not os.path.exists(ext_config_app):
                                ext_config_app = ""

                            if extension_max_instances < -1:
                                extension_max_instances = 1
                                
                            found = 0
                            for enabled_extension in enabled_extensions:
                                if extension_uuid in enabled_extension:
                                    found += 1
                            extension_icon = None
                            if "icon" in data:
                                extension_icon = data["icon"]
                            elif os.path.exists("%s/%s/icon.png" % (directory, extension)):
                                extension_icon = "%s/%s/icon.png" % (directory, extension)
                            if extension_icon is None:
                                extension_icon = "cs-%ss" % (collect_type)

                            read_only = os.access(directory, os.W_OK)
                            icon_system = "cs-xlet-system"
                            if (read_only):
                                icon_system = ""
                            icon = ""
                            if (found):
                                icon = "cs-xlet-running"
                            is_update = not self._can_update(collect_type, extension_uuid, last_edited_value)
                            if extension_uuid in self.cache_actived[collect_type]:
                                is_active = True
                            else:
                                is_active = False
                            file_url = ""
                            if extension_uuid in self.cache_object[collect_type]:
                                file_url = self.cache_object[collect_type][extension_uuid]["file"]
                            self.cache_installed[collect_type][extension_uuid] = self._get_empty_installed()
                            self.cache_installed[collect_type][extension_uuid]["uuid"] = extension_uuid
                            self.cache_installed[collect_type][extension_uuid]["description"] = extension_description
                            self.cache_installed[collect_type][extension_uuid]["enabled"] = found
                            self.cache_installed[collect_type][extension_uuid]["max_instances"] = extension_max_instances
                            self.cache_installed[collect_type][extension_uuid]["icon"] = extension_icon
                            self.cache_installed[collect_type][extension_uuid]["name"] = extension_name
                            self.cache_installed[collect_type][extension_uuid]["read_only"] = read_only
                            self.cache_installed[collect_type][extension_uuid]["hide-configuration"] = hide_config_button
                            self.cache_installed[collect_type][extension_uuid]["ext_setting_app"] = ext_config_app
                            self.cache_installed[collect_type][extension_uuid]["last_edited"] = last_edited_value
                            self.cache_installed[collect_type][extension_uuid]["read_only_icon"] = icon_system
                            self.cache_installed[collect_type][extension_uuid]["active_icon"] = icon
                            self.cache_installed[collect_type][extension_uuid]["schema_file_name"] = schema_filename
                            self.cache_installed[collect_type][extension_uuid]["settings_type"] = setting_type
                            self.cache_installed[collect_type][extension_uuid]["installed"] = True
                            self.cache_installed[collect_type][extension_uuid]["is_update"] = is_update
                            self.cache_installed[collect_type][extension_uuid]["is_active"] = is_active
                            self.cache_installed[collect_type][extension_uuid]["file"] = file_url
                            self.cache_installed[collect_type][extension_uuid]["collection"] = collect_type
                    except Exception:
                        e = sys.exc_info()[1]
                        #print("Failed to load extension %s: %s" % (extension, str(e)))

    def _enabled_extensions_changed(self, collect_type):
        #if collect_type != "theme":
        #   self.spices.scrubConfigDirs(self.enabled_extensions)
        if collect_type == "theme":
            self.cache_actived[collect_type] = [self.settings.get_string("name")]
        else:
            self.cache_actived[collect_type] = self.settings.get_strv(("enabled-%ss") % (collect_type))
            uuidCount = {}
            enabled_extensions = self.cache_actived[collect_type]
            for enabled_extension in enabled_extensions:
                try:
                    uuid = self.from_setting_string(collect_type, enabled_extension)
                    if uuid == "":
                        uuid = "STOCK"
                    if uuid in uuidCount:
                        uuidCount[uuid] += 1
                    else:
                        uuidCount[uuid] = 1
                except:
                    pass
        model = self.cache_installed[collect_type]
        for row in self.model:
            if collect_type == "theme":
                if model[row].uuid == "STOCK":
                    uuid = "STOCK"
                else:
                    uuid = model[row].name
            else:
                uuid = model[row].uuid
            if(uuid in uuidCount):
                model[row].max_instances = uuidCount[uuid]
            else:
                model[row].max_instances = 0
         ##we need to update is_active also.
         #self.emitActiveChange();

    def refresh_cache_type(self, collect_type, reporthook=None):
        #self.progressbar.set_fraction(0)
        #self.progress_bar_pulse()
        cache_folder = self.get_cache_folder(collect_type)
        cache_file = os.path.join(cache_folder, "index.json")
        fd, filename = tempfile.mkstemp()
        f = os.fdopen(fd, 'wb')
        try:
            self._download_file(self.get_index_url(collect_type), f, filename, reporthook, collect_type)
        except Exception:
            e = sys.exc_info()[1]
            print(str(e))
        if os.path.isfile(filename):
            if self.abort_download > ABORT_NONE:
                os.remove(filename)
            else:
                shutil.move(filename, cache_file)
                self._load_cache_online_type(collect_type)
                self._update_data_cache_type(collect_type)
        #print("Loaded index, now we know about %d spices." % len(self.index_cache))

    def load_assets_type(self, collect_type, reporthook=None):
        used_thumbs = []
        index_cache = self.cache_object[collect_type]
        cache_folder = self.get_cache_folder(collect_type)
        uuids = index_cache.keys()
        for uuid in uuids:
            if collect_type == "theme":
                icon_basename = self.sanitize_thumb(os.path.basename(index_cache[uuid]['screenshot']))  
            else:
                icon_basename = os.path.basename(index_cache[uuid]['icon'])
            icon_path = os.path.join(cache_folder, icon_basename)
            used_thumbs.append(icon_basename)

            index_cache[uuid]['icon_filename'] = icon_basename
            index_cache[uuid]['icon_path'] = icon_path
            if uuid in self.cache_installed[collect_type]:
                self.cache_installed[collect_type][uuid]['icon_filename'] = icon_basename
                self.cache_installed[collect_type][uuid]['icon_path'] = icon_path

        # Cleanup obsolete thumbs
        trash = []
        flist = os.listdir(cache_folder)
        for f in flist:
            if f not in used_thumbs and f != "index.json":
                trash.append(f)
        for t in trash:
            try:
                os.remove(os.path.join(cache_folder, t))
            except:
                pass

    def get_assets_type_to_refresh(self, collect_type):
        index_cache = self.cache_object[collect_type]
        need_refresh = {}
        uuids = index_cache.keys()
        for uuid in uuids:
            icon_path = index_cache[uuid]['icon_path']
            if not os.path.isfile(icon_path):
                download_url = self.get_assets_url(collect_type, index_cache[uuid])
                need_refresh[download_url] = index_cache[uuid]
        return need_refresh

    def refresh_asset(self, pkg, download_url, reporthook=None):
        if self.abort_download > ABORT_NONE:
            return False
        valid = True
        try:
            urllib2.urlopen(download_url).getcode()
            fd, filename = tempfile.mkstemp()
            f = os.fdopen(fd, 'wb')
            self._download_file(download_url, f, filename, reporthook, pkg)
            if os.path.isfile(filename):
                if self.abort_download > ABORT_NONE:
                    os.remove(filename)
                else:
                    shutil.move(filename, pkg['icon_path'])
                   #self._load_cache_online_type(collect_type)
                   #self._update_data_cache_type(collect_type)
        except Exception:
            valid = False
            e = sys.exc_info()[1]
            print(str(e))
        if not valid:
            #report an error?
            pass
        return valid

    def download_packages(self, pkg, f, filename, reporthook=None):
        try:
            url = URL_SPICES_HOME + pkg['file'];
            self._download_file(url, f, filename, reporthook, pkg)
        except Exception:
            e = sys.exc_info()[1]
            print(str(e))

    def _download_file(self, url, outfd, outfile, reporthook, user_param=None):
        self.abort_download = ABORT_NONE
        try:
            self.url_retrieve(url, outfd, reporthook, user_param)
        except KeyboardInterrupt:
            try:
                os.remove(outfile)
            except OSError:
                pass
            if self.abort_download == ABORT_ERROR:
                print(_("An error occurred while trying to access the server.  Please try again in a little while.") + self.error)
            raise Exception(_("Download aborted."))

        return outfile

    def _reporthook(self, count, blockSize, totalSize, user_param):
        pass
        '''
        if self.download_total_files > 1:
            fraction = (float(self.download_current_file) / float(self.download_total_files));
            self.progressbar.set_text("%s - %d / %d files" % (str(int(fraction*100)) + '%', self.download_current_file, self.download_total_files))
        else:
            fraction = count * blockSize / float((totalSize / blockSize + 1) *
                (blockSize))
            self.progressbar.set_text(str(int(fraction * 100)) + '%')

        if fraction > 0:
            self.progressbar.set_fraction(fraction)
        else:
            self.progress_bar_pulse()

        while Gtk.events_pending():
            Gtk.main_iteration()
       '''

    def url_retrieve(self, url, f, user_param, reporthook):        
        #Like the one in urllib. Unlike urllib.retrieve url_retrieve
        #can be interrupted. KeyboardInterrupt exception is rasied when
        #interrupted.        
        count = 0
        block_size = 1024 * 8
        try:
            urlobj = urllib2.urlopen(url)
        except Exception:
            f.close()
            self.abort_download = ABORT_ERROR
            e = sys.exc_info()[1]
            self.error = str(e)
            raise KeyboardInterrupt
        total_size = int(urlobj.info()['content-length'])

        try:
            while self.abort_download == ABORT_NONE:
                data = urlobj.read(block_size)
                count += 1
                if not data:
                    break
                f.write(data)
                if (reporthook) and (callable(reporthook)):
                    reporthook(count, block_size, total_size, user_param)
        except KeyboardInterrupt:
            f.close()
            self.abort_download = ABORT_USER

        if self.abort_download > ABORT_NONE:
            raise KeyboardInterrupt

        del urlobj
        f.close()

    def sanitize_thumb(self, basename):
        return basename.replace("jpg", "png").replace("JPG", "png").replace("PNG", "png")

    def get_cache_folder(self, collect_type):
        cache_folder = "%s/.cinnamon/spices.cache/%s/" % (home, collect_type)

        if not os.path.exists(cache_folder):
            rec_mkdir(cache_folder)
        return cache_folder

    def get_cache_file(self, collect_type):
        return os.path.join(self.get_cache_folder(collect_type), "index.json")

    def get_install_folder(self, collect_type):
        if collect_type in ['applet','desklet','extension']:
            install_folder = '%s/.local/share/cinnamon/%ss/' % (home, collect_type)
        elif collect_type == 'theme':
            install_folder = '%s/.themes/' % (home)
        return install_folder

    def get_index_url(self, collect_type):
        if collect_type == 'theme':
            return URL_SPICES_THEME_LIST
        elif collect_type == 'extension':
            return URL_SPICES_EXTENSION_LIST
        elif collect_type == 'applet':
            return URL_SPICES_APPLET_LIST
        elif collect_type == 'desklet':
            return URL_SPICES_DESKLET_LIST
        else:
            return None

    def get_assets_url(self, collect_type, package):
        if collect_type == "theme":
            download_url = URL_SPICES_HOME + "/uploads/themes/thumbs/" + package['icon_filename']
        else:
            download_url = URL_SPICES_HOME + package['icon']
        return download_url

    def from_setting_string(self, collect_type, string):
        if collect_type == 'theme':
            return string
        elif collect_type == 'extension':
            return string
        elif collect_type == 'applet':
            panel, side, position, uuid, instanceId = string.split(":")
            return uuid
        elif collect_type == 'desklet':
            uuid, instanceId, x, y = string.split(":")
            return uuid
        else:
            return None

class SpiceExecuter(GObject.GObject):
    __gsignals__ = {
        'EmitTransactionDone': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitTransactionError': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitAvailableUpdates': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN, GObject.TYPE_BOOLEAN,)),
        'EmitAction': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitActionLong': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitNeedDetails': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN,)),
        'EmitIcon': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitTarget': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitPercent': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_FLOAT, GObject.TYPE_OBJECT)),
        'EmitDownloadPercentChild': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_FLOAT, GObject.TYPE_STRING,)),
        'EmitLogError': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_OBJECT,)),
        'EmitLogWarning': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitTransactionStart': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,))
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.cache = SpiceCache()
        self.index_cache = {}
        self.error = None
        self.has_cache = False
        self.collection_type = None
        self.max_process = 3
        self.lock = Lock()
        self.validTypes = self.cache.get_valid_types();
        self.cacheTypesLength = len(self.validTypes)

    def load_cache_async(self):
        for collect_type in self.validTypes:
            thread = Thread(target = self.cache.load_collection_type, args=(collect_type,))
            thread.start()

    def load_cache_sync(self):
        self.cache.load()

    def refresh_cache(self, collect_type, load_assets=True):
        if (collect_type == "all"):
           self._refresh_all_cache()
        #elif (self.cache.is_valid_type(collect_type)):
        #   self.refresh_cache_type(collect_type, load_assets)
        #self.abort_download = ABORT_NONE
        #self.cache.refresh_cache_type(collect_type, load_assets)

    def _refresh_all_cache(self):
        total_count = len(self.validTypes)
        install_errors = {}#Queue()
        valid_task = {}
        for collect_type in self.validTypes:
            valid_task[collect_type] = [Thread(target = self._refresh_cache_type, args=(collect_type, total_count,
                                        valid_task,)), -1, install_errors]
        self._try_start_task(valid_task, self.max_process)
        #for collect_type in self.validTypes:
        #    refresh_cache_type(collect_type, load_assets)

    def _refresh_cache_type(self, collect_type, total_count, valid_task):
        self.cache.refresh_cache_type(collect_type, self.reporthook_refresh)
        self._on_refresh_finished(collect_type, total_count, valid_task, "")

    def reporthook_refresh(self, count, block_size, total_size, user_param):
        print("refresh")

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
            precentText = ('{transferred}/{size}').format(transferred = self.noun, size = self.cacheTypesLength)
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
        print("called refresh_assets " + str(total_count))
        for collect_type in self.validTypes:
            valid_task[collect_type] = [Thread(target = self._refresh_assets_type,
                                        args=(collect_type, total_count, valid_task,)), -1, install_errors]
        self._try_start_task(valid_task, max_process)

    def _refresh_assets_type(self, collect_type, total_count, valid_task):
        assets = self.cache.get_assets_type_to_refresh(collect_type)
        internal_total_count = len(assets.keys())
        print("called refresh_assets_type " + str(internal_total_count))
        if internal_total_count > 0:
            internal_valid_task = {}
            install_errors = {}
            for download_url in assets:
                internal_valid_task[download_url] = [Thread(target = self._refresh_assets_type_async,
                    args=(assets[download_url], collect_type, download_url, internal_total_count, valid_task,
                    internal_valid_task,)), -1, install_errors]
            self._try_start_task(internal_valid_task, self.max_process)
        else:
            self._on_refresh_assets_finished(None, collect_type, "", total_count, valid_task, None)

    def _refresh_assets_type_async(self, package, collect_type, download_url, total_count, valid_task, internal_valid_task):
        self.EmitAction("Downloading")
        self.EmitDownloadPercentChild(str(package["uuid"]), str(package["name"]), 0, str(package['last_edited']))
        self.cache.refresh_asset(package, download_url, self.reporthook_assets)
        error = None
        is_really_finished = self._on_refresh_assets_type_finished(package, download_url, total_count, internal_valid_task, error)
        if (is_really_finished):
            self._on_refresh_assets_finished(package, collect_type, download_url, total_count, valid_task, error)
        print("called refresh_assets_type_async")
        return True

    def reporthook_assets(self, count, block_size, total_size, user_param):
       print("called")
       pass

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
        uuid = pkg['uuid']
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
        uuid = pkg['uuid']
        title = pkg['name']
        error_title = uuid
        try:
            edited_date = pkg['last_edited']
            collect_type = pkg['collection']

            #self.progress_window.show()
            #self.progresslabel.set_text(_("Installing %s...") % (title))
            #self.progressbar.set_fraction(0)
            fd, filename = tempfile.mkstemp()
            dirname = tempfile.mkdtemp()
            f = os.fdopen(fd, 'wb')
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
                file = open(os.path.join(temp_path, "cinnamon", "cinnamon.css"), 'r')
                file.close()

                md = {}
                md["last-edited"] = edited_date
                md["uuid"] = uuid
                raw_meta = json.dumps(md, indent=4)
                final_path = os.path.join(dest, title)
                file = open(os.path.join(temp_path, "cinnamon", "metadata.json"), 'w+')
            else:
                error_title = uuid
                dest = os.path.join(self.cache.get_install_folder(collect_type), uuid)
                schema_filename = ""
                zip.extractall(dirname, self.get_members(zip))
                for file in self.get_members(zip):
                    if not (file.filename.endswith('/')): #and ((file.external_attr >> 16L) & 0o755) == 0o755:
                        os.chmod(os.path.join(dirname, file.filename), 0o755)
                    elif file.filename[:3] == 'po/':
                        parts = os.path.splitext(file.filename)
                        if parts[1] == '.po':
                           this_locale_dir = os.path.join(locale_inst, parts[0][3:], 'LC_MESSAGES')
                           #self.progresslabel.set_text(_("Installing translations for %s...") % title)
                           rec_mkdir(this_locale_dir)
                           #print("/usr/bin/msgfmt -c %s -o %s" % (os.path.join(dest, file.filename), os.path.join(this_locale_dir, '%s.mo' % uuid)))
                           subprocess.call(["msgfmt", "-c", os.path.join(dirname, file.filename), "-o", os.path.join(this_locale_dir, '%s.mo' % uuid)])
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
                file = open(os.path.join(dirname, "metadata.json"), 'r')
                raw_meta = file.read()
                file.close()
                md = json.loads(raw_meta)
                md["last-edited"] = edited_date
                if schema_filename != "":
                    md["schema-file"] = schema_filename
                raw_meta = json.dumps(md, indent=4)
                temp_path = dirname
                final_path = dest
                file = open(os.path.join(dirname, "metadata.json"), 'w+')
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

    def EmitAction(self, action):
        self.emit("EmitAction", action)

    def EmitActionLong(self, action):
        self.emit("EmitActionLong", action)

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

    def EmitTransactionError(self, message):
        self.emit("EmitTransactionError", message)

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
        os.system("xdg-open '%s/%ss/view/%s'" % (URL_SPICES_HOME, self.collection_type, appletData['spices-id']))
        return
        
        screenshot_filename = os.path.basename(appletData['screenshot'])
        screenshot_path = os.path.join(self.get_cache_folder(), screenshot_filename)
        appletData['screenshot_path'] = screenshot_path
        appletData['screenshot_filename'] = screenshot_filename

        if not os.path.exists(screenshot_path):
            f = open(screenshot_path, 'w')
            self.download_url = URL_SPICES_HOME + appletData['screenshot']
            self.download_with_progressbar(f, screenshot_path, _("Downloading screenshot"), False)

        template = open(os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + "/../data/spices/applet-detail.html")).read()
        subs = {}
        subs['appletData'] = json.dumps(appletData, sort_keys=False, indent=3)
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
            uuid = title.split(':')[1]
            #self.install(uuid)
        elif title.startswith("uninstall:"):
            uuid = title.split(':')[1]
            #self.uninstall(uuid, '')
        return

    def browser_console_message(self, view, msg, line, sourceid):
        return
        #print(msg)

    def get_members(self, zip):
        parts = []
        for name in zip.namelist():
            if not name.endswith('/'):
                parts.append(name.split('/')[:-1])
        prefix = os.path.commonprefix(parts) or ''
        if prefix:
            prefix = '/'.join(prefix) + '/'
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
                        if os.path.isfile(os.path.join(locale_inst, i19_folder, 'LC_MESSAGES', "%s.mo" % uuid)):
                            os.remove(os.path.join(locale_inst, i19_folder, 'LC_MESSAGES', "%s.mo" % uuid))
                        # Clean-up this locale folder
                        removeEmptyFolders(os.path.join(locale_inst, i19_folder))

                # Uninstall settings file, if any
                if (os.path.exists(os.path.join(settings_dir, uuid))):
                    shutil.rmtree(os.path.join(settings_dir, uuid))
            else:
                shutil.rmtree(os.path.join(self.install_folder, name))
        except Exception:
            self.progress_window.hide()
            e = sys.exc_info()[1]
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

    def download_with_progressbar(self, outfd, outfile, caption='Please wait..', waitForClose=True):
        self.progressbar.set_fraction(0)
        self.progressbar.set_text('0%')        
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
        #targent = "%s - %d / %d files" % (str(int(fraction*100)) + '%', self.download_current_file, self.download_total_files)
        targent = "%s - %d / %d files"% (str(int(fraction*100)) + '%', 1, 1)
        self.EmitTarget(targent)
        print(str(block_size/total_size))
        '''
        if self.download_total_files > 1:
            fraction = (float(self.download_current_file) / float(self.download_total_files));
            self.progressbar.set_text("%s - %d / %d files" % (str(int(fraction*100)) + '%', self.download_current_file, self.download_total_files))
        else:
            fraction = count * blockSize / float((totalSize / blockSize + 1) *
                (blockSize))
            self.progressbar.set_text(str(int(fraction * 100)) + '%')

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
