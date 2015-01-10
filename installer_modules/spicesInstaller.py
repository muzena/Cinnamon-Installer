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

from gi.repository import GObject, Gtk, GLib, Pango
# WebKit requires gir1.2-javascriptcoregtk-3.0 and gir1.2-webkit-3.0
    # try:
    #     from gi.repository import WebKit
    #     HAS_WEBKIT=True
    # except:
    #     HAS_WEBKIT=False
    #     print("WebKit not found on this system. These packages are needed for adding spices:")
    #     print("  gir1.2-javascriptcoregtk-3.0")
    #     print("  gir1.2-webkit-3.0")
import gettext, locale, sys, os, datetime
from time import sleep

MODULES = 'lib'
ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"
sys.path.append(DIR_PATH + MODULES)

_ = gettext.gettext

try:
    import transactionspi as transaction

except Exception as e:
    print(str(e))
    sys.exit(1)

class ControlWindow(object):

    COL_PERCENT, COL_NAME, COL_DETAILS, COL_URI = list(range(4))

    def __init__(self, mainApp):
        self.mainApp = mainApp
        '''Begin SpicesKit'''
        self.validTypes = ['applet','desklet','extension', 'theme'];
        self.trans = transaction.InstallerService(True)
        self.signals = {
                        'on_ChooseButton_clicked'            : self.on_ChooseButton_clicked,
                        'on_progress_textview_size_allocate' : self.on_progress_textview_size_allocate,
                        'on_choose_renderertoggle_toggled'   : self.on_choose_renderertoggle_toggled,
                        'on_PreferencesCloseButton_clicked'  : self.on_PreferencesCloseButton_clicked,
                        'on_PreferencesWindow_delete_event'  : self.on_PreferencesWindow_delete_event,
                        'on_PreferencesValidButton_clicked'  : self.on_PreferencesValidButton_clicked,
                        'on_confAceptButton_clicked'         : self.on_confAceptButton_clicked,
                        'on_confCancelButton_clicked'        : self.on_confCancelButton_clicked,
                        'on_ProgressCloseButton_clicked'     : self.on_ProgressCloseButton_clicked,
                        'on_ProgressCancelButton_clicked'    : self.on_ProgressCancelButton_clicked
        }
        #self.mainApp.interface.connect_signals(self.signals)
        self.config_signals()
        self._download_map = {}
        self.terminal = None

        #self._create_download_model()
        #iter = model.append(("bbbbbbb", 5, "aaaa"))

    def _create_download_model(self):
        self._download_map = {}
        columns = self.mainApp._downloadTreeView.get_columns()
        for col in columns:
            self.mainApp._downloadTreeView.remove_column(col)

        cell_percent = Gtk.CellRendererProgress()
        column_percent = Gtk.TreeViewColumn(_("%"))
        column_percent.pack_start(cell_percent, True)
        column_percent.set_cell_data_func(cell_percent, self._data_percent, None)

        cell_name = Gtk.CellRendererText()
        cell_name.props.ellipsize = Pango.EllipsizeMode.END
        column_name = Gtk.TreeViewColumn(_("Name"))
        column_name.pack_start(cell_name, True)
        column_name.add_attribute(cell_name, "markup", self.COL_NAME)

        cell_details = Gtk.CellRendererText()
        cell_details.props.ellipsize = Pango.EllipsizeMode.END
        column_details = Gtk.TreeViewColumn(_("Details"))
        column_details.pack_start(cell_details, True)
        column_details.add_attribute(cell_details, "markup", self.COL_DETAILS)

        self.mainApp._downloadTreeView.append_column(column_percent)
        self.mainApp._downloadTreeView.append_column(column_name)
        self.mainApp._downloadTreeView.append_column(column_details)

        model = Gtk.ListStore(GObject.TYPE_INT, GObject.TYPE_STRING,
                              GObject.TYPE_STRING, GObject.TYPE_STRING)
        self.mainApp._downloadTreeView.set_model(model)
        #model = self.mainApp._downloadTreeView.get_model()

    def _data_percent(self, column, cell, model, iter, data):
        percent = model.get_value(iter, self.COL_PERCENT)
        if percent == -1:
            cell.props.pulse = percent
        else:
            cell.props.value = percent

    def exec_percent_child(self, id, name, percent, details):
        print("send " + id + " " + name + " " + details)
        text = ""#desc[:]
        if percent > 1:
            percent = 1
        text = "<small>"
        text += "100%" #_("%s%") % (str(percent))
        text += "</small>"
        model = self.mainApp._downloadTreeView.get_model()

        try:
            iter = self._download_map[id]
        except KeyError:
            adj = self.mainApp._downloadTreeView.get_vadjustment()
            is_scrolled_down = (adj.get_value() + adj.get_page_size() ==
                                adj.get_upper())
            time = datetime.datetime.fromtimestamp(int(details)).strftime('%Y-%m-%d %H:%M:%S')
            iter = model.append((percent, name, time, id))
            self._download_map[id] = iter
            #if is_scrolled_down:
            #    self.mainApp._downloadTreeView.scroll_to_cell(model.get_path(iter),
            #        None, False, False, False)
        #else:
        #    model.set_value(iter, self.COL_TEXT, text)
        '''
        self.window = self.mainApp._mainWindow
        self.builder = self.mainApp.interface

        self.progress_window = self.builder.get_object("progress_window")
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
        '''

    def preformUninstall(self, packagesCollect):
        print("uninstall: " + str(packagesCollect))
        #self.trans.mainApp._roleLabel.set_text("Uninstall: " + str(packageName))
        #self.trans.mainApp.interface.connect_signals(self.signals)
        #Gtk.main()
           

    def install_finished(self, need_restart):
        self.load_extensions()
        if need_restart:
            self.show_info(_("One or more active %s may have been updated. You probably need to restart Cinnamon for the changes to take effect") % (self.pl_noun))

    def preformInstall(self, packagesCollect):
        print("install: " + str(packagesCollect))
        #self.trans.mainApp._roleLabel.set_text("Uninstall: " + str(packageName))
        #self.trans.mainApp.interface.connect_signals(self.signals)
        listUninstall = packagesCollect.split(",")
        collectType = listUninstall[0]
        del listUninstall[0]
        print("" + collectType)
        if(collectType in self.validTypes):
            print("we goo for that")
            self.mainApp._roleLabel.set_text("Uninstall: " + collectType)
            self.mainApp.show()
            self.mainApp.refresh()
            self.trans.install_all(collectType, listUninstall)
            #sleep(1.1)
            print("sleep")
            Gtk.main()
            #Gtk.main_quit()

    def preformUpgrade(self, packageName):
        print("upgrade:" + str(packageName))
        #self.trans.mainApp._roleLabel.set_text("Uninstall: " + str(packageName))
        #self.trans.mainApp.interface.connect_signals(self.signals)
        #Gtk.main()

    def preformUpdate(self, collectType):
        print("update:" + str(collectType))
        self._create_download_model()
        self.mainApp._roleLabel.set_text("Uninstall: " + collectType)
        self.mainApp.show()
        self.trans.refresh_cache(collectType)
        #self.trans.mainApp._roleLabel.set_text("Uninstall: " + str(packageName))
        #self.trans.mainApp.interface.connect_signals(self.signals)
        Gtk.main()

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

    def _custom_dialog(self, dialog_type, title, message):
        '''
        This is a generic Gtk Message Dialog function.
        dialog_type = this is a Gtk type.
        '''
        dialog = Gtk.MessageDialog(None, 0, dialog_type,
            Gtk.ButtonsType.OK, "")
        dialog.set_markup("<b>%s</b>" % title)
        dialog.format_secondary_markup(message)
        dialog.run()
        dialog.destroy()

    def show_info(title):
            message = _("If you detect any problem or you want to contribute,\n" + \
                      "please visit: <a href='%s'>Cinnamon Installer</a>.") % WEB_SITE_URL
            _custom_dialog(Gtk.MessageType.INFO, title, message)

    def on_ChooseButton_clicked(self, *args):
        self.mainApp._chooseDialog.hide()
        self.mainApp.refresh()
        for row in self.mainApp._chooseList:
            if row[0] is True:
                self.trans.to_add.add(row[1].split(':')[0]) # split done in case of optdep choice

    def on_progress_textview_size_allocate(self, *args):
        #auto-scrolling method
        adj = self.mainApp._terminalTextView.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def on_choose_renderertoggle_toggled(self, widget, line):
        self.mainApp._chooseList[line][0] = not self.mainApp._chooseList[line][0]

    def on_PreferencesCloseButton_clicked(self, *args):
        self.mainApp._preferencesWindow.hide()

    def on_PreferencesWindow_delete_event(self, *args):
        self.mainApp._preferencesWindow.hide()
        # return True is needed to not destroy the window
        return True

    def on_PreferencesValidButton_clicked(self, *args):
        pass

    def on_confAceptButton_clicked(self, *args):
        GObject.idle_add(self.exec_Transaction)
        sleep(0.1)

    def on_confCancelButton_clicked(self, *args):
        self.mainApp._confDialog.hide()
        self.mainApp.refresh()
        self.trans.release()
        #self.exiting('')

    def on_ProgressCloseButton_clicked(self, *args):
        self.mainApp._mainWindow.hide()
        self.mainApp.refresh()
        self.transaction_done = True
        #self.trans.checkUpdates()
        Gtk.main_quit()

    def on_ProgressCancelButton_clicked(self, *args):
        self.trans.interrupt()
        self.mainApp._mainWindow.hide()
        self.mainApp.refresh()
        #self.exiting('')
        Gtk.main_quit()

    def handle_error(self, service, error):
        GObject.idle_add(self.show_Error, (error))
        sleep(0.1)

    def handle_replay(self, service, replay):
        try:
            GObject.idle_add(self.exec_replay, (replay,))
            self.mainApp.refresh()
            sleep(0.1)
        except Exception as e:
            print(str(e))

    def handle_updates(self, service, syncfirst, updates):
        GObject.idle_add(self.exec_update, (syncfirst, updates,))
        sleep(0.1)

    def action_handler(self, service, action):
        GObject.idle_add(self.exec_action, (action))
        sleep(0.05)

    def action_long_handler(self, service, action_long):
        GObject.idle_add(self.exec_action_long, (action_long))
        sleep(0.1)

    def icon_handler(self, service, icon):
        self.mainApp._actionImage.set_from_icon_name(icon, Gtk.IconSize.BUTTON)
        self.mainApp.refresh()

    def target_handler(self, service, target):
        GObject.idle_add(self.target_change, (target))
        sleep(0.05)

    def percent_handler(self, service, percent):
        GObject.idle_add(self.exec_percent, (percent))
        sleep(0.05)

    def percent_child_handler(self, service, id, name, percent, details):
        GObject.idle_add(self.exec_percent_child, id, name, percent, details)
        sleep(0.1)

    def need_details_handler(self, service, need):
        GObject.idle_add(self.exec_need_details, (need))
        sleep(0.1)

    def transaction_start_handler(self, service, msg):
        GObject.idle_add(self.exec_transaction_start)
        sleep(0.05)

    def log_error(self, msg):
        GObject.idle_add(self.throw_error, (msg))
        sleep(0.1)
        #self.throw_error(msg)

    def log_warning(self, service, msg):
        GObject.idle_add(self.throw_warning, (msg))
        sleep(0.1)
        #self.throw_warning(msg)

    def exec_replay(self, replay):
        self.mainApp._closeButton.set_visible(True)
        self.mainApp._actionImage.set_from_icon_name('dialog-information', Gtk.IconSize.BUTTON)
        self.mainApp._roleLabel.set_text(str(replay))
        self.mainApp._statusLabel.set_text(str(replay))
        self.mainApp._progressBar.set_text('')
        end_iter = self.mainApp._terminalTextBuffer.get_end_iter()
        self.mainApp._terminalTextBuffer.insert(end_iter, str(replay))
        self.mainApp.refresh()

    def throw_warning(self, msg):
        self.mainApp._warningDialog.format_secondary_text(msg)
        response = self.mainApp._warningDialog.run()
        self.mainApp.refresh()
        if response:
            self.mainApp._warningDialog.hide()

    def throw_error(self, msg):
        self.mainApp._errorDialog.format_secondary_text(msg)
        response = self.mainApp._errorDialog.run()
        self.mainApp.refresh()
        if response:
            self.mainApp._errorDialog.hide()

    def exec_transaction_start(self):
        self.mainApp._cancelButton.set_visible(False)
        self.mainApp.refresh()

    def exec_need_details(self, need):
        self.mainApp._terminalExpander.set_expanded(need)
        self.details = need;
        self.mainApp.refresh()

    def exec_percent(self, percent):
        if percent > 1:
            self.mainApp._progressBar.pulse()
            self.mainApp._progressBar.set_text('')
        else:
            self.mainApp._progressBar.set_fraction(percent)
        self.mainApp.refresh()

    def target_change(self, target):
        self.mainApp._progressBar.set_text(target)
        self.mainApp.refresh()

    def exec_action_long(self, action_long):
        end_iter = self.mainApp._terminalTextBuffer.get_end_iter()
        self.mainApp._terminalTextBuffer.insert(end_iter, action_long)
        self.mainApp.refresh()

    def exec_action(self, action):
        self.mainApp._statusLabel.set_text(action)
        if action in ("Downloading", "Downloading index"):
            self.mainApp._terminalExpander.set_sensitive(True)
            self.mainApp._downloadScrolled.show()
            self.mainApp._terminalTextView.hide()
            if self.terminal:
                self.terminal.hide()
        else:
            self.mainApp._downloadScrolled.hide()
            self.mainApp._terminalTextView.show()
            if self.terminal:
                self.terminal.hide()
            self.mainApp._terminalExpander.set_sensitive(False)
            self.mainApp._terminalExpander.set_expanded(False)
        self.mainApp.refresh()

    def show_Error(self, error):
        #self.mainApp._mainWindow.hide()
        self.mainApp.refresh()
        if error:
            this._show_error(_("Cinnamon Installer Error"), error)
        self.exiting(error)

    def config_signals(self):
        self.trans.service.connect("EmitTransactionDone", self.handle_replay)
        self.trans.service.connect("EmitTransactionError", self.handle_error)
        self.trans.service.connect("EmitAvailableUpdates", self.handle_updates)
        self.trans.service.connect("EmitAction", self.action_handler)
        self.trans.service.connect("EmitActionLong", self.action_long_handler)
        self.trans.service.connect("EmitIcon", self.icon_handler)
        self.trans.service.connect("EmitTarget", self.target_handler)
        self.trans.service.connect("EmitPercent", self.percent_handler)
        self.trans.service.connect("EmitDownloadPercentChild", self.percent_child_handler)
        self.trans.service.connect("EmitNeedDetails", self.need_details_handler)
        self.trans.service.connect("EmitTransactionStart", self.transaction_start_handler)
        self.trans.service.connect("EmitLogError", self.log_error)
        self.trans.service.connect("EmitLogWarning", self.log_warning)
