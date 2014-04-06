#! /usr/bin/python3
# -*- coding: utf-8 -*-
#
# Cinnamon Installer
#
# Authors: Lester Carballo Pérez <lestcape@gmail.com>
#
# Original version from: Guillaume Benoit <guillaume@manjaro.org>
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

from gi.repository import GObject, Gio, Polkit
import re, os, sys
from time import sleep

import pyalpm
from multiprocessing import Process

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"
sys.path.append(DIR_PATH)

import config, common, aur

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

def format_error(data):
    errstr = data[0].strip('\n')
    errno = data[1]
    detail = data[2]
    if detail:
        # detail is a list of '\n' terminated strings
        return '{}:\n'.format(errstr) + ''.join(i for i in detail)
    else:
        return errstr

class InstallerService(GObject.GObject):
    __gsignals__ = {
        'EmitTransactionDone': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitTransactionError': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitAvailableUpdates': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN, GObject.TYPE_BOOLEAN,)),
        'EmitAction': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitActionLong': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitNeedDetails': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_BOOLEAN,)),
        'EmitIcon': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitTarget': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitPercent': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_FLOAT,)),
        'EmitLogError': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitLogWarning': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitTransactionStart': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'EmitReloadConfig': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,))
    }


    def __init__(self):
        GObject.GObject.__init__(self)
        self.t = None
        self.task = None
        self.error = ''
        self.warning = ''
        self.providers = []
        self.previous_action = ''
        self.previous_action_long = ''
        self.previous_icon = ''
        self.previous_target = ''
        self.previous_percent = 0
        self.total_size = 0
        self.already_transferred = 0
        self.local_packages = set()
        self.aur_updates_checked = False
        self.aur_updates_pkgs = []
        self.localdb = None
        self.syncdbs = None
        self.get_handle()

    def startTransaction(self):
        myservice = InstallerService()

    def stopTransaction(self):
        self.StopDaemon()

    def get_handle(self):
        self.handle = config.handle()
        self.localdb = self.handle.get_localdb()
        self.syncdbs = self.handle.get_syncdbs()
        self.handle.dlcb = self.cb_dl
        self.handle.totaldlcb = self.totaldlcb
        self.handle.eventcb = self.cb_event
        self.handle.questioncb = self.cb_question
        self.handle.progresscb = self.cb_progress
        self.handle.logcb = self.cb_log

    def get_local_packages(self):
        self.local_packages = set()
        sync_pkg = None
        for pkg in self.localdb.pkgcache:
            for db in self.syncdbs:
                sync_pkg = db.get_pkg(pkg.name)
                if sync_pkg:
                    break
            if not sync_pkg:
                self.local_packages.add(pkg.name)

    def check_finished_commit(self, loop):
        if self.task.is_alive():
            if loop:
                loop.quit()
            return True
        else:
            self.get_handle()
            if loop:
                loop.quit()
            return False

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

    def EmitReloadConfig(self, message):
        # recheck aur updates next time
        self.aur_updates_checked = False
        # reload config
        config.installer_conf.reload()
        self.emit("EmitReloadConfig", message)

    def cb_event(self, event, tupel):
        action = self.previous_action
        action_long = self.previous_action_long
        icon = self.previous_icon
        if event == 'ALPM_EVENT_CHECKDEPS_START':
            action = _('Checking dependencies')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-search'
        elif event == 'ALPM_EVENT_CHECKDEPS_DONE':
            if self.warning:
                self.EmitLogWarning(self.warning)
                self.warning = ''
        elif event == 'ALPM_EVENT_FILECONFLICTS_START':
            action = _('Checking file conflicts')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-search'
        elif event == 'ALPM_EVENT_FILECONFLICTS_DONE':
            pass
        elif event == 'ALPM_EVENT_RESOLVEDEPS_START':
            action = _('Resolving dependencies')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-setup'
        elif event == 'ALPM_EVENT_RESOLVEDEPS_DONE':
            if self.warning:
                self.EmitLogWarning(self.warning)
                self.warning = ''
        elif event == 'ALPM_EVENT_INTERCONFLICTS_START':
            action = _('Checking inter conflicts')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-search'
        elif event == 'ALPM_EVENT_INTERCONFLICTS_DONE':
            if self.warning:
                self.EmitLogWarning(self.warning)
                self.warning = ''
        elif event == 'ALPM_EVENT_ADD_START':
            string = _('Installing {pkgname}').format(pkgname = tupel[0].name)
            action = string+'...'
            action_long = '{} ({})...\n'.format(string, tupel[0].version)
            icon = 'cinnamon-installer-add'
        elif event == 'ALPM_EVENT_ADD_DONE':
            formatted_event = 'Installed {pkgname} ({pkgversion})'.format(pkgname = tupel[0].name, pkgversion = tupel[0].version)
            common.write_log_file(formatted_event)
        elif event == 'ALPM_EVENT_REMOVE_START':
            string = _('Removing {pkgname}').format(pkgname = tupel[0].name)
            action = string+'...'
            action_long = '{} ({})...\n'.format(string, tupel[0].version)
            icon = 'cinnamon-installer-delete'
        elif event == 'ALPM_EVENT_REMOVE_DONE':
            formatted_event = 'Removed {pkgname} ({pkgversion})'.format(pkgname = tupel[0].name, pkgversion = tupel[0].version)
            common.write_log_file(formatted_event)
        elif event == 'ALPM_EVENT_UPGRADE_START':
            string = _('Upgrading {pkgname}').format(pkgname = tupel[1].name)
            action = string+'...'
            action_long = '{} ({} => {})...\n'.format(string, tupel[1].version, tupel[0].version)
            icon = 'cinnamon-installer-update'
        elif event == 'ALPM_EVENT_UPGRADE_DONE':
            formatted_event = 'Upgraded {pkgname} ({oldversion} -> {newversion})'.format(pkgname = tupel[1].name, oldversion = tupel[1].version, newversion = tupel[0].version)
            common.write_log_file(formatted_event)
        elif event == 'ALPM_EVENT_DOWNGRADE_START':
            string = _('Downgrading {pkgname}').format(pkgname = tupel[1].name)
            action = string+'...'
            action_long = '{} ({} => {})...\n'.format(string, tupel[1].version, tupel[0].version)
            icon = 'cinnamon-installer-add'
        elif event == 'ALPM_EVENT_DOWNGRADE_DONE':
            formatted_event = 'Downgraded {pkgname} ({oldversion} -> {newversion})'.format(pkgname = tupel[1].name, oldversion = tupel[1].version, newversion = tupel[0].version)
            common.write_log_file(formatted_event)
        elif event == 'ALPM_EVENT_REINSTALL_START':
            string = _('Reinstalling {pkgname}').format(pkgname = tupel[0].name)
            action = string+'...'
            action_long = '{} ({})...\n'.format(string, tupel[0].version)
            icon = 'cinnamon-installer-add'
        elif event == 'ALPM_EVENT_REINSTALL_DONE':
            formatted_event = 'Reinstalled {pkgname} ({pkgversion})'.format(pkgname = tupel[0].name, pkgversion = tupel[0].version)
            common.write_log_file(formatted_event)
        elif event == 'ALPM_EVENT_INTEGRITY_START':
            action = _('Checking integrity')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-search'
            self.already_transferred = 0
        elif event == 'ALPM_EVENT_INTEGRITY_DONE':
            pass
        elif event == 'ALPM_EVENT_LOAD_START':
            action = _('Loading packages files')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-search'
        elif event == 'ALPM_EVENT_LOAD_DONE':
            pass
        elif event == 'ALPM_EVENT_DELTA_INTEGRITY_START':
            action = _('Checking delta integrity')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-search'
        elif event == 'ALPM_EVENT_DELTA_INTEGRITY_DONE':
            pass
        elif event == 'ALPM_EVENT_DELTA_PATCHES_START':
            action = _('Applying deltas')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-setup'
        elif event == 'ALPM_EVENT_DELTA_PATCHES_DONE':
            pass
        elif event == 'ALPM_EVENT_DELTA_PATCH_START':
            action = _('Generating {} with {}').format(tupel[0], tupel[1])+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-setup'
        elif event == 'ALPM_EVENT_DELTA_PATCH_DONE':
            action = _('Generation succeeded!')
            action_long = action+'\n'
        elif event == 'ALPM_EVENT_DELTA_PATCH_FAILED':
            action = _('Generation failed.')
            action_long = action+'\n'
        elif event == 'ALPM_EVENT_SCRIPTLET_INFO':
            action =_('Configuring {pkgname}').format(pkgname = self.previous_target)+'...'
            action_long = tupel[0]
            icon = 'cinnamon-installer-setup'
            self.EmitNeedDetails(True)
        elif event == 'ALPM_EVENT_RETRIEVE_START':
            action = _('Downloading')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-download'
        elif event == 'ALPM_EVENT_DISKSPACE_START':
            action = _('Checking available disk space')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-search'
        elif event == 'ALPM_EVENT_OPTDEP_REQUIRED':
            print('Optionnal deps exist')
        elif event == 'ALPM_EVENT_DATABASE_MISSING':
            #action =_('Database file for {} does not exist').format(tupel[0])+'...'
            #action_long = action
            pass
        elif event == 'ALPM_EVENT_KEYRING_START':
            action = _('Checking keyring')+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-search'
        elif event == 'ALPM_EVENT_KEYRING_DONE':
            pass
        elif event == 'ALPM_EVENT_KEY_DOWNLOAD_START':
            action = _('Downloading required keys')+'...'
            action_long = action+'\n'
        elif event == 'ALPM_EVENT_KEY_DOWNLOAD_DONE':
            pass
        if action != self.previous_action:
            self.previous_action = action
            self.EmitAction(action)
        if action_long != self.previous_action_long:
            self.previous_action_long != action_long
            self.EmitActionLong(action_long)
        if icon != self.previous_icon:
            self.previous_icon = icon
            self.EmitIcon(icon)
        print(event)

    def cb_question(self, event, data_tupel, extra_data):
        if event == 'ALPM_QUESTION_INSTALL_IGNOREPKG':
            return 0 # Do not install package in IgnorePkg/IgnoreGroup
        if event == 'ALPM_QUESTION_REPLACE_PKG':
            self.warning += _('{pkgname1} will be replaced by {pkgname2}').format(pkgname1 = data_tupel[0].name, pkgname2 = data_tupel[1].name)+'\n'
            return 1 # Auto-remove conflicts in case of replaces
        if event == 'ALPM_QUESTION_CONFLICT_PKG':
            self.warning += _('{pkgname1} conflicts with {pkgname2}').format(pkgname1 = data_tupel[0], pkgname2 = data_tupel[1])+'\n'
            return 1 # Auto-remove conflicts
        if event == 'ALPM_QUESTION_CORRUPTED_PKG':
            return 1 # Auto-remove corrupted pkgs in cache
        if event == 'ALPM_QUESTION_REMOVE_PKGS':
            return 1 # Do not upgrade packages which have unresolvable dependencies
        if event == 'ALPM_QUESTION_SELECT_PROVIDER':
            ## In this case we populate providers with different choices
            ## the client will have to release transaction and re-init one 
            ## with the chosen package added to it
            self.providers.append(([pkg.name for pkg in data_tupel[0]], data_tupel[1]))
            return 0 # return the first choice, this is not important because the transaction will be released
        if event == 'ALPM_QUESTION_IMPORT_KEY':
            ## data_tupel = (revoked(int), length(int), pubkey_algo(string), fingerprint(string), uid(string), created_time(int))
            if data_tupel[0] is 0: # not revoked
                return 1 # Auto get not revoked key
            if data_tupel[0] is 1: # revoked
                return 0 # Do not get revoked key

    def cb_log(self, level, line):
        _logmask = pyalpm.LOG_ERROR | pyalpm.LOG_WARNING
        if not (level & _logmask):
            return
        if level & pyalpm.LOG_ERROR:
            #self.EmitLogError(line)
            _error = _('Error: ')+line
            self.EmitActionLong(_error)
            self.EmitNeedDetails(True)
            print(line)
        elif level & pyalpm.LOG_WARNING:
            self.warning += line
            _warning = _('Warning: ')+line
            self.EmitActionLong(_warning)
        elif level & pyalpm.LOG_DEBUG:
            line = "DEBUG: " + line
            print(line)
        elif level & pyalpm.LOG_FUNCTION:
            line = "FUNC: " + line
            print(line)

    def totaldlcb(self, _total_size):
        self.total_size = _total_size

    def cb_dl(self, _target, _transferred, _total):
        if _target.endswith('.db'):
            action = _('Refreshing {repo}').format(repo = _target.replace('.db', ''))+'...'
            action_long = ''
            icon = 'cinnamon-installer-refresh'
        else:
            action = _('Downloading {pkgname}').format(pkgname = _target.replace('.pkg.tar.xz', ''))+'...'
            action_long = action+'\n'
            icon = 'cinnamon-installer-download'
        if self.total_size > 0:
            percent = round((_transferred+self.already_transferred)/self.total_size, 2)
            if _transferred+self.already_transferred <= self.total_size:
                target = '{transferred}/{size}'.format(transferred = common.format_size(_transferred+self.already_transferred), size = common.format_size(self.total_size))
            else:
                target = ''
        else:
            percent = round(_transferred/_total, 2)
            target = ''
        if action != self.previous_action:
            self.previous_action = action
            self.EmitAction(action)
        if action_long != self.previous_action_long:
            self.previous_action_long = action_long
            self.EmitActionLong(action_long)
        if icon != self.previous_icon:
            self.previous_icon = icon
            self.EmitIcon(icon)
        if target != self.previous_target:
            self.previous_target = target
            self.EmitTarget(target)
        if percent != self.previous_percent:
            self.previous_percent = percent
            self.EmitPercent(percent)
        elif _transferred == _total:
            self.already_transferred += _total

    def cb_progress(self, event, target, _percent, n, i):
        if event in ('ALPM_PROGRESS_ADD_START', 'ALPM_PROGRESS_UPGRADE_START', 'ALPM_PROGRESS_DOWNGRADE_START', 'ALPM_PROGRESS_REINSTALL_START', 'ALPM_PROGRESS_REMOVE_START'):
            percent = round(((i-1)/n)+(_percent/(100*n)), 2)
        else:
            percent = round(_percent/100, 2)
        if percent == 0:
            self.EmitTransactionStart('')
        if target != self.previous_target:
            self.previous_target = target
        if percent >= self.previous_percent + 1:
            self.EmitTarget('{}/{}'.format(str(i), str(n)))
            self.previous_percent = percent
            self.EmitPercent(percent)

    def SetPkgReason(self, pkgname, reason, loop, result):
        error = ''
        try:
            pkg = self.localdb.get_pkg(pkgname)
            if pkg:
                self.handle.set_pkgreason(pkg, reason)
        except Exception as er:
            error = format_error(er.args)
        result.append(error)
        sleep(0.1)
        loop.quit()

    def CheckUpdates(self, success, nosuccess, loop):
        #success('')
        syncfirst = False
        updates = []
        _ignorepkgs = set()
        self.get_handle()
        for group in self.handle.ignoregrps:
            db = self.localdb
            grp = db.read_grp(group)
            if grp:
                name, pkg_list = grp
                for pkg in pkg_list:
                    _ignorepkgs.add(pkg.name)
        for name in self.handle.ignorepkgs:
            pkg = self.localdb.get_pkg(name)
            if pkg:
                _ignorepkgs.add(pkg.name)
        if config.syncfirst:
            for name in config.syncfirst:
                pkg = self.localdb.get_pkg(name)
                if pkg:
                    candidate = pyalpm.sync_newversion(pkg, self.syncdbs)
                    if candidate:
                        syncfirst = True
                        updates.append((candidate.name, candidate.version, candidate.db.name, '', candidate.download_size))
        if not updates:
            if config.enable_aur:
                if not self.aur_updates_checked:
                    self.get_local_packages()
                    self.local_packages -= _ignorepkgs
            for pkg in self.localdb.pkgcache:
                if not pkg.name in _ignorepkgs:
                    candidate = pyalpm.sync_newversion(pkg, self.syncdbs)
                    if candidate:
                        updates.append((candidate.name, candidate.version, candidate.db.name, '', candidate.download_size))
                        self.local_packages.discard(pkg.name)
            if config.enable_aur:
                if not self.aur_updates_checked:
                    if self.local_packages:
                        self.aur_updates_pkgs = aur.multiinfo(self.local_packages)
                        self.aur_updates_checked = True
                for aur_pkg in self.aur_updates_pkgs:
                    if self.localdb.get_pkg(aur_pkg.name):
                        comp = pyalpm.vercmp(aur_pkg.version, self.localdb.get_pkg(aur_pkg.name).version)
                        if comp == 1:
                            updates.append((aur_pkg.name, aur_pkg.version, aur_pkg.db.name, aur_pkg.tarpath, aur_pkg.download_size))
        self.EmitAvailableUpdates(syncfirst, updates)
        loop.quit()

    def Refresh(self, force_update, loop):
        print("Refresh")
        def refresh():
            self.target = ''
            self.percent = 0
            error = ''
            for db in self.syncdbs:
                try:
                    self.t = self.handle.init_transaction()
                    db.update(force = bool(force_update))
                    self.t.release()
                except pyalpm.error as e:
                    print(e)
                    error += format_error(e.args)
                    break
            if error:
                self.EmitTransactionError(error)
            else:
                self.EmitTransactionDone('')
        self.task = Process(target=refresh)
        self.task.start()
        GObject.timeout_add(100, self.check_finished_commit, loop)

    def Init(self, options, loop, result):
        error = ''
        try:
            self.subject = Polkit.UnixProcess.new(os.getppid())
            self.subject.set_uid(0)
            self.get_handle()
            self.t = self.handle.init_transaction(**options)
            print('Init:',self.t.flags)
        except pyalpm.error as e:
            print(str(e))
            error = format_error(e.args)
        finally:
            result.append(error)
            sleep(0.1)
            loop.quit()
            #return error

    def Sysupgrade(self, downgrade, loop, result):
        error = ''
        try:
            self.t.sysupgrade(downgrade = bool(downgrade))
        except pyalpm.error as e:
            error = format_error(e.args)
            self.t.release()
        finally:
            result.append(error)
            sleep(0.1)
            loop.quit()
            #return error

    def Remove(self, pkgname, loop, result):
        error = ''
        try:
            pkg = self.localdb.get_pkg(pkgname)
            if pkg is not None:
                self.t.remove_pkg(pkg)
        except pyalpm.error as e:
            error = format_error(e.args)
        finally:
            result.append(error)
            sleep(0.1)
            loop.quit()
            #return error

    def Add(self, pkgname, loop, result):
        error = ''
        try:
            for db in self.syncdbs:
                # this is a security, in case of virtual package it will
                # choose the first provider, the choice should have been
                # done by the client
                pkg = pyalpm.find_satisfier(db.pkgcache, pkgname)
                if pkg:
                    self.t.add_pkg(pkg)
                    break
        except pyalpm.error as e:
            error = format_error(e.args)
        finally:
            result.append(error)
            sleep(0.1)
            loop.quit()
            #return error

    def Load(self, tarball_path, loop, result):
        error = ''
        try:
            pkg = self.handle.load_pkg(tarball_path)
            if pkg:
                self.t.add_pkg(pkg)
        except pyalpm.error:
            error = _('{pkgname} is not a valid path or package name').format(pkgname = tarball_path)
        finally:
            result.append(error)
            sleep(0.1)
            loop.quit()
            #return error

    def check_extra_modules(self):
        to_add = set(pkg.name for pkg in self.t.to_add)
        to_remove = set(pkg.name for pkg in self.t.to_remove)
        to_check = [pkg for pkg in self.t.to_add]
        already_checked = set(pkg.name for pkg in to_check)
        depends = [to_check]
        # get installed kernels and modules
        pkgs = self.localdb.search('linux')
        installed_kernels = set()
        installed_modules =  set()
        for pkg in pkgs:
            match = re.match("(linux[0-9]{2,3})(.*)", pkg.name)
            if match:
                installed_kernels.add(match.group(1))
                if match.group(2):
                    installed_modules.add(match.group(2))
        for pkg in self.t.to_add:
            match = re.match("(linux[0-9]{2,3})(.*)", pkg.name)
            if match:
                installed_kernels.add(match.group(1))
                if match.group(2):
                    installed_modules.add(match.group(2))
        # check in to_remove if there is a kernel and if so, auto-remove the corresponding modules 
        for pkg in self.t.to_remove:
            match = re.match("(linux[0-9]{2,3})(.*)", pkg.name)
            if match:
                if not match.group(2):
                    installed_kernels.discard(match.group(1))
                    for module in installed_modules:
                        pkgname = match.group(1)+module
                        if not pkgname in to_remove:
                            _pkg = self.localdb.get_pkg(pkgname)
                            if _pkg:
                                # Check we won't remove a third party kernel
                                third_party = False
                                for provide in _pkg.provides:
                                    if 'linux=' in provide:
                                        third_party = True
                                if not third_party:
                                    to_remove.add(pkgname)
                                    self.t.remove_pkg(_pkg)
        # start loops to check pkgs
        i = 0
        while depends[i]:
            # add a empty list for new pkgs to check next loop
            depends.append([])
            # start to check one pkg
            for pkg in depends[i]:
                # check if the current pkg is a kernel and if so, check if a module is required to install
                match = re.match("(linux[0-9]{2,3})(.*)", pkg.name)
                if match:
                    if not match.group(2): # match pkg is a kernel
                        for module in installed_modules:
                            pkgname = match.group(1) + module
                            if not self.localdb.get_pkg(pkgname):
                                for db in self.syncdbs:
                                    _pkg = db.get_pkg(pkgname)
                                    if _pkg:
                                        if not _pkg.name in already_checked:
                                            depends[i+1].append(_pkg)
                                            already_checked.add(_pkg.name)
                                        if not _pkg.name in to_add | to_remove:
                                            to_add.add(_pkg.name)
                                            self.t.add_pkg(_pkg)
                                        break
                # check if the current pkg is a kernel module and if so, install it for all installed kernels
                match = re.match("(linux[0-9]{2,3})(.*-modules)", pkg.name)
                if match:
                    for kernel in installed_kernels:
                        pkgname = kernel + match.group(2)
                        if not self.localdb.get_pkg(pkgname):
                            for db in self.syncdbs:
                                _pkg = db.get_pkg(pkgname)
                                if _pkg:
                                    if not _pkg.name in already_checked:
                                        depends[i+1].append(_pkg)
                                        already_checked.add(_pkg.name)
                                    if not _pkg.name in to_add | to_remove:
                                        to_add.add(_pkg.name)
                                        self.t.add_pkg(_pkg)
                                    break
                for depend in pkg.depends:
                    found_depend = pyalpm.find_satisfier(self.localdb.pkgcache, depend)
                    if not found_depend:
                        for db in self.syncdbs:
                            found_depend = pyalpm.find_satisfier(db.pkgcache, depend)
                            if found_depend:
                                break
                    if found_depend:
                        # add the dep in list to check its deps in next loop 
                        if not found_depend.name in already_checked:
                            depends[i+1].append(found_depend)
                            already_checked.add(found_depend.name)
            i += 1
            # end of the loop

    def Prepare(self, loop, result):
        error = ''
        self.providers.clear()
        self.check_extra_modules()
        try:
            self.t.prepare()
        except pyalpm.error as e:
            print("Error")
            error = format_error(e.args)
            self.t.release()
        else:
            for pkg in self.t.to_remove:
                if pkg.name in config.holdpkg:
                    error = _('The transaction cannot be performed because it needs to remove {pkgname1} which is a locked package').format(pkgname1 = pkg.name)
                    self.t.release()
                    break
        finally:
            try:
                summ = len(self.t.to_add) + len(self.t.to_remove)
            except pyalpm.error:
                result.append([((), error)])
            if summ == 0:
                self.t.release()
                result.append([((), _('Nothing to do'))])
            elif error:
                result.append([((), error)])
            elif self.providers:
                result.append(self.providers)
            else:
                result.append([((), '')])
            loop.quit()

    def To_Remove(self, loop, result):
        _list = []
        result.append(_list)
        try:
            for pkg in self.t.to_remove:
                _list.append((pkg.name, pkg.version))
        except:
            pass

        sleep(0.1)
        loop.quit()
        #return _list

    def To_Add(self, loop, result):
        _list = []
        result.append(_list)
        try:
            for pkg in self.t.to_add:
                _list.append((pkg.name, pkg.version, pkg.download_size))
        except:
            pass
        sleep(0.1)
        loop.quit()
        #return _list

    def Interrupt(self, loop):
        def interrupt():
            try:
                self.t.interrupt()
            except:
                pass
            try:
                self.t.release()
            except:
                pass
            finally:
                common.rm_lock_file()
        if self.task:
            self.task.terminate()
        interrupt()
        loop.quit()

    def Commit(self, loop):
        error = ''
        try:
            self.t.commit()
        except pyalpm.error as e:
            error = format_error(e.args)
        except Exception:
            pass
        finally:
            self.t.release()
            if self.warning:
                self.EmitLogWarning(self.warning)
                self.warning = ''
            if error:
                self.EmitTransactionError(error)
            else:
                self.EmitTransactionDone(_('Transaction successfully finished'))
        sleep(0.1)
        loop.quit()

    def Release(self, loop):
        try:
            self.t.release()
        except:
            pass
        sleep(0.1)
        loop.quit()

    def StopDaemon(self):
        try:
            self.t.release()
        except:
            pass
        #common.rm_pid_file()
        #self.mainloop.quit()

    def WriteConfig(self, array, loop, result):
        error = ''
        with open(config.INSTALLER_PATH, 'r') as conffile:
            data = conffile.readlines()
        i = 0
        while i < len(data):
            line = data[i].strip()
            if len(line) == 0:
                i += 1
                continue
            if line[0] == '#':
                line = line.lstrip('#')
            if line == '\n':
                i += 1
                continue
            old_key, equal, old_value = [x.strip() for x in line.partition('=')]
            for tupel in array:
                new_key = tupel[0]
                new_value = tupel[1]
                if old_key == new_key:
                    # i is equal to the line number where we find the key in the file
                    if new_key in config.SINGLE_OPTIONS:
                        data[i] = '{} = {}\n'.format(new_key, new_value)
                    elif new_key in config.BOOLEAN_OPTIONS:
                        if new_value == 'False': 
                            data[i] = '#{}\n'.format(new_key)
                        else:
                            data[i] = '{}\n'.format(new_key)
            i += 1
        with open(config.INSTALLER_PATH, 'w') as conffile:
            conffile.writelines(data)
        self.EmitReloadConfig('')
        result.append(error)
        sleep(0.1)
        loop.quit()
