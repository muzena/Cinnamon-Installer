#! /usr/bin/python3
# -*- coding: utf-8 -*-
#
# Cinnamon Installer
#
# Authors: Lester Carballo Pérez <lestcape@gmail.com>
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


import subprocess, os, fnmatch, signal, re, sys, os
from gi.repository import Gtk, GObject
from time import sleep
from threading import Thread

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"
sys.path.append(DIR_PATH)
GUI_PATH = os.path.dirname(os.path.dirname(os.path.dirname(DIR_PATH))) + "/"

import executerkit

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

class Transaction(object):
    def __init__(self, mainApp):
        self.mainApp = mainApp
        self.mainApp.interface.set_translation_domain(DOMAIN)
        self.cancel_download = False
        self.details = False
        self.service = executerkit.InstallerService()
        self.available_updates = (False, [])
        self.to_add = []
        self.to_remove = []
        self.to_update = []
        self.to_trans = []
        self._terminalTextBuffer = self.mainApp._terminalTextView.get_buffer()
        self.colors_regexp = re.compile('\\033\[(\d;)?\d*m')
        self.currPackage = ''
        self.releaseTransaction = False
        self.loop = GObject.MainLoop()

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

    def prepare_transaction(self):
        if self.to_add or self.to_remove:
            self.action_handler(None, _('Preparing')+'...')
            self.icon_handler(None, 'cinnamon-installer-setup')
            self.target_handler(None, '')
            self.percent_handler(None, 0)
            self._terminalTextBuffer.delete(self._terminalTextBuffer.get_start_iter(), self._terminalTextBuffer.get_end_iter())
            self.mainApp._cancelButton.set_visible(False)
            self.mainApp._closeButton.set_visible(False)
            self.mainApp._terminalExpander.set_visible(True)
            self.mainApp._mainWindow.show()
            self.updateGtk()
            # we need to give some time to the window to refresh
            #sleep(0.1)
            error = ''
            self.mainApp._cancelButton.set_visible(True)
            self.updateGtk()
            sleep(0.2)
            print("prepare_transaction")
            if(len(self.to_remove) > 0):
                result = self.prepare_remove(self.to_remove)
            elif(len(self.to_add) > 0):
                result = self.prepare_add(self.to_add)
            if(isinstance(result, str)):
                error += result
            else:
                self.to_trans = result

            if self.releaseTransaction:
                error = _("Transaction Cancel")

            if not error:
                self.set_transaction_sum()
                self.mainApp._confDialog.show_all()
                self.updateGtk()
                sleep(0.4)
            else:
                self.release()
                return(error)
        else:
            return (_('Nothing to do'))

    def prepare_remove(self, pkgNames):
        result = []
        thread = Thread(target = self.service.prepare_remove, args=(pkgNames, self.loop, result,))
        thread.start()
        self.loop.run()
        if(self.releaseTransaction):
            return _("Transaction Cancel")
        return result[0];

    def prepare_add(self, pkgNames):
        print("prepare_add")
        result = []
        thread = Thread(target = self.service.prepare_add, args=(pkgNames, self.loop, result,))
        thread.start()
        self.loop.run()
        if(self.releaseTransaction):
            return _("Transaction Cancel")
        return result[0];

    def commit(self, sender=None, connexion=None):
        error = ''
        if(len(self.to_remove) > 0):
            error += self.remove(self.to_remove)
        elif(len(self.to_add) > 0):
            error += self.add(self.to_add)
        return error

    def remove(self, pkgNames):
        result = []
        thread = Thread(target = self.service.remove, args=(pkgNames, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0];

    def add(self, pkgname):
        result = []
        thread = Thread(target = self.service.add, args=(pkgname, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0];

    def get_transaction_sum(self):
        transaction_dict = {'to_remove': [], 'to_install': [], 'to_update': [], 'to_reinstall': [], 'to_downgrade': []}
        _to_transaction = sorted(self.to_trans)
        for name, version, dtype, dsize in _to_transaction:
            if (dtype == 1):
                transaction_dict['to_install'].append((name+' '+version, dsize))
            elif (dtype == 2):
                transaction_dict['to_remove'].append(name+' '+version)
            elif (dtype == 3):
                transaction_dict['to_update'].append(name+' '+version)
        '''
        others
        for name, version, dsize in others:
            pkg = self.get_localpkg(name)
            if pkg:
                comp = executer.pyalpm.vercmp(version, pkg.version)
                if comp == 1:
                    transaction_dict['to_update'].append((name+' '+version, dsize))
                elif comp == 0:
                    transaction_dict['to_reinstall'].append((name+' '+version, dsize))
                elif comp == -1:
                    transaction_dict['to_downgrade'].append((name+' '+version, dsize))
            else:
                transaction_dict['to_install'].append((name+' '+version, dsize))
        '''
        #~ if transaction_dict['to_install']:
            #~ print('To install:', [name for name, size in transaction_dict['to_install']])
        #~ if transaction_dict['to_reinstall']:
            #~ print('To reinstall:', [name for name, size in transaction_dict['to_reinstall']])
        #~ if transaction_dict['to_downgrade']:
            #~ print('To downgrade:', [name for name, size in transaction_dict['to_downgrade']])
        #~ if transaction_dict['to_remove']:
            #~ print('To remove:', [name for name in transaction_dict['to_remove']])
        #~ if transaction_dict['to_update']:
            #~ print('To update:', [name for name, size in transaction_dict['to_update']])
        return transaction_dict

    def set_transaction_sum(self, show_updates = True):
        dsize = 0
        self.mainApp._transactionSum.clear()
        transaction_dict = self.get_transaction_sum()
        self.mainApp._sumTopLabel.set_markup('<big><b>{}</b></big>'.format(_('Transaction Summary')))
        if transaction_dict['to_remove']:
            self.mainApp._transactionSum.append([_('To remove')+':', transaction_dict['to_remove'][0]])
            i = 1
            while i < len(transaction_dict['to_remove']):
                self.mainApp._transactionSum.append(['', transaction_dict['to_remove'][i]])
                i += 1
        if transaction_dict['to_downgrade']:
            self.mainApp._transactionSum.append([_('To downgrade')+':', transaction_dict['to_downgrade'][0][0]])
            dsize += transaction_dict['to_downgrade'][0][1]
            i = 1
            while i < len(transaction_dict['to_downgrade']):
                self.mainApp._transactionSum.append(['', transaction_dict['to_downgrade'][i][0]])
                dsize += transaction_dict['to_downgrade'][i][1]
                i += 1
        if transaction_dict['to_install']:
            self.mainApp._transactionSum.append([_('To install')+':', transaction_dict['to_install'][0][0]])
            dsize += transaction_dict['to_install'][0][1]
            i = 1
            while i < len(transaction_dict['to_install']):
                self.mainApp._transactionSum.append(['', transaction_dict['to_install'][i][0]])
                dsize += transaction_dict['to_install'][i][1]
                i += 1
        if transaction_dict['to_reinstall']:
            self.mainApp._transactionSum.append([_('To reinstall')+':', transaction_dict['to_reinstall'][0][0]])
            dsize += transaction_dict['to_reinstall'][0][1]
            i = 1
            while i < len(transaction_dict['to_reinstall']):
                self.mainApp._transactionSum.append(['', transaction_dict['to_reinstall'][i][0]])
                dsize += transaction_dict['to_reinstall'][i][1]
                i += 1
        if show_updates:
            if transaction_dict['to_update']:
                self.mainApp._transactionSum.append([_('To update')+':', transaction_dict['to_update'][0][0]])
                dsize += transaction_dict['to_update'][0][1]
                i = 1
                while i < len(transaction_dict['to_update']):
                    self.mainApp._transactionSum.append(['', transaction_dict['to_update'][i][0]])
                    dsize += transaction_dict['to_update'][i][1]
                    i += 1
        else:
            for name, size in transaction_dict['to_update']:
                dsize += size
        if dsize == 0:
            self.mainApp._sumBottomLabel.set_markup('')
        else:
            unit = 'Bt'
            if dsize > 1000:
                dsize = dsize/1000
                unit = 'Kb'
                if dsize > 1000:
                    dsize = dsize/1000
                    unit = 'Mb'
                    if dsize > 1000:
                        dsize = round(dsize/1000, 2)
                        unit = 'Gb'
                    else:
                        dsize = round(dsize, 2)
                else:
                    dsize = round(dsize, 2)
            else:
                dsize = round(dsize, 2)
               
            self.mainApp._sumBottomLabel.set_markup('<b>{} {} {}</b>'.format(_('Total download size:'), dsize, unit))

    def updateGtk(self):
        while Gtk.events_pending():
            Gtk.main_iteration()

    def release(self):
        self.releaseTransaction = True;
        ##self.loop.quit()
        thread = Thread(target = self.service.Release, args=(self.loop,))
        thread.start()
        #self.loop.run()


    def config_signals(self):
        self.service.connect("EmitAction", self.action_handler)
        self.service.connect("EmitActionLong", self.action_long_handler)
        self.service.connect("EmitIcon", self.icon_handler)
        self.service.connect("EmitTarget", self.target_handler)
        self.service.connect("EmitPercent", self.percent_handler)
        self.service.connect("EmitNeedDetails", self.need_details_handler)
        self.service.connect("EmitTransactionStart", self.transaction_start_handler)
        self.service.connect("EmitLogError", self.log_error)
        self.service.connect("EmitLogWarning", self.log_warning)

    def action_handler(self, obj, action):
        GObject.idle_add(self.exec_action, (action))
        sleep(0.05)

    def exec_action(self, action):
        self.mainApp._statusLabel.set_text(action)
        if(action == _('Test commit')+'...'):
             self.mainApp._cancelButton.set_visible(False)
        self.updateGtk()

    def action_long_handler(self, obj, action_long):
        GObject.idle_add(self.exec_action_long, (action_long))
        sleep(0.05)

    def exec_action_long(self, action_long):
        end_iter = self._terminalTextBuffer.get_end_iter()
        self._terminalTextBuffer.insert(end_iter, action_long+"\n")
        if(action_long == _('Test commit')+'...'):
            self.mainApp._cancelButton.set_visible(False)
        self.updateGtk()

    def need_details_handler(self, obj, need):
        GObject.idle_add(self.exec_need_details, (need))
        sleep(0.1)

    def exec_need_details(self, need):
        self.mainApp._terminalExpander.set_expanded(need)
        self.details = need;
        self.updateGtk()

    def icon_handler(self, obj, icon):
        GObject.idle_add(self.exec_icon_handler, (icon))
        sleep(0.05)

    def exec_icon_handler(self, icon):
        self.mainApp._actionImage.set_from_icon_name(icon, Gtk.IconSize.BUTTON)
        self.updateGtk()

    def target_handler(self, obj, target):
        GObject.idle_add(self.target_change, (target))
        sleep(0.05)

    def target_change(self, target):
        self.mainApp._progressBar.set_text(target)
        self.updateGtk()

    def percent_handler(self, obj, percent):
        GObject.idle_add(self.print_percent, (percent))
        #try:
        #    if percent > 1:
        #        self.mainApp._progressBar.pulse()
        #        self.mainApp._progressBar.set_text('')
        #    else:
        #        self.mainApp._progressBar.set_fraction(percent)
        #    self.updateGtk()
        #except Exception as e:
        #    print(e)

    def print_percent(self, percent):
        try:
            if percent > 1:
                self.mainApp._progressBar.pulse()
                self.mainApp._progressBar.set_text('')
            else:
                self.mainApp._progressBar.set_fraction(percent)
            self.updateGtk()
        except Exception as e:
            print(e)

    def transaction_start_handler(self, obj, msg):
        self.mainApp._cancelButton.set_visible(False)
        self.updateGtk()

    def log_error(self, msg):
        GObject.idle_add(self.throw_error, (msg))
        sleep(0.1)
        #self.throw_error(msg)

    def log_warning(self, obj, msg):
        GObject.idle_add(self.throw_warning, (msg))
        sleep(0.1)
        #self.throw_warning(msg)

    def throw_warning(self, msg):
        self.mainApp._warningDialog.format_secondary_text(msg)
        response = self.mainApp._warningDialog.run()
        self.updateGtk()
        if response:
            self.mainApp._warningDialog.hide()

    def throw_error(self, msg):
        self.mainApp._errorDialog.format_secondary_text(msg)
        response = self.mainApp._errorDialog.run()
        self.updateGtk()
        if response:
            self.mainApp._errorDialog.hide()

    def choose_provides(self, data):
        virtual_dep = str(data[1])
        providers = data[0]
        self.mainApp._chooseLabel.set_markup('<b>{}</b>'.format(_('{pkgname} is provided by {number} packages.\nPlease choose those you would like to install:').format(pkgname = virtual_dep, number = str(len(providers)))))
        self.mainApp._chooseList.clear()
        for name in providers:
            self.mainApp._chooseList.append([False, str(name)])
        lenght = len(self.to_add)
        self.mainApp._chooseDialog.run()
        if len(self.to_add) == lenght: # no choice was done by the user
            self.to_add.add(self.mainApp._chooseList.get(self.mainApp._chooseList.get_iter_first(), 1)[0]) # add first provider

    def on_choose_renderertoggle_toggled(self, widget, line):
        self.mainApp._chooseList[line][0] = not self.mainApp._chooseList[line][0]

    def on_ChooseButton_clicked(self, *args):
        self.mainApp._chooseDialog.hide()
        self.updateGtk()
        for row in self.mainApp._chooseList:
            if row[0] is True:
                self.to_add.add(row[1].split(':')[0]) # split done in case of optdep choice

    def on_progress_textview_size_allocate(self, *args):
        #auto-scrolling method
        adj = self.mainApp._terminalTextView.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def on_PreferencesValidButton_clicked(self, *args):
        self.mainApp._preferencesWindow.hide()

    def on_PreferencesCloseButton_clicked(self, *args):
        self.mainApp._preferencesWindow.hide()

    def on_PreferencesWindow_delete_event(self, *args):
        self.mainApp._preferencesWindow.hide()
        # return True is needed to not destroy the window
        return True

    def download(self, url_list, path):
        def write_file(chunk):
            nonlocal transferred
            nonlocal f
            if self.cancel_download:
                if ftp:
                    ftp.quit()
                raise Exception('Download cancelled')
                return
            f.write(chunk)
            transferred += len(chunk)
            if total_size > 0:
                percent = round(transferred/total_size, 2)
                self.percent_handler(None, percent)
                if transferred <= total_size:
                    target = '{transferred}/{size}'.format(transferred = common.format_size(transferred), size = common.format_size(total_size))
                else:
                    target = ''
                self.target_handler(None, target)
            self.updateGtk()
	
        self.cancel_download = False
        ftp = None
        total_size = 0
        transferred = 0
        self.icon_handler(None, 'cinnamon-installer-download')
        self.mainApp._cancelButton.set_visible(True)
        self.mainApp._closeButton.set_visible(False)
        parsed_urls = []
        for url in url_list:
            url_components = urlparse(url)
            if url_components.scheme:
                parsed_urls.append(url_components)
        print(parsed_urls)
        for url_components in parsed_urls:
            if url_components.scheme == 'http':
                total_size += int(requests.get(url).headers['Content-Length'])
            elif url_components.scheme == 'ftp':
                ftp = FTP(url_components.netloc)
                ftp.login('anonymous', '')
                total_size += int(ftp.size(url_components.path))
        print(total_size)
        for url_components in parsed_urls:
            filename = url_components.path.split('/')[-1]
            print(filename)
            action = _('Downloading {pkgname}').format(pkgname = filename)+'...'
            action_long = action+'\n'
            self.action_handler(None, action)
            self.action_long_handler(None, action_long)
            self.mainApp._mainWindow.show()
            self.updateGtk()
            with open(os.path.join(path, filename), 'wb') as f:
                if url_components.scheme == 'http':
                    try:
                        r = requests.get(url, stream = True)
                        for chunk in r.iter_content(1024):
                            if self.cancel_download:
                                raise Exception('Download cancelled')
                                break
                            else:
                                write_file(chunk)
                    except Exception as e:
                        print(e)
                        self.cancel_download = False
                elif url_components.scheme == 'ftp':
                    try:
                        ftp = FTP(url_components.netloc)
                        ftp.login('anonymous', '') 
                        ftp.retrbinary('RETR '+url_components.path, write_file, blocksize=1024)
                    except Exception as e:
                        print(e)
                        self.cancel_download = False
