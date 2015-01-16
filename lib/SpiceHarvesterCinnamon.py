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

import os, sys

try:
    import gettext
    from gi.repository import Gio, Gtk, GObject, Gdk, GdkPixbuf
    # WebKit requires gir1.2-javascriptcoregtk-3.0 and gir1.2-webkit-3.0
    # try:
    #     from gi.repository import WebKit
    #     HAS_WEBKIT=True
    # except:
    #     HAS_WEBKIT=False
    #     print("WebKit not found on this system. These packages are needed for adding spices:")
    #     print("  gir1.2-javascriptcoregtk-3.0")
    #     print("  gir1.2-webkit-3.0")
    import locale
    import tempfile
    import time
    import urllib2
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

import SpicesInstaller

home = os.path.expanduser("~")
locale_inst = "%s/.local/share/locale" % home
settings_dir = "%s/.cinnamon/configs/" % home

URL_SPICES_HOME = "http://cinnamon-spices.linuxmint.com"
URL_SPICES_APPLET_LIST = URL_SPICES_HOME + "/json/applets.json"
URL_SPICES_THEME_LIST = URL_SPICES_HOME + "/json/themes.json"
URL_SPICES_DESKLET_LIST = URL_SPICES_HOME + "/json/desklets.json"
URL_SPICES_EXTENSION_LIST = URL_SPICES_HOME + "/json/extensions.json"

ABORT_NONE = 0
ABORT_ERROR = 1
ABORT_USER = 2

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

