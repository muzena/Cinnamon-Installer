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

import os, sys, tempfile, shutil

try:
    try:
        import urllib2
    except:
        import urllib.request as urllib2
    try:
        import json
    except ImportError:
        import simplejson as json
    from gi.repository import Gio, GObject
except Exception:
    e = sys.exc_info()[1]
    print(str(e))
    #sys.exit(1)


home = os.path.expanduser("~")
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

    def get_collection(self, collect_type):
        return self.cache_object[collect_type]

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
                #self.errorMessage(_("Something went wrong with the spices download.  Please try refreshing the list again."), str(str(e)))

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

    def _enabled_extensions_changed(self, setting, key, collect_type):
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
        for uuid in model:
            if collect_type == "theme":
                if model[uuid]["uuid"] == "STOCK":
                    new_uuid = "STOCK"
                else:
                    new_uuid = model[uuid]["name"]
            else:
                new_uuid = model[uuid]["uuid"]
            if(new_uuid in uuidCount):
                model[uuid]["max_instances"] = uuidCount[new_uuid]
            else:
                model[uuid]["max_instances"] = 0
         ##we need to update is_active also.
         #self.emitActiveChange();

    def refresh_cache_type(self, user_param, reporthook=None):
        #self.progressbar.set_fraction(0)
        #self.progress_bar_pulse()
        cache_folder = self.get_cache_folder(user_param[0])
        cache_file = os.path.join(cache_folder, "index.json")
        fd, filename = tempfile.mkstemp()
        f = os.fdopen(fd, 'wb')
        try:
            self._download_file(self.get_index_url(user_param[0]), f, filename, reporthook, user_param)
        except Exception:
            e = sys.exc_info()[1]
            print(str(e))
        if os.path.isfile(filename):
            if self.abort_download > ABORT_NONE:
                os.remove(filename)
            else:
                shutil.move(filename, cache_file)
                self._load_cache_online_type(user_param[0])
                self._update_data_cache_type(user_param[0])
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
                    shutil.move(filename, pkg[0]['icon_path'])
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
                print(_("An error occurred while trying to access the server.  Please try again in a little while."), self.error)
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

       '''

    def url_retrieve(self, url, f, reporthook, user_param):        
        #Like the one in urllib. Unlike urllib.retrieve url_retrieve
        #can be interrupted. KeyboardInterrupt exception is rasied when
        #interrupted.        
        count = 0
        block_size = 1024 * 8
        try:
            urlobj = urllib2.urlopen(url)
        except Exception:
            f.close()
            e = sys.exc_info()[1]
            self.abort_download = ABORT_ERROR
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
                else:
                    print(str(reporthook))
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
