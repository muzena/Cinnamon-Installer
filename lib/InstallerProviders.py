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

try:
    from threading import Thread, Lock
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
    import types
    import gettext
    import locale
    import tempfile
    import os
    import sys
    import time
    import zipfile
    import string
    import shutil
    import cgi
    import subprocess
    try:
        import urllib2
    except:
        import urllib.request as urllib2
except Exception:
    e = sys.exc_info()[1]
    print(str(e))
    sys.exit(1)

try:
    import json
except ImportError:
    import simplejson as json

home = os.path.expanduser("~")
locale_inst = '%s/.local/share/locale' % home
settings_dir = '%s/.cinnamon/configs/' % home

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(os.path.dirname(ABS_PATH)) + "/"

URL_SPICES_HOME = "http://cinnamon-spices.linuxmint.com"
URL_SPICES_APPLET_LIST = URL_SPICES_HOME + "/json/applets.json"
URL_SPICES_THEME_LIST = URL_SPICES_HOME + "/json/themes.json"
URL_SPICES_DESKLET_LIST = URL_SPICES_HOME + "/json/desklets.json"
URL_SPICES_EXTENSION_LIST = URL_SPICES_HOME + "/json/extensions.json"

ABORT_NONE = 0
ABORT_ERROR = 1
ABORT_USER = 2

CI_STATUS = {
    'RESOLVING_DEPENDENCIES': "Resolving dep",
    'SETTING_UP': "Setting up",
    'LOADING_CACHE': "Loading cache",
    'AUTHENTICATING': "authenticating",
    'DOWNLOADING': "Downloading",
    'DOWNLOADING_REPO': "Downloading repo",
    'RUNNING': "Running",
    'COMMITTING': "Committing",
    'INSTALLING': "Installing",
    'REMOVING': "Removing",
    'CHECKING': "Checking",
    'FINISHED': "Finished",
    'WAITING': "Waiting",
    'WAITING_LOCK': "Waiting lock",
    'WAITING_MEDIUM': "Waiting medium",
    'WAITING_CONFIG_FILE': "Waiting config file",
    'CANCELLING': "Cancelling",
    'CLEANING_UP': "Cleaning up",
    'QUERY': "Query",
    'DETAILS': "Details",
    'UNKNOWN': "Unknown"
}

import ExecuterSpi as executer

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
        print("Removing empty folder: " + path)
        os.rmdir(path)

def rec_mkdir(path):
    if os.path.exists(path):
        return
    
    rec_mkdir(os.path.split(path)[0])

    if os.path.exists(path):
        return
    os.mkdir(path)

class MainApp():
    """Graphical progress for installation/fetch/operations.
    This widget provides a progress bar, a terminal and a status bar for
    showing the progress of package manipulation tasks.
    """
    def __init__(self, builder):
        self.builder = builder
        self.builder.add_from_file(DIR_PATH + "gui/main.ui")
        #self.builder.add_from_file("/usr/lib/cinnamon-settings/bin/main.ui")
        self._mainWindow = self.builder.get_object('Installer')
        self._appNameLabel = self.builder.get_object('appNameLabel')
        self._cancelButton = self.builder.get_object('cancelButton')
        self._closeButton = self.builder.get_object('closeButton')
        self._terminalExpander = self.builder.get_object('terminalExpander')
        self._terminalTextView = self.builder.get_object('terminalTextView')
        self._terminalTextBuffer = self._terminalTextView.get_buffer()
        self._terminalScrolled = self.builder.get_object('terminalScrolledWindow')
        self._terminalBox = self.builder.get_object('terminalBox')
        self._downloadScrolled = self.builder.get_object('downloadScrolledWindow')
        self._downloadTreeView = self.builder.get_object('downloadTreeView')
        self._downloadListModel = self.builder.get_object('downloadListModel')
        self._progressColumn = self.builder.get_object('progressColumn')
        self._nameColumn = self.builder.get_object('nameColumn')
        self._descriptionColumn = self.builder.get_object('descriptionColumn')
        self._progressCell = self.builder.get_object('progressCell')
        self._nameCell = self.builder.get_object('nameCell')
        self._descriptionCell = self.builder.get_object('descriptionCell')

        self._progressBar = self.builder.get_object('progressBar')
        self._roleLabel = self.builder.get_object('roleLabel')
        self._statusLabel = self.builder.get_object('statusLabel')
        self._actionImage = self.builder.get_object('actionImage')
        self._confTopLabel = self.builder.get_object('confTopLabel')
        self._confBottomLabel = self.builder.get_object('confBottomLabel')

        self._infoDialog = self.builder.get_object('InfoDialog')
        self._errorDialog = self.builder.get_object('ErrorDialog')
        self._errorDetails = self.builder.get_object('errorDetails')
        self._errorExpander = self.builder.get_object('errorBoxExpander')

        self._confDialog = self.builder.get_object('ConfDialog')
        self._confTreeView = self.builder.get_object('configTreeView')
        self._confScrolledWindow = self.builder.get_object('confScrolledWindow')
        self._confActionColumn = self.builder.get_object('confActionColumn')
        self._confImgCell = self.builder.get_object('confImgCell')
        self._confDesCell = self.builder.get_object('confDesCell')

        self._fileConfDialog = self.builder.get_object('FileConfDialog')
        self._fileConfTextView = self.builder.get_object('fileConfTextView')

        self._chooseDialog = self.builder.get_object('ChooseDialog')
        #self._chooseLabelModel = self.builder.get_object('chooseLabelModel')

        self._questionDialog = self.builder.get_object('QuestionDialog')
        self._warningDialog = self.builder.get_object('WarningDialog')
        self._preferencesWindow = self.builder.get_object('PreferencesWindow')

        #self._transactionSum = self.builder.get_object('transaction_sum')

        #self._downloadList = self.builder.get_object('download_list')
        #self._column_download = self.builder.get_object('column_download')

        self._chooseList = self.builder.get_object('chooseListModel')
        self._chooseToggleCell = self.builder.get_object('chooseToggleCell')
        self._enableAURButton = self.builder.get_object('enableAURButton')
        self._removeUnrequiredDepsButton = self.builder.get_object('RemoveUnrequiredDepsButton')
        self._refreshPeriodSpinButton = self.builder.get_object('refreshPeriodSpinButton')
        #refreshPeriodLabel = builder.get_object('refreshPeriodLabel')
        #self._mainWindow.connect("delete-event", self.closeWindows)
        self._init_common_values()

    def _init_common_values(self):
        self._statusLabel.set_max_width_chars(15)
        self._treestoreModel = None
        #self.set_title("")
        #self.mainApp._progressBar.set_size_request(350, -1)

    def show(self):
        self._mainWindow.show()
        #self._mainWindow.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
        #self.refresh()

    def hide(self):
        model = self._downloadTreeView.get_model()
        model.clear()
        self._mainWindow.hide()

    def closeWindows(self, windows, event):
        Gtk.main_quit()

    def refresh(self, force_update = False):
        while Gtk.events_pending():
            Gtk.main_iteration()
        while Gtk.events_pending():
            Gtk.main_iteration()
        #Refresh(force_update)

    def show_info(self, title, message):
        self._infoDialog.set_markup("<b>%s</b>" % title)
        self._infoDialog.format_secondary_markup(message)
        response = self._infoDialog.run()
        if response:
            self._infoDialog.hide()

    def show_providers(self, info_prov):
        self._chooseDialog.set_markup("<b>%s</b>" % info_prov['title'])
        self._chooseDialog.format_secondary_markup(info_prov['description'])
        list_providers = info_prov['providers']##need to be filled.
        self._chooseList.clear()
        for name in providers:
            self._chooseList.append([False, str(name)])
        lenght = len(self.to_add)
        response = self._chooseDialog.run()
        if response:
            self._errorDialog.hide()

    def show_error(self, title, message, details=None):
        self._errorDialog.set_markup("<b>%s</b>" % title)
        self._errorDialog.format_secondary_markup(message)
        if details:
            self._errorExpander.set_visible(True)
            self._errorDetails.set_text(details)
        response = self._errorDialog.run()
        if response:
            self._errorDialog.hide()

    def show_question(self, title, message):
        self._questionDialog.set_markup("<b>%s</b>" % title)
        self._questionDialog.format_secondary_markup(message)
        response = self._questionDialog.run()
        self._questionDialog.hide()
        return (response == Gtk.ResponseType.YES)

    def show_conf(self, infoConf):
        if(self._treestoreModel is None):
            self._treestoreModel = Gtk.TreeStore(GObject.TYPE_STRING)
            self._confTreeView.set_model(self._treestoreModel)
        else:
            self._treestoreModel.clear()
        packages_list = infoConf['dependencies']
        for msg in packages_list:
            piter = self._treestoreModel.append(None, ["<b>%s</b>" % msg])
            collect = packages_list[msg]
            for package in packages_list[msg]:
                self._treestoreModel.append(piter, [package])
        if len(self._treestoreModel) == 1:
            filtered_store = self._treestoreModel.filter_new(
                Gtk.TreePath.new_first())
            self._confTreeView.expand_all()
            self._confTreeView.set_model(filtered_store)
            self._confTreeView.set_show_expanders(False)
            if len(filtered_store) < 6:
                #self._mainWindow.set_resizable(False)
                self._confScrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                         Gtk.PolicyType.NEVER)
            else:
                self._confTreeView.set_size_request(350, 200)
        else:
            self._confTreeView.set_size_request(350, 200)
            self._confTreeView.collapse_all()
        self._confDialog.set_markup("<b>%s</b>" % infoConf['title'])
        self._confDialog.format_secondary_markup(infoConf['description'])
        res = self._confDialog.run()
        self._confDialog.hide()
        return res == Gtk.ResponseType.OK

    def show_file_conf(self):
        res = self._fileConfDialog.run()
        self._fileConfDialog.hide()
        return res == Gtk.ResponseType.OK

