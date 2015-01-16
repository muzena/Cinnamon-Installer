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

import os, sys, tempfile, time, shutil

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
        "EmitCacheUpdate": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN, GObject.TYPE_BOOLEAN,)),
        "EmitCacheUpdateError": (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN, GObject.TYPE_BOOLEAN,)),
    }
    '''
    def __init__(self):
        GObject.GObject.__init__(self)
        self.valid_types = ["applet","desklet","extension", "theme"];
        self.cache_object = { "applet": {}, "desklet": {}, "extension": {}, "theme": {} }
        self.cache_installed = { "applet": {}, "desklet": {}, "extension": {}, "theme": {} }
        self.cache_is_load = { "applet": False, "desklet": False, "extension": False, "theme": False }
        self.cache_types_length = len(self.valid_types)

    def get_valid_types(self):
        return self.valid_types

    def is_valid_type(self, collect_type):
        return (self.valid_types.index(collect_type) != -1)

    def get_local_packages(self, collect_type=None):
        if collect_type:
            return self.cache_installed[collect_type]
        else:
            return self.cache_installed

    def get_remote_packages(self, collect_type=None):
        if collect_type:
            return self.cache_object[collect_type]
        else:
            return self.cache_object

    def is_load(self, collect_type=None):
        if collect_type:
            return self.cache_is_load[collect_type]
        else:
            for collect_type in self.valid_types:
                if self.is_load(collect_type):
                    return True
            return False

    def get_package_from_collection(self, collect_type, package_uuid):
        if (collect_type in self.cache_installed) and (package_uuid in self.cache_installed[collect_type]):
            return self.cache_installed[collect_type][package_uuid]
        if (collect_type in self.cache_object) and (package_uuid in self.cache_object[collect_type]):
            return self.cache_object[collect_type][package_uuid]
        return self.cache_object[collect_type][package_uuid]

    def load(self, callback=None):
        for collect_type in self.cache_object:
            self.load_collection_type(collect_type, callback)
        print("init cache")

    def load_collection_type(self, collect_type, callback=None):
        self._load_cache_online_type(collect_type)
        self._load_extensions(collect_type)
        self._update_data_cache_type(collect_type)
        if callback and callable(callback):
            callback()
        self.cache_is_load[collect_type] = True

    def _load_cache_online_type(self, collect_type):
        self.cache_object = { "applet": {}, "desklet": {}, "extension": {}, "theme": {} }
        cache_folder = self.get_cache_folder(collect_type)
        cache_file = os.path.join(cache_folder, "index.json")
        if os.path.exists(cache_file):
            f = open(cache_file, "r")
            try:
                self.cache_object[collect_type] = json.load(f)
            except ValueError:
                pass
                try:
                    self.cache_object[collect_type] = { "applet": {}, "desklet": {}, "extension": {}, "theme": {} }
                    os.remove(cache_file)
                except:
                    pass
                e = sys.exc_info()[1]
                print("Please try refreshing the list again. The online cache for %s is corrupted. %s" % (collect_type, str(e)))
                #self.errorMessage(_("Something went wrong with the spices download.  Please try refreshing the list again."), str(e))
        else:
            print("The online cache for %s is empty" % (collect_type))
            self.cache_object[collect_type] = { "applet": {}, "desklet": {}, "extension": {}, "theme": {} }

    def _update_data_cache_type(self, collect_type):
        cache_data = self.cache_object[collect_type]
        transitionData = {}
        for uuid in cache_data:
            extensionData = cache_data[uuid]
            if collect_type == "theme":
                data = extensionData["name"].replace("&", "&amp;")
                try:
                    data = data.encode("UTF-8")
                except:
                    data = str(data)
                remplace_uuid = str.lower(data)
                transitionData[remplace_uuid] = extensionData
                extensionData["hide-configuration"] = True
            else:
                remplace_uuid = uuid
                extensionData["hide-configuration"] = False
            extensionData["uuid"] = str(uuid)
            extensionData["settings-type"] = SETTING_TYPE_NONE
            extensionData["ext-setting-app"] = ""
            extensionData["schema-file"] = ""
            extensionDesc = extensionData["description"].replace("&", "&amp;")
            if "spices-id" in extensionData:
                extensionData["spices-show"] = "'%s/%ss/view/%s'" % (URL_SPICES_HOME, collect_type, extensionData["spices-id"])
            else:
                extensionData["spices-show"] = ""
            install_edited = -1
            installed_folder = ""
            max_instances = 1
            score = 0
            self._fix_last_edited(extensionData)

            try: extensionData["score"] = int(extensionData["score"])
            except Exception: extensionData["score"] = 0
            if collect_type in self.cache_installed:
                if remplace_uuid in self.cache_installed[collect_type]:
                    installed_ext = self.cache_installed[collect_type][remplace_uuid]
                    if installed_ext["uuid"] == "cinnamon":
                        print("Seraaaa> " + str(installed_ext["uuid"]))
                    install_edited = installed_ext["install-edited"]
                    if "last-edited" in extensionData:
                        installed_ext["last-edited"] = extensionData["last-edited"]
                    installed_folder = installed_ext["installed-folder"]
                    max_instances = installed_ext["max-instances"]
                    installed_ext["score"] = extensionData["score"]
                    installed_ext["file"] = extensionData["file"]
                    installed_ext["spices-show"] = extensionData["spices-show"]
                    extensionData["hide-configuration"] = installed_ext["hide-configuration"]
                    extensionData["settings-type"] = installed_ext["settings-type"]
                    extensionData["ext-setting-app"] = installed_ext["ext-setting-app"]
                    extensionData["schema-file"] = installed_ext["schema-file"]
            extensionData["installed-folder"] = installed_folder
            extensionData["install-edited"] = install_edited

            if "max-instances" in extensionData:
                try: max_instances = int(extensionData["max-instances"])
                except Exception: max_instances = 1
            if max_instances < -1:
                max_instances = 1
            extensionData["max-instances"] = max_instances
            extensionData["name"] = extensionData["name"].replace("&", "&amp;")
            extensionData["description"] = extensionDesc
            extensionData["collection"] = collect_type
            extensionData["ext-setting-app"] = ""
        if collect_type == "theme":
            self.cache_object[collect_type] = transitionData
        self.load_assets_type(collect_type)

    def on_cache_refresh(self, collect_type, cache_data):
        #print("total spices loaded: %d" % len(cache_data))
        self._load_online_cache_type(collect_type)

    def is_update(self, collect_type, uuid):
        if uuid in self.cache_object[collect_type]:
            return self.cache_object[uuid]["last-edited"] > self.cache_object[uuid]["install-edited"]
        elif uuid in self.cache_installed[collect_type]:
            return self.cache_installed[uuid]["last-edited"] > self.cache_installed[uuid]["install-edited"]
        return False

    def _fix_last_edited(self, cache_data):
        if "last_edited" in cache_data:
            cache_data["last-edited"] = cache_data["last_edited"]
            del cache_data["last_edited"]
        if not "last-edited" in cache_data:
            cache_data["last-edited"] = -1
        else:
            try:
                cache_data["last-edited"] = long(cache_data["last-edited"])
            except:
                try:
                    cache_data["last-edited"] = int(cache_data["last-edited"])
                except:
                    cache_data["last-edited"] = -1
        return cache_data["last-edited"]

    def _get_empty_installed(self):
       instance = { "uuid": "", "description": "", "max-instances": 1, "spices-show": "",
                    "icon": "", "name": "", "hide-configuration": True,
                    "ext-setting-app": "", "last-edited": -1, "schema-file": "",
                    "settings-type": 0, "install-edited": -1, "installed-folder": "", 
                    "file": "", "collection": "" }
       return instance

    def _load_extensions(self, collect_type):
        self.cache_installed = { "applet": {}, "desklet": {}, "extension": {}, "theme": {} }
        if collect_type == "theme":
            self._load_extensions_in(collect_type, ("%s/.themes") % (home))
            self._load_extensions_in(collect_type, "/usr/share", True)
            self._load_extensions_in(collect_type, "/usr/share/themes")
        else:
            self._load_extensions_in(collect_type, ("%s/.local/share/cinnamon/%ss") % (home, collect_type))
            self._load_extensions_in(collect_type, ("/usr/share/cinnamon/%ss") % (collect_type))

    def _load_extensions_in(self, collect_type, directory, stock_theme = False):
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
                            install_folder = os.path.join(directory, theme, "theme")
                        else:
                            install_folder = os.path.join(directory, theme, "cinnamon")
                        if os.path.exists(install_folder) and os.path.isdir(install_folder):
                            theme_uuid = theme
                            metadata = os.path.join(install_folder, "metadata.json")
                            last_edited = -1
                            spices_show = ""
                            if os.path.exists(metadata):
                                json_data=open(metadata).read()
                                data = json.loads(json_data)  
                                last_edited = self._fix_last_edited(data)
                                if last_edited == -1:
                                    last_edited = os.path.getmtime("%s/metadata.json" % install_folder)
                                try: theme_uuid = str(data["uuid"])
                                except KeyError: theme_uuid = theme
                                except ValueError: theme_uuid = theme
                                try: spices_show = data["spices-id"]
                                except KeyError: spices_show = None
                                except ValueError: spices_show = None
                                if spices_show:
                                    spices_show = "'%s/%ss/view/%s'" % (URL_SPICES_HOME, collect_type, spices_show)

                            if last_edited == -1:
                                if os.path.exists("%s/cinnamon.css" % install_folder):
                                    last_edited = os.path.getmtime("%s/cinnamon.css" % install_folder)

                            if stock_theme:
                                theme_name = "Cinnamon"
                                theme_uuid = "STOCK"
                            else:
                                theme_name = theme
                            index_id = str.lower(theme_name);
                            theme_description = ""
                            icon = ""
                            if os.path.exists(os.path.join(install_folder, "thumbnail.png")):
                                icon = os.path.join(install_folder, "thumbnail.png")
                            else:
                                icon = "/usr/lib/cinnamon-settings/data/icons/themes.svg"

                            self.cache_installed[collect_type][index_id] = {}
                            self.cache_installed[collect_type][index_id]["uuid"] = theme_uuid
                            self.cache_installed[collect_type][index_id]["description"] = theme_name
                            self.cache_installed[collect_type][index_id]["max-instances"] = 1
                            self.cache_installed[collect_type][index_id]["icon"] = icon
                            self.cache_installed[collect_type][index_id]["name"] = theme_name
                            self.cache_installed[collect_type][index_id]["hide-configuration"] = True
                            self.cache_installed[collect_type][index_id]["ext-setting-app"] = ""
                            self.cache_installed[collect_type][index_id]["last-edited"] = -1
                            self.cache_installed[collect_type][index_id]["spices-show"] = spices_show
                            self.cache_installed[collect_type][index_id]["schema-file"] = ""
                            self.cache_installed[collect_type][index_id]["settings-type"] = SETTING_TYPE_NONE
                            self.cache_installed[collect_type][index_id]["installed-folder"] = install_folder
                            self.cache_installed[collect_type][index_id]["install-edited"] = last_edited
                            self.cache_installed[collect_type][index_id]["file"] = ""
                            self.cache_installed[collect_type][index_id]["collection"] = collect_type
                            self.cache_installed[collect_type][index_id]["score"] = 0
                    except Exception:
                        e = sys.exc_info()[1]
                        print("Failed to load extension %s: %s" % (theme, str(e)))
        else: # Applet, Desklet, Extension handling
            if os.path.exists(directory) and os.path.isdir(directory):
                extensions = os.listdir(directory)
                extensions.sort()
                for extension in extensions:
                    try:
                        if extension in self.cache_installed[collect_type]:
                            continue
                        install_folder = "%s/%s" % (directory, extension)
                        if os.path.exists("%s/metadata.json" % install_folder):
                            json_data=open("%s/metadata.json" % install_folder).read()
                            setting_type = 0
                            data = json.loads(json_data)  
                            extension_uuid = data["uuid"]
                            extension_name = data["name"]                                        
                            extension_description = data["description"]                          
                            try: max_instances = int(data["max-instances"])
                            except KeyError: max_instances = 1
                            except ValueError: max_instances = 1
                            if max_instances < -1:
                                max_instances = 1

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

                            if os.path.exists("%s/settings-schema.json" % install_folder):
                                setting_type = SETTING_TYPE_INTERNAL

                            last_edited = self._fix_last_edited(data)
                            if last_edited == -1:
                                last_edited = os.path.getmtime("%s/metadata.json" % install_folder)
                            try: schema_filename = data["schema-file"]
                            except KeyError: schema_filename = ""
                            except ValueError: schema_filename = ""

                            if ext_config_app != "" and not os.path.exists(ext_config_app):
                                ext_config_app = ""

                            extension_icon = None
                            if "icon" in data:
                                extension_icon = data["icon"]
                            elif os.path.exists("%s/icon.png" % install_folder):
                                extension_icon = "%s/icon.png" % install_folder
                            if extension_icon is None:
                                extension_icon = "cs-%ss" % (collect_type)

                            self.cache_installed[collect_type][extension_uuid] = self._get_empty_installed()
                            self.cache_installed[collect_type][extension_uuid]["uuid"] = extension_uuid
                            self.cache_installed[collect_type][extension_uuid]["description"] = extension_description
                            self.cache_installed[collect_type][extension_uuid]["max-instances"] = max_instances
                            self.cache_installed[collect_type][extension_uuid]["icon"] = extension_icon
                            self.cache_installed[collect_type][extension_uuid]["name"] = extension_name
                            self.cache_installed[collect_type][extension_uuid]["hide-configuration"] = hide_config_button
                            self.cache_installed[collect_type][extension_uuid]["ext-setting-app"] = ext_config_app
                            self.cache_installed[collect_type][extension_uuid]["last-edited"] = -1
                            self.cache_installed[collect_type][extension_uuid]["schema-file"] = schema_filename
                            self.cache_installed[collect_type][extension_uuid]["settings-type"] = setting_type
                            self.cache_installed[collect_type][extension_uuid]["installed-folder"] = install_folder
                            self.cache_installed[collect_type][extension_uuid]["install-edited"] = last_edited
                            self.cache_installed[collect_type][extension_uuid]["file"] = ""
                            self.cache_installed[collect_type][extension_uuid]["collection"] = collect_type
                            self.cache_installed[collect_type][extension_uuid]["score"] = 0
                    except Exception:
                        e = sys.exc_info()[1]
                        print("Failed to load extension of %s: %s" % (extension, str(e)))

    def refresh_cache_type(self, user_param, reporthook=None):
        #self.progressbar.set_fraction(0)
        #self.progress_bar_pulse()
        cache_folder = self.get_cache_folder(user_param[0])
        cache_file = os.path.join(cache_folder, "index.json")
        fd, filename = tempfile.mkstemp()
        f = os.fdopen(fd, "wb")
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
                icon_basename = self.sanitize_thumb(os.path.basename(index_cache[uuid]["screenshot"]))  
            else:
                icon_basename = os.path.basename(index_cache[uuid]["icon"])
            icon_path = os.path.join(cache_folder, icon_basename)
            used_thumbs.append(icon_basename)

            index_cache[uuid]["icon_filename"] = icon_basename
            index_cache[uuid]["icon_path"] = icon_path
            index_cache[uuid]["icon"] = icon_path
            if uuid in self.cache_installed[collect_type]:
                self.cache_installed[collect_type][uuid]["icon_filename"] = icon_basename
                self.cache_installed[collect_type][uuid]["icon_path"] = icon_path

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
            icon_path = index_cache[uuid]["icon_path"]
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
            f = os.fdopen(fd, "wb")
            self._download_file(download_url, f, filename, reporthook, pkg)
            if os.path.isfile(filename):
                if self.abort_download > ABORT_NONE:
                    os.remove(filename)
                else:
                    shutil.move(filename, pkg[0]["icon_path"])
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
            url = URL_SPICES_HOME + pkg["file"];
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
            self.progressbar.set_text("%s - %d / %d files" % (str(int(fraction*100)) + "%", self.download_current_file, self.download_total_files))
        else:
            fraction = count * blockSize / float((totalSize / blockSize + 1) *
                (blockSize))
            self.progressbar.set_text(str(int(fraction * 100)) + "%")

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
        total_size = int(urlobj.info()["content-length"])

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
        if collect_type in ["applet","desklet","extension"]:
            install_folder = "%s/.local/share/cinnamon/%ss/" % (home, collect_type)
        elif collect_type == "theme":
            install_folder = "%s/.themes/" % (home)
        return install_folder

    def get_index_url(self, collect_type):
        if collect_type == "theme":
            return URL_SPICES_THEME_LIST
        elif collect_type == "extension":
            return URL_SPICES_EXTENSION_LIST
        elif collect_type == "applet":
            return URL_SPICES_APPLET_LIST
        elif collect_type == "desklet":
            return URL_SPICES_DESKLET_LIST
        else:
            return None

    def get_assets_url(self, collect_type, package):
        if collect_type == "theme":
            download_url = URL_SPICES_HOME + "/uploads/themes/thumbs/" + package["icon_filename"]
        else:
            download_url = URL_SPICES_HOME + package["icon"]
        return download_url

    def from_setting_string(self, collect_type, string):
        if collect_type == "theme":
            return string
        elif collect_type == "extension":
            return string
        elif collect_type == "applet":
            panel, side, position, uuid, instanceId = string.split(":")
            return uuid
        elif collect_type == "desklet":
            uuid, instanceId, x, y = string.split(":")
            return uuid
        else:
            return None