class Spice_Harvester_Cinnamon(SpicesInstaller.Spice_Harvester):
    def __init__(self, collection_type, window, builder, parent):
        SpicesInstaller.Spice_Harvester.__init__(self, collection_type, window, builder)
        self.parent = parent

    def get_cache_folder(self):
        cache_folder = "%s/.cinnamon/spices.cache/%s/" % (home, self.collection_type)
        if not os.path.exists(cache_folder):
            rec_mkdir(cache_folder)
        return cache_folder

    def load(self, onDone, force=False):
        self.abort_download = ABORT_NONE
        if (self.has_cache and not force):
            self.load_cache()
        elif force:
            self.parent.emit("EmitTransactionStart", _("Refreshing index..."))
            self.refresh_cache()
            self.parent.emit("EmitTransactionDone", "")
        onDone(self.index_cache)

    def refresh_cache(self, load_assets=True):
        self.download_url = self.get_index_url()
        self.parent.emit("EmitPercent", 2)

        filename = os.path.join(self.cache_folder, "index.json")
        f = open(filename, "w")
        self.download(f, filename)
        
        self.load_cache()
        #print("Loaded index, now we know about %d spices." % len(self.index_cache))
        
        if load_assets:
            self.load_assets()

    def load_assets(self):
        #self.progresslabel.set_text(_("Refreshing cache..."))
        #self.progress_button_abort.set_sensitive(True)
        self.parent.emit("EmitTransactionStart", _("Refreshing index..."))
        self.parent.emit("EmitTransactionCancellable", True)

        needs_refresh = 0
        used_thumbs = []

        uuids = self.index_cache.keys()

        for uuid in uuids:
            if not self.themes:
                icon_basename = os.path.basename(self.index_cache[uuid]["icon"])
                icon_path = os.path.join(self.cache_folder, icon_basename)
                used_thumbs.append(icon_basename)
            else:
                icon_basename = self.sanitize_thumb(os.path.basename(self.index_cache[uuid]["screenshot"]))
                icon_path = os.path.join(self.cache_folder, icon_basename)
                used_thumbs.append(icon_basename)

            self.index_cache[uuid]["icon_filename"] = icon_basename
            self.index_cache[uuid]["icon_path"] = icon_path

            if not os.path.isfile(icon_path):
                needs_refresh += 1

        self.download_total_files = needs_refresh
        self.download_current_file = 0

        for uuid in uuids:
            if self.abort_download > ABORT_NONE:
                return

            icon_path = self.index_cache[uuid]["icon_path"]
            if not os.path.isfile(icon_path):
                #self.progress_bar_pulse()
                self.download_current_file += 1
                f = open(icon_path, "w")
                if not self.themes:
                    self.download_url = URL_SPICES_HOME + self.index_cache[uuid]["icon"]
                else:
                    self.download_url = URL_SPICES_HOME + "/uploads/themes/thumbs/" + self.index_cache[uuid]["icon_filename"]
                valid = True
                try:
                    urllib2.urlopen(self.download_url).getcode()
                except:
                    valid = False
                if valid:
                    self.download(f, icon_path)

        # Cleanup obsolete thumbs
        trash = []
        flist = os.listdir(self.cache_folder)
        for f in flist:
            if f not in used_thumbs and f != "index.json":
                trash.append(f)
        for t in trash:
            try:
                os.remove(os.path.join(self.cache_folder, t))
            except:
                pass

        #self.progress_window.hide()
        self.parent.emit("EmitTransactionDone", "")

        self.download_total_files = 0
        self.download_current_file = 0

    def download(self, outfd, outfile):
        url = self.download_url
        #self.progress_button_abort.set_sensitive(True)
        self.parent.emit("EmitTransactionCancellable", True)
        try:
            self.url_retrieve(url, outfd, self.reporthook)
        except KeyboardInterrupt:
            try:
                os.remove(outfile)
            except OSError:
                pass
            #self.progress_window.hide()
            self.parent.emit("EmitTransactionDone", "Error")
            if self.abort_download == ABORT_ERROR:
                #self.errorMessage(_("An error occurred while trying to access the server.  Please try again in a little while."), self.error)
                self.parent.emit("EmitTransactionError", _("An error occurred while trying to access the server.  Please try again in a little while."), "")
            raise Exception(_("Download aborted."))

        return outfile
        
    def refresh_cache_silent(self):
        download_url = self.get_index_url()
        fd, filename = tempfile.mkstemp()
        f = open(filename, "w")
        self.download_silent(f, filename, download_url)
        print("download finished")
        #self.load_cache()
        #print("Loaded index, now we know about %d spices." % len(self.index_cache))

    def _deepEquals(self, o1, o2, uuid, root): #need to be compare all property, to know who uuid need an update.
        result = True
        k1 = o1.keys().sort()
        k2 = o2.keys().sort()
        if (len(k1) != len(k2)):
            if (uuid):
                root[uuid] = {"category": "", "action": ""}
            else:
                maxval = k1
                minval = k2
                if (len(k2) > len(k1)):
                    maxval = k2
                    minval = k1
                for i in maxval:
                    if (minval.index(maxval[i]) == -1):
                        root[maxval[i]] = {"category": "", "action": ""}
            return False
        for i in k1:
            level = k1[i]
            if (type(o1[level]) != type(o2[level])):
                if (uuid):
                    root[uuid] = {"category": "", "action": ""}
                else:
                    root[level] = {"category": "", "action": ""}
                result = False
            else:
                if (type(o1[level]) == dict):
                    if (uuid):
                        ret = this._deepEquals(o1[level], o2[level], uuid, root)
                    else:
                        ret = this._deepEquals(o1[level], o2[level], level, root)
                    if (not ret):
                        result = False
                elif (o1[level] != o2[level]):
                    if (uuid):
                        root[uuid] = {"category": "", "action": ""}
                    else:
                        root[level] = {"category": "", "action": ""}
                    result = False
        return result

    def download_silent(self, outfd, outfile, url):
        try:
            self.url_retrieve(url, outfd, self.silentReporthook)
        except KeyboardInterrupt:
            try:
                os.remove(outfile)
            except OSError:
                pass
        return outfile

    def reporthook(self, count, blockSize, totalSize):
        if self.download_total_files > 1:
            fraction = (float(self.download_current_file) / float(self.download_total_files));
            self.parent.emit("EmitTarget", "%s - %d / %d files" % (str(int(fraction*100)) + "%", self.download_current_file, self.download_total_files))
        else:
            fraction = count * blockSize / float((totalSize / blockSize + 1) * (blockSize))
            self.parent.emit("EmitTarget", str(int(fraction * 100)) + "%")

        if fraction > 0:
             self.parent.emit("EmitPercent", fraction)
        else:
             self.parent.emit("EmitPercent", 2)

        #while Gtk.events_pending():
        #    Gtk.main_iteration()

    def silentReporthook(self, count, blockSize, totalSize):
        pass