class Transaction(object):
    def __init__(self):
        self.loop = GObject.MainLoop()
        self.service = executer.SpiceExecuter()
        self.service.load_cache_async()

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

    def prepare_transaction_install(self, pkgs, cascade = True, recurse = False):
        thread = Thread(target = self.service.prepare_transaction_install, args=(pkgs, cascade, recurse,))
        thread.start()

    def prepare_transaction_remove(self, pkgs, cascade = True, recurse = False):
        thread = Thread(target = self.service.prepare_transaction_remove, args=(pkgs, cascade, recurse,))
        thread.start()

    def commit(self, sender=None, connexion=None):
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

    def refresh_cache(self, collect_type, force_update):#Test if this can removed latter.
        thread = Thread(target = self.service.refresh_cache, args=(collect_type, force_update,))
        thread.start()

    '''  this need to be see  '''
    def refresh(self, force_update):#Test if this can removed latter.
        thread = Thread(target = self.service.refresh_pylamp, args=(force_update,))
        thread.start()

    def release(self):#Test if this can removed latter.
        thread = Thread(target = self.service.release_all, args=())
        thread.start()

class Spice_Harvester:
    def __init__(self, collection_type, window, builder):
        self.collection_type = collection_type        
        self.cache_folder = self.get_cache_folder()
        self.install_folder = self.get_install_folder()
        self.index_cache = {}
        self.error = None
        self.themes = collection_type == "theme"
        
        if not os.path.exists(os.path.join(self.cache_folder, "index.json")):
            self.has_cache = False
        else:
            self.has_cache = True
        
        self.window = window
        self.builder = builder

        self.progress_window = self.builder.get_object("progress_window")
        self.progress_window.set_transient_for(window)
        self.progress_window.set_destroy_with_parent(True)
        self.progress_window.set_modal(True)
        self.progress_window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.progress_button_abort = self.builder.get_object("btnProgressAbort")
        self.progress_window.connect("delete-event", self.on_progress_close)
        self.progresslabel = self.builder.get_object('progresslabel')
        self.progressbar = self.builder.get_object("progressbar")
        self.progressbar.set_text('')
        self.progressbar.set_fraction(0)

        self.progress_window.set_title("")

        self.abort_download = ABORT_NONE
        self.download_total_files = 0
        self.download_current_file = 0
        self._sigLoadFinished = None

        self.progress_button_abort.connect("clicked", self.on_abort_clicked)

        self.spiceDetail = Gtk.Dialog(title = _("Applet info"),
                                      transient_for = self.window,
                                      modal = True,
                                      destroy_with_parent = True)
        self.spiceDetailSelectButton = self.spiceDetail.add_button(_("Select and Close"), Gtk.ResponseType.YES)
        self.spiceDetailSelectButton.connect("clicked", lambda x: self.close_select_detail())
        self.spiceDetailCloseButton = self.spiceDetail.add_button(_("Close"), Gtk.ResponseType.CANCEL)
        self.spiceDetailCloseButton.connect("clicked", lambda x: self.close_detail())
        self.spiceDetail.connect("destroy", self.on_close_detail)
        self.spiceDetail.connect("delete_event", self.on_close_detail)
        self.spiceDetail.set_default_size(640, 440)
        self.spiceDetail.set_size_request(640, 440)
        content_area = self.spiceDetail.get_content_area()

        # if self.get_webkit_enabled():
        #     self.browser = WebKit.WebView()
            
        #     self.browser.connect('button-press-event', lambda w, e: e.button == 3)
        #     self.browser.connect('title-changed', self.browser_title_changed)
        #     self.browser.connect('console-message' , self.browser_console_message)
        
        #     settings = WebKit.WebSettings()
        #     settings.set_property('enable-xss-auditor', False)
        #     settings.set_property('enable-file-access-from-file-uris', True)
        #     settings.set_property('enable-accelerated-compositing', True)
        #     self.browser.set_settings(settings)

        #     scrolled_window = Gtk.ScrolledWindow()
        #     scrolled_window.set_shadow_type(Gtk.ShadowType.NONE)
        #     scrolled_window.set_border_width(0)
        #     scrolled_window.add(self.browser)
        #     content_area.pack_start(scrolled_window, True, True, 0)
        #     scrolled_window.show()

    def get_webkit_enabled(self):
        return HAS_WEBKIT
    
    def close_select_detail(self):
        self.spiceDetail.hide()
        if callable(self.on_detail_select):
            self.on_detail_select(self)

    def on_close_detail(self, *args):
        self.close_detail()
        return True

    def close_detail(self):
        self.spiceDetail.hide()
        if hasattr(self, 'on_detail_close') and callable(self.on_detail_close):
            self.on_detail_close(self)

    def show_detail(self, uuid, onSelect=None, onClose=None):        
        self.on_detail_select = onSelect
        self.on_detail_close = onClose

        if not self.has_cache:
            self.refresh_cache(False)
        elif len(self.index_cache) == 0:
            self.load_cache()

        if uuid not in self.index_cache:
            self.load(lambda x: self.show_detail(uuid))
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

    def get_index_url(self):
        if self.collection_type == 'applet':
            return URL_SPICES_APPLET_LIST
        elif self.collection_type == 'extension':
            return URL_SPICES_EXTENSION_LIST
        elif self.collection_type == 'theme':
            return URL_SPICES_THEME_LIST
        elif self.collection_type == 'desklet':
            return URL_SPICES_DESKLET_LIST
        else:
            return False

    def get_cache_folder(self):
        cache_folder = "%s/.cinnamon/spices.cache/%s/" % (home, self.collection_type)

        if not os.path.exists(cache_folder):
            rec_mkdir(cache_folder)
        return cache_folder

    def get_install_folder(self):
        if self.collection_type in ['applet','desklet','extension']:
            install_folder = '%s/.local/share/cinnamon/%ss/' % (home, self.collection_type)
        elif self.collection_type == 'theme':
            install_folder = '%s/.themes/' % (home)

        return install_folder

    def load(self, onDone, force=False):
        self.abort_download = ABORT_NONE
        if (self.has_cache and not force):
            self.load_cache()
        else:
            self.progresslabel.set_text(_("Refreshing index..."))
            self.progress_window.show()
            self.refresh_cache()

        onDone(self.index_cache)

    def refresh_cache(self, load_assets=True):
        self.download_url = self.get_index_url()
        self.progressbar.set_fraction(0)
        self.progress_bar_pulse()

        filename = os.path.join(self.cache_folder, "index.json")
        f = open(filename, 'w')
        self.download(f, filename)
        
        self.load_cache()
        #print("Loaded index, now we know about %d spices." % len(self.index_cache))
        
        if load_assets:
            self.load_assets()

    def load_cache(self):
        filename = os.path.join(self.cache_folder, "index.json")
        f = open(filename, 'r')
        try:
            self.index_cache = json.load(f)
        except ValueError:
            try:
                os.remove(filename)
            except:
                pass
            e = sys.exc_info()[1]
            self.errorMessage(_("Something went wrong with the spices download.  Please try refreshing the list again."), str(e))

    def load_assets(self):
        self.progresslabel.set_text(_("Refreshing cache..."))
        self.progress_button_abort.set_sensitive(True)
        needs_refresh = 0
        used_thumbs = []

        uuids = self.index_cache.keys()

        for uuid in uuids:
            if not self.themes:
                icon_basename = os.path.basename(self.index_cache[uuid]['icon'])
                icon_path = os.path.join(self.cache_folder, icon_basename)
                used_thumbs.append(icon_basename)
            else:
                icon_basename = self.sanitize_thumb(os.path.basename(self.index_cache[uuid]['screenshot']))
                icon_path = os.path.join(self.cache_folder, icon_basename)
                used_thumbs.append(icon_basename)

            self.index_cache[uuid]['icon_filename'] = icon_basename
            self.index_cache[uuid]['icon_path'] = icon_path

            if not os.path.isfile(icon_path):
                needs_refresh += 1

        self.download_total_files = needs_refresh
        self.download_current_file = 0

        for uuid in uuids:
            if self.abort_download > ABORT_NONE:
                return

            icon_path = self.index_cache[uuid]['icon_path']
            if not os.path.isfile(icon_path):
                #self.progress_bar_pulse()
                self.download_current_file += 1
                f = open(icon_path, 'w')
                if not self.themes:
                    self.download_url = URL_SPICES_HOME + self.index_cache[uuid]['icon']
                else:
                    self.download_url = URL_SPICES_HOME + "/uploads/themes/thumbs/" + self.index_cache[uuid]['icon_filename']
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

        self.progress_window.hide()

        self.download_total_files = 0
        self.download_current_file = 0

    def sanitize_thumb(self, basename):
        return basename.replace("jpg", "png").replace("JPG", "png").replace("PNG", "png")     

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
    '''
    def make_transaction(self, install_list=[], update_list=[], remove_list=[] onFinished=None):
        for uuid, is_update, is_active in install_list:
            print("Start downloading")
            if uuid in self.index_cache:
                title = self.index_cache[uuid]['name']
                self.download_url = URL_SPICES_HOME + self.index_cache[uuid]['file'];
                self.current_uuid = uuid
                #self.progress_window.show()

                #self.progresslabel.set_text(_("Installing %s...") % (title))
                #self.progressbar.set_fraction(0)
                edited_date = self.index_cache[uuid]['last_edited']
                if not self.themes:
                    fd, filename = tempfile.mkstemp()
                    dirname = tempfile.mkdtemp()
                    f = os.fdopen(fd, 'wb')
                    try:
                        self.download(f, filename)
            
    '''
    def install_all(self, install_list=[], onFinished=None):
        need_restart = False
        success = False
        #subprocess.call(["python3", INSTALLER_PATH, "--icinnamon", self.collection_type + ",AlsaMixer@logan.com"])
        for uuid, is_update, is_active in install_list:
            success = self.install(uuid, is_update, is_active)
            need_restart = need_restart or (is_update and is_active and success)
        self.progress_window.hide()
        self.abort_download = False
        if callable(onFinished):
            try:
                onFinished(need_restart)
            except:
                pass

    def install(self, uuid, is_update, is_active):
        #print("Start downloading and installation")
        title = self.index_cache[uuid]['name']

        self.download_url = URL_SPICES_HOME + self.index_cache[uuid]['file'];
        self.current_uuid = uuid

        self.progress_window.show()        

        self.progresslabel.set_text(_("Installing %s...") % (title))
        self.progressbar.set_fraction(0)

        edited_date = self.index_cache[uuid]['last_edited']

        if not self.themes:
            fd, filename = tempfile.mkstemp()
            dirname = tempfile.mkdtemp()
            f = os.fdopen(fd, 'wb')
            try:
                self.download(f, filename)
                dest = os.path.join(self.install_folder, uuid)
                schema_filename = ""
                zip = zipfile.ZipFile(filename)
                zip.extractall(dirname, self.get_members(zip))
                for file in self.get_members(zip):
                    #if not file.filename.endswith('/') and ((file.external_attr >> 16L) & 0o755) == 0o755:
                    #    os.chmod(os.path.join(dirname, file.filename), 0o755)
                    #elif file.filename[:3] == 'po/':
                    if file.filename[:3] == 'po/':
                        parts = os.path.splitext(file.filename)
                        if parts[1] == '.po':
                           this_locale_dir = os.path.join(locale_inst, parts[0][3:], 'LC_MESSAGES')
                           self.progresslabel.set_text(_("Installing translations for %s...") % title)
                           rec_mkdir(this_locale_dir)
                           #print("/usr/bin/msgfmt -c %s -o %s" % (os.path.join(dest, file.filename), os.path.join(this_locale_dir, '%s.mo' % uuid)))
                           subprocess.call(["msgfmt", "-c", os.path.join(dirname, file.filename), "-o", os.path.join(this_locale_dir, '%s.mo' % uuid)])
                           self.progresslabel.set_text(_("Installing %s...") % (title))
                    elif "gschema.xml" in file.filename:
                        sentence = _("Please enter your password to install the required settings schema for %s") % (uuid)
                        if os.path.exists("/usr/bin/gksu") and os.path.exists("/usr/lib/cinnamon-settings/bin/installSchema.py"):
                            launcher = "gksu  --message \"<b>%s</b>\"" % sentence
                            tool = "/usr/lib/cinnamon-settings/bin/installSchema.py %s" % (os.path.join(dirname, file.filename))
                            command = "%s %s" % (launcher, tool)
                            os.system(command)
                            schema_filename = file.filename
                        else:
                            self.errorMessage(_("Could not install the settings schema for %s.  You will have to perform this step yourself.") % (uuid))
                file = open(os.path.join(dirname, "metadata.json"), 'r')
                raw_meta = file.read()
                file.close()
                md = json.loads(raw_meta)
                md["last-edited"] = edited_date
                if schema_filename != "":
                    md["schema-file"] = schema_filename
                raw_meta = json.dumps(md, indent=4)
                file = open(os.path.join(dirname, "metadata.json"), 'w+')
                file.write(raw_meta)
                file.close()
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(dirname, dest)
                shutil.rmtree(dirname)
                os.remove(filename)

            except Exception:
                self.progress_window.hide()
                try:
                    shutil.rmtree(dirname)
                    os.remove(filename)
                except:
                    pass
                if not self.abort_download:
                    self.errorMessage(_("An error occurred during installation or updating.  You may wish to report this incident to the developer of %s.\n\nIf this was an update, the previous installation is unchanged") % (uuid), str(e))
                return False
        else:
            fd, filename = tempfile.mkstemp()
            dirname = tempfile.mkdtemp()
            f = os.fdopen(fd, 'wb')
            try:
                self.download(f, filename)
                dest = self.install_folder
                zip = zipfile.ZipFile(filename)
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
                file = open(os.path.join(temp_path, "cinnamon", "metadata.json"), 'w+')
                file.write(raw_meta)
                file.close()
                final_path = os.path.join(dest, title)
                if os.path.exists(final_path):
                    shutil.rmtree(final_path)
                shutil.copytree(temp_path, final_path)
                shutil.rmtree(dirname)
                os.remove(filename)

            except Exception:
                self.progress_window.hide()
                try:
                    shutil.rmtree(dirname)
                    os.remove(filename)
                except:
                    pass
                if not self.themes:
                    obj = uuid
                else:
                    obj = title
                if not self.abort_download:
                    self.errorMessage(_("An error occurred during installation or updating.  You may wish to report this incident to the developer of %s.\n\nIf this was an update, the previous installation is unchanged") % (obj), str(e))
                return False

        self.progress_button_abort.set_sensitive(False)
        self.progress_window.show()
        return True

    def uninstall_all(self, list_uninstall, onFinished=None):
        try:
            if not self.themes:
                tool = ""
                for item in list_uninstall:
                    if item[2] != "":
                        if tool == "":
                            tool = "/usr/lib/cinnamon-settings/bin/removeSchema.py %s" % (item[2])
                        else:
                            tool += " && /usr/lib/cinnamon-settings/bin/removeSchema.py %s" % (item[2])
                if tool != "":
                    sentence = _("Please enter your password to remove the settings schema for %s") % (uuid)
                    if os.path.exists("/usr/bin/gksu") and os.path.exists("/usr/lib/cinnamon-settings/bin/removeSchema.py"):
                        launcher = "gksu  --message \"<b>%s</b>\"" % sentence
                        command = "%s %s" % (launcher, tool)
                        os.system(command)
                    else:
                        self.errorMessage(_("Could not remove the settings schema for %s.  You will have to perform this step yourself.  This is not a critical error.") % (uuid))

                for item in list_uninstall:
                    shutil.rmtree(os.path.join(self.install_folder, item[0]))

                    # Uninstall spice localization files, if any
                    if (os.path.exists(locale_inst)):
                        i19_folders = os.listdir(locale_inst)
                        for i19_folder in i19_folders:
                            if os.path.isfile(os.path.join(locale_inst, i19_folder, 'LC_MESSAGES', "%s.mo" % item[0])):
                                os.remove(os.path.join(locale_inst, i19_folder, 'LC_MESSAGES', "%s.mo" % item[0]))
                            # Clean-up this locale folder
                            removeEmptyFolders(os.path.join(locale_inst, i19_folder))
                    # Uninstall settings file, if any
                    if (os.path.exists(os.path.join(settings_dir, item[0]))):
                        shutil.rmtree(os.path.join(settings_dir, item[0]))
            else:
                for item in list_uninstall:
                    shutil.rmtree(os.path.join(self.install_folder, item[1]))
        except Exception:
            #self.progress_window.hide()
            self.errorMessage(_("Problem uninstalling %s.  You may need to manually remove it.") % (uuid), e)

        if callable(onFinished):
            onFinished()

    def uninstall(self, uuid, name, schema_filename, onFinished=None):
        self.progresslabel.set_text(_("Uninstalling %s...") % name)
        self.progress_window.show()
        
        self.progress_bar_pulse()
        try:
            if not self.themes:
                print("uninstall")
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
            self.errorMessage(_("Problem uninstalling %s.  You may need to manually remove it.") % (uuid), e)

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

    def download(self, outfd, outfile):
        url = self.download_url
        self.progress_button_abort.set_sensitive(True)
        try:
            self.url_retrieve(url, outfd, self.reporthook)
        except KeyboardInterrupt:
            try:
                os.remove(outfile)
            except OSError:
                pass
            self.progress_window.hide()
            if self.abort_download == ABORT_ERROR:
                self.errorMessage(_("An error occurred while trying to access the server.  Please try again in a little while."), self.error)
            raise Exception(_("Download aborted."))

        return outfile

    def reporthook(self, count, blockSize, totalSize):
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

    def url_retrieve(self, url, f, reporthook):        
        #Like the one in urllib. Unlike urllib.retrieve url_retrieve
        #can be interrupted. KeyboardInterrupt exception is rasied when
        #interrupted.        
        count = 0
        blockSize = 1024 * 8
        try:
            urlobj = urllib2.urlopen(url)
        except Exception:
            f.close()
            self.abort_download = ABORT_ERROR
            e = sys.exc_info()[1]
            self.error = str(e)
            raise KeyboardInterrupt

        totalSize = int(urlobj.info()['content-length'])

        try:
            while self.abort_download == ABORT_NONE:
                data = urlobj.read(blockSize)
                count += 1
                if not data:
                    break
                f.write(data)
                reporthook(count, blockSize, totalSize)
        except KeyboardInterrupt:
            f.close()
            self.abort_download = ABORT_USER

        if self.abort_download > ABORT_NONE:
            raise KeyboardInterrupt

        del urlobj
        f.close()

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

class Installer():
    def __init__(self, window, builder):
        self.installer_providers = {}
        self.providers = []
        sp_har = Spice_Harvester_Composed()
        self.installer_providers[sp_har.name] = sp_har
        self.select_installer_provider(window, builder)

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

    def check_update_silent(self):
        if self.single_mode:
            self.providers[0].check_update_silent()
        else:
            print("Not implemented, provide a way to update modules for different installer")
        return True

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
        self.trans = Transaction()
        self.name = "Spice_Harvester"
        self.supported_modules = ["applet", "desklet", "extension", "theme"]
        self.installer = {}
        self.modules = {}

    def set_parent_ref(self, window, builder):
        self.builder = builder
        self.window = window

        self.mainApp = MainApp(builder)

        #self.debconf = True
        self._expanded_size = None
        self.terminal = None
        self._signals = []
        self._download_map = {}
        if self.trans.have_terminal():
            self.terminal = Vte.Terminal()
            self._master, self._slave = pty.openpty()
            self._ttyname = os.ttyname(self._slave)
            self.terminal.set_size(80, 24)
            self.terminal.set_pty_object(Vte.Pty.new_foreign(self._master))
            self.mainApp._terminalBox.pack_start(self.terminal, True, True, 0)
            self.trans.set_terminal(self._ttyname)
            self.terminal.hide()

        self.mainApp._terminalExpander.connect("notify::expanded", self._on_expanded)
        self.mainApp._progressColumn.set_cell_data_func(self.mainApp._progressCell, self._data_progress, None)
        self.mainApp._confActionColumn.set_cell_data_func(self.mainApp._confImgCell, self._render_package_icon, None)
        self.mainApp._confActionColumn.set_cell_data_func(self.mainApp._confDesCell, self._render_package_desc, None)

        self.signals = {
                        'on_chooseButton_clicked'            : self._on_chooseButton_clicked,
                        'on_terminalTextView_allocate'       : self._on_terminalTextView_allocate,
                        'on_chooseToggleCell_toggled'        : self._on_chooseToggleCell_toggled,
                        'on_preferencesCloseButton_clicked'  : self._on_preferencesCloseButton_clicked,
                        'on_preferencesWindow_delete_event'  : self._on_preferencesWindow_delete_event,
                        'on_preferencesAceptButton_clicked'  : self._on_preferencesAceptButton_clicked,
                        'on_progressCloseButton_clicked'     : self._on_progressCloseButton_clicked,
                        'on_progressCancelButton_clicked'    : self._on_progressCancelButton_clicked
                       }

        self.mainApp.builder.connect_signals(self.signals)
        self._config_signals()
        self.details = False#Que es esto kit
        self.transaction_done = True#Que es esto pac update after install


    def _config_signals(self):
        self.trans.connect("EmitTransactionConfirmation", self.handler_confirm_deps)
        self.trans.connect("EmitTransactionDone", self.handler_reply)
        self.trans.connect("EmitTransactionError", self.handler_transaction_error)
        self.trans.connect("EmitTransactionCancellable", self.handler_cancellable_changed)
        self.trans.connect("EmitTransactionStart", self.handler_transaction_start)
        self.trans.connect("EmitAvailableUpdates", self.handler_updates)
        self.trans.connect("EmitStatus", self.handler_status)
        self.trans.connect("EmitRole", self.handler_role)
        self.trans.connect("EmitIcon", self.handler_icon)
        self.trans.connect("EmitTarget", self.handler_target)
        self.trans.connect("EmitPercent", self.handler_percent)
        self.trans.connect("EmitDownloadChildStart", self.handler_start_childs)
        self.trans.connect("EmitDownloadPercentChild", self.handler_percent_childs)
        self.trans.connect("EmitTerminalAttached", self.handler_terminal_attached)
        self.trans.connect("EmitNeedDetails", self.handler_need_details)
        self.trans.connect("EmitLogError", self.handler_log_error)
        self.trans.connect("EmitLogWarning", self.handler_log_warning)
        self.trans.connect("EmitConflictFile", self.handler_conflict_file)
        self.trans.connect("EmitChooseProvider", self.handler_choose_provider)
        self.trans.connect("EmitReloadConfig", self.handler_config_change)
        self.trans.connect("EmitMediumRequired", self.handler_medium_required)

    def handler_confirm_deps(self, service, conf_info):
        GObject.idle_add(self.exec_confirm_deps, conf_info)
        time.sleep(0.1)

    def handler_choose_provider(self, service, info_prov):
        GObject.idle_add(self.exec_choose_provider, info_prov)
        time.sleep(0.1)

    def handler_config_change(self, service, data):
        GObject.idle_add(self.exec_config_change, data)
        time.sleep(0.1)

    def handler_transaction_start(self, service, message):
        GObject.idle_add(self.exec_transaction_start, message)
        time.sleep(0.1)

    def handler_reply(self, service, reply):
        GObject.idle_add(self.exec_reply, reply)
        time.sleep(0.1)

    def handler_transaction_error(self, service, title, message):
        GObject.idle_add(self.exec_transaction_error, title, message)
        time.sleep(0.1)

    def handler_status(self, service, status, translation):
        GObject.idle_add(self.exec_status, status, translation)
        time.sleep(0.05)

    def handler_role(self, service, role_translate):
        GObject.idle_add(self.exec_role, role_translate)
        time.sleep(0.05)

    def handler_icon(self, service, icon_name):
        GObject.idle_add(self.exec_icon, icon_name)
        time.sleep(0.05)

    def handler_percent(self, service, percent):
        GObject.idle_add(self.exec_percent, percent)
        time.sleep(0.05)

    def handler_target(self, service, text):
        GObject.idle_add(self.exec_target, text)
        time.sleep(0.05)

    def handler_need_details(self, service, need):
        GObject.idle_add(self.exec_need_details, need)
        time.sleep(0.1)

    def handler_updates(self, service, syncfirst, updates):
        GObject.idle_add(self.exec_updates, syncfirst, updates)
        time.sleep(0.1)

    def handler_cancellable_changed(self, service, cancellable):
        GObject.idle_add(self.exec_cancellable_changed, cancellable)
        time.sleep(0.1)

    def handler_start_childs(self, service, restar_all):
        GObject.idle_add(self.exec_start_childs, restar_all)
        time.sleep(0.1)

    def handler_percent_childs(self, service, id, name, percent, details):
        GObject.idle_add(self.exec_percent_childs, id, name, percent, details)
        time.sleep(0.1)

    def handler_terminal_attached(self, service, attached):
        GObject.idle_add(self.exec_terminal_attached, attached)
        time.sleep(0.1)

    def handler_medium_required(self, service, medium, title, drive):
        GObject.idle_add(self.exec_medium_required, medium, title, drive)
        time.sleep(0.1)

    def handler_conflict_file(self, service, old, new):
        GObject.idle_add(self.exec_conflict_file, old, new)
        time.sleep(0.1)

    def handler_log_error(self, service, msg):
        GObject.idle_add(self.exec_log_error, msg)
        time.sleep(0.1)

    def handler_log_warning(self, service, msg):
        GObject.idle_add(self.exec_log_warning, msg)
        time.sleep(0.1)

    def exec_confirm_deps(self, conf_info):
        if len(conf_info["dependencies"]) > 0:
            confirmation = self.mainApp.show_conf(conf_info)
        else:
            confirmation = True
        if confirmation:
            self.trans.commit()
        else:
            self.trans.cancel()
            self.exec_transaction_error(_("Transaction canceled:"), _("Transaction fail."), )
            self.mainApp.refresh()
            self.exiting('')
        ''' For pac
        self.mainApp._confDialog.hide()
        self.mainApp.refresh()
        self.trans.finalize()
        self.mainApp.refresh()
        if not self.trans.details:
            self.trans.release()
            self.exiting('')
        '''

    def exec_transaction_start(self, message):
        self.mainApp._cancelButton.hide()
        self.mainApp.refresh()

    def exec_reply(self, message):
        end_iter = self.mainApp._terminalTextBuffer.get_end_iter()
        self.mainApp._terminalTextBuffer.insert(end_iter, str(message))
        self.exiting("")

    def exec_transaction_error(self, title, message):
        self.mainApp.show_error(title, message)
        self.exiting("")

    def exec_status(self, status, translation):
       
        if translation != "":
            self.mainApp._statusLabel.set_markup(translation)
        elif status in CI_STATUS:
            self.mainApp._statusLabel.set_markup(CI_STATUS[status])
        else:
            self.mainApp._statusLabel.set_markup(CI_STATUS["UNKNOWN"])
        if status in ("DOWNLOADING", "DOWNLOADING_REPO"):
            self.mainApp._terminalExpander.set_sensitive(True)
            self.mainApp._downloadScrolled.show()
            self.mainApp._terminalTextView.hide()
            if self.terminal:
                self.terminal.hide()
        elif status == "COMMITTING":
            self.mainApp._downloadScrolled.hide()
            if self.terminal:
                self.terminal.show()
                self.mainApp._terminalExpander.set_sensitive(True)
            else:
                self.mainApp._terminalTextView.show()
                self.mainApp._terminalExpander.set_expanded(False)
                #self.mainApp._terminalExpander.set_sensitive(False)
        elif status == "DETAILS":
            return
        else:
            self.mainApp._downloadScrolled.hide()
            if self.terminal:
                self.terminal.hide()
            else:
                self.mainApp._terminalTextView.show()
            #self.mainApp._terminalExpander.set_sensitive(False)
            self.mainApp._terminalExpander.set_expanded(False)
        self.mainApp.refresh()

    def exec_role(self, role_translate):
        end_iter = self.mainApp._terminalTextBuffer.get_end_iter()      
        self.mainApp._terminalTextBuffer.insert(end_iter, role_translate)
        self.mainApp._roleLabel.set_markup("<big><b>%s</b></big>" % role_translate)
        self.mainApp.refresh()

    def exec_icon(self, icon_name):
        if icon_name is None:
            icon_name = Gtk.STOCK_MISSING_IMAGE
        self.mainApp._actionImage.set_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        self.mainApp.refresh()

    def exec_percent(self, percent):
        if percent > 1:
            self.mainApp._progressBar.pulse()
            if percent > 2:
                self.mainApp._progressBar.set_text('')
        else:
            self.mainApp._progressBar.set_fraction(percent)
        self.mainApp.refresh()

    def exec_target(self, text):
        self.mainApp._progressBar.set_text(text)
        self.mainApp.refresh()

    def exec_need_details(self, need):
        self.mainApp._terminalExpander.set_expanded(need)
        self.details = need;
        self.mainApp.refresh()

    def exec_updates(self, syncfirst=True, updates=None):
        #syncfirst, updates = update_data
        if self.transaction_done:
            self.exiting('')
        elif updates:
            self.mainApp._errorDialog.format_secondary_text(_('Some updates are available.\nPlease update your system first'))
            response = self.mainApp._errorDialog.run()
            if response:
                self.mainApp._errorDialog.hide()
                self.exiting('')

    def exec_cancellable_changed(self, cancellable):
        self.mainApp._cancelButton.set_sensitive(cancellable)

    def exec_start_childs(self, restar_all):
        self.mainApp._downloadTreeView.get_model().clear()

    def exec_percent_childs(self, id, name, percent, details):
        model = self.mainApp._downloadTreeView.get_model()
        if percent > 100:
            percent = 100
        try:
            iter = self._download_map[id]
        except KeyError:
            adj = self.mainApp._downloadTreeView.get_vadjustment()
            is_scrolled_down = (adj.get_value() + adj.get_page_size() ==
                                adj.get_upper())
            iter = model.append((percent, name, details, id))
            self._download_map[id] = iter
            if is_scrolled_down:
                # If the treeview was scrolled to the end, do this again
                # after appending a new item
                self.mainApp._downloadTreeView.scroll_to_cell(model.get_path(iter),
                    None, False, False, False)
        else:
            model.set_value(iter, 0, percent)
            model.set_value(iter, 1, name)
            model.set_value(iter, 2, details)

    def exec_terminal_attached(self, attached):
        if attached and self.terminal:
            self.mainApp._terminalExpander.set_sensitive(True)

    def exec_medium_required(self, medium, title, drive):
        if self.mainApp.show_question(title, desc):
            self.trans.provide_medium_required(medium)
        else:
             self.trans.cancel()

    def exec_conflict_file(self, old, new):
        self._create_file_diff(old, new)
        replace = self.mainApp.show_file_conf()
        self.trans.resolve_config_file_conflict(replace, old, new)

    def exec_log_error(self, msg):
        textbuffer = self.mainApp._terminalTextBuffer
        end_iter = self.mainApp._terminalTextBuffer.get_end_iter()
        tags = textbuffer.get_tag_table()
        name = "error"+str(self.tag_count)
        tag_default = Gtk.TextTag.new(name)
        tag_default.set_properties(background='red')
        tags.add(tag_default)
        self._insert_tagged_text(end_iter, textbuffer, msg, name)
        self.tag_count += 1

    def exec_log_warning(self, msg):
        textbuffer = self.mainApp._terminalTextBuffer
        end_iter = self.mainApp._terminalTextBuffer.get_end_iter()
        tags = textbuffer.get_tag_table()
        name = "warning"+str(self.tag_count)
        tag_default = Gtk.TextTag.new(name)
        tag_default.set_properties(background='yellow')
        tags.add(tag_default)
        self._insert_tagged_text(end_iter, textbuffer, msg, name)
        self.tag_count += 1

    def exec_choose_provider(self, info_prov):
        provider_selected = None
        if len(info_prov["providers"]) > 0:
            confirmation = self.mainApp.show_providers(info_prov)
            if confirmation:
                provider_selected  = set()
                for row in self.mainApp.choose_list:
                    if row[0] is True:
                        provider_selected .add(row[1].split(':')[0]) # split done in case of optdep choice
        else:
            confirmation = True
        if confirmation:
            self.trans.resolve_package_providers(provider_selected)##we need to select a provider really
            print("fixmeee no real provider")
        else:
            self.trans.release()
            self.exec_transaction_error(_("Transaction canceled:"), _("Transaction fail."), )
            self.mainApp.refresh()
            self.trans.release()
            self.exiting('')

    def exec_config_change(self, data):
        pass

    def _on_terminalTextView_allocate(self, *args):
        #auto-scrolling method
        adj = self.mainApp._terminalTextView.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def _on_chooseToggleCell_toggled(self, *args):
        self.mainApp._chooseList[line][0] = not self.mainApp._chooseList[line][0]

    def _on_preferencesCloseButton_clicked(self, *args):
        self.mainApp._preferencesWindow.hide()

    def _on_preferencesWindow_delete_event(self, *args):
        self.mainApp._preferencesWindow.hide()
        # return True is needed to not destroy the window
        return True

    def _on_preferencesAceptButton_clicked(self, *args):
        data = []
        data.append(('EnableAUR', str(self.mainApp._enableAURButton.get_active())))
        data.append(('RemoveUnrequiredDeps', str(self.mainApp._removeUnrequiredDepsButton.get_active())))
        data.append(('RefreshPeriod', str(self.mainApp._refreshPeriodSpinButton.get_value_as_int())))
        self.trans.write_config(data)
        self.mainApp._preferencesWindow.hide()

    def _on_progressCloseButton_clicked(self, *args):
        self.exiting("")

    def _on_progressCancelButton_clicked(self, *args):
        self.exiting("")

    def _on_chooseButton_clicked(self, *args):# no existe
        self.mainApp._chooseDialog.hide()
        self.mainApp.refresh()
        #for row in self.mainApp._chooseList:
        #    if row[0] is True:
        #        self.trans.resolve_package_providers(row[1].split(':')[0]) # split done in case of optdep choice

    def _on_expanded(self, expander, param):
        # Make the dialog resizable if the expander is expanded
        # try to restore a previous size
        if not expander.get_expanded():
            self._expanded_size = ((self.terminal and self.terminal.get_visible()),
                                   self.mainApp._mainWindow.get_size())
            self.mainApp._mainWindow.set_resizable(False)
        elif self._expanded_size:
            self.mainApp._mainWindow.set_resizable(True)
            term_visible, (stored_width, stored_height) = self._expanded_size
            # Check if the stored size was for the download details or
            # the terminal widget
            if term_visible != (self.terminal and self.terminal.get_visible()):
                # The stored size was for the download details, so we need
                # get a new size for the terminal widget
                self._resize_to_show_details()
            else:
                self.mainApp._mainWindow.resize(stored_width, stored_height)
        else:
            self.mainApp._mainWindow.set_resizable(True)
            self._resize_to_show_details()

    def _resize_to_show_details(self):
        win_width, win_height = self.mainApp._mainWindow.get_size()
        exp_width = self.mainApp._terminalExpander.get_allocation().width
        exp_height = self.mainApp._terminalExpander.get_allocation().height
        if self.terminal and self.terminal.get_visible():
            terminal_width = self.terminal.get_char_width() * 80
            terminal_height = self.terminal.get_char_height() * 24
            self.mainApp._mainWindow.resize(terminal_width - exp_width,
                               terminal_height - exp_height )
        else:
            self.mainApp._mainWindow.resize(win_width + 100, win_height)

    def _data_progress(self, column, cell, model, iter, data):
        try:
            progress = model.get_value(iter, 0)
            if progress == -1:
                cell.props.pulse = progress
            else:
                cell.props.value = progress
        except Exception:
            e = sys.exc_info()[1]
            print(str(e))

    def _render_package_icon(self, column, cell, model, iter, data):
        """Data func for the Gtk.CellRendererPixbuf which shows the package. Override
        this method if you want to show custom icons for a package or map it to applications.
        """
        path = model.get_path(iter)
        if path.get_depth() == 0:
            cell.props.visible = False
        else:
            cell.props.visible = True
        cell.props.icon_name = "applications-other"

    def _render_package_desc(self, column, cell, model, iter, data):
        """Data func for the Gtk.CellRendererText which shows the package. Override
        this method if you want to show more information about a package or map it to applications.
        """
        value = model.get_value(iter, 0)
        if not value:
            return
        try:
            pkg_name, pkg_version = value.split("=")[0:2]
        except ValueError:
            pkg_name = value
            pkg_version = None
        if pkg_version:
            text = "%s (%s)" % (pkg_name, pkg_version)
        else:
            text = "%s" % pkg_name
        cell.set_property("markup", text)

    def run(self):
        self.transaction_done = False
        self.mainApp._closeButton.hide()
        GObject.idle_add(self.exec_show)
        time.sleep(0.1)
        #Gtk.main()

    def exec_show(self):
        self.mainApp.show()

    def exiting(self, msg):
        self.transaction_done = True
        self.trans.cancel()
        self.mainApp.hide()
        print(msg)
        #Gtk.main_quit()

    def score(self):
        return 0

    def register_module(self, module):
        collect_type = module.sidePage.collection_type
        if (collect_type in self.supported_modules):
            try:
                module.sidePage.set_installer(self)
                self.installer[collect_type] = Spice_Harvester_Cinnamon(collect_type, self.window, self.builder, self)
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
                self.trans.refresh_cache("all", True)
            except Exception:
                e = sys.exc_info()[1]
                print(str(e))
        on_spice_load(self.installer[mod_name].index_cache)
        '''

    def get_cache_folder(self, mod_name):
        return self.installer[mod_name].get_cache_folder()

    def install_all(self, mod_name, install_list, install_finished):
        self.installer[mod_name].install_all(install_list, install_finished)

    def uninstall(self, mod_name, uuid, name, schema_filename, on_uninstall_finished):
        self.installer[mod_name].uninstall(uuid, name, schema_filename, on_uninstall_finished)

    def uninstall_all(self, mod_name, list_uninstall, on_uninstall_finished):
        self.installer[mod_name].uninstall_all(list_uninstall, on_uninstall_finished)

class Spice_Harvester_Cinnamon(Spice_Harvester):
    def __init__(self, collection_type, window, builder, parent):
        Spice_Harvester.__init__(self, collection_type, window, builder)
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
            self.parent.emit('EmitTransactionStart', _("Refreshing index..."))
            self.refresh_cache()
            self.parent.emit('EmitTransactionDone', "")
        onDone(self.index_cache)

    def refresh_cache(self, load_assets=True):
        self.download_url = self.get_index_url()
        self.parent.emit('EmitPercent', 2)

        filename = os.path.join(self.cache_folder, "index.json")
        f = open(filename, 'w')
        self.download(f, filename)
        
        self.load_cache()
        #print("Loaded index, now we know about %d spices." % len(self.index_cache))
        
        if load_assets:
            self.load_assets()

    def load_assets(self):
        #self.progresslabel.set_text(_("Refreshing cache..."))
        #self.progress_button_abort.set_sensitive(True)
        self.parent.emit('EmitTransactionStart', _("Refreshing index..."))
        self.parent.emit('EmitTransactionCancellable', True)

        needs_refresh = 0
        used_thumbs = []

        uuids = self.index_cache.keys()

        for uuid in uuids:
            if not self.themes:
                icon_basename = os.path.basename(self.index_cache[uuid]['icon'])
                icon_path = os.path.join(self.cache_folder, icon_basename)
                used_thumbs.append(icon_basename)
            else:
                icon_basename = self.sanitize_thumb(os.path.basename(self.index_cache[uuid]['screenshot']))
                icon_path = os.path.join(self.cache_folder, icon_basename)
                used_thumbs.append(icon_basename)

            self.index_cache[uuid]['icon_filename'] = icon_basename
            self.index_cache[uuid]['icon_path'] = icon_path

            if not os.path.isfile(icon_path):
                needs_refresh += 1

        self.download_total_files = needs_refresh
        self.download_current_file = 0

        for uuid in uuids:
            if self.abort_download > ABORT_NONE:
                return

            icon_path = self.index_cache[uuid]['icon_path']
            if not os.path.isfile(icon_path):
                #self.progress_bar_pulse()
                self.download_current_file += 1
                f = open(icon_path, 'w')
                if not self.themes:
                    self.download_url = URL_SPICES_HOME + self.index_cache[uuid]['icon']
                else:
                    self.download_url = URL_SPICES_HOME + "/uploads/themes/thumbs/" + self.index_cache[uuid]['icon_filename']
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
        self.parent.emit('EmitTransactionDone', "")

        self.download_total_files = 0
        self.download_current_file = 0

    def download(self, outfd, outfile):
        url = self.download_url
        #self.progress_button_abort.set_sensitive(True)
        self.parent.emit('EmitTransactionCancellable', True)
        try:
            self.url_retrieve(url, outfd, self.reporthook)
        except KeyboardInterrupt:
            try:
                os.remove(outfile)
            except OSError:
                pass
            #self.progress_window.hide()
            self.parent.emit('EmitTransactionDone', "Error")
            if self.abort_download == ABORT_ERROR:
                #self.errorMessage(_("An error occurred while trying to access the server.  Please try again in a little while."), self.error)
                self.parent.emit('EmitTransactionError', _("An error occurred while trying to access the server.  Please try again in a little while."), "")
            raise Exception(_("Download aborted."))

        return outfile
        
    def refresh_cache_silent(self):
        download_url = self.get_index_url()
        fd, filename = tempfile.mkstemp()
        f = open(filename, 'w')
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
            self.parent.emit('EmitTarget', "%s - %d / %d files" % (str(int(fraction*100)) + '%', self.download_current_file, self.download_total_files))
        else:
            fraction = count * blockSize / float((totalSize / blockSize + 1) * (blockSize))
            self.parent.emit('EmitTarget', str(int(fraction * 100)) + '%')

        if fraction > 0:
             self.parent.emit('EmitPercent', fraction)
        else:
             self.parent.emit('EmitPercent', 2)

        #while Gtk.events_pending():
        #    Gtk.main_iteration()

    def silentReporthook(self, count, blockSize, totalSize):
        pass
