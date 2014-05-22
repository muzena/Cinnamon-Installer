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

from gi.repository import PackageKitGlib as packagekit
from gi.repository import GObject, Gio, GLib

import re, os, sys
from time import sleep
from multiprocessing import Process

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


'''
def make_locale_string():
    loc = locale.getlocale(locale.LC_MESSAGES)
    if loc[1]:
        return loc[0] + '.' + loc[1]
    return loc[0]

def get_installed_files(pkclient, pkgname):
    p = self._get_one_package(pkgname)
    if not p:
        return []
    res = pkclient.get_files((p.get_id(),), None, self._on_progress_changed, None)
    files = res.get_files_array()
    if not files:
        return []
    return files[0].get_property('files')

def _get_one_package(self, pkgname, pfilter=packagekit.FilterEnum.NONE, cache=USE_CACHE):
   LOG.debug("package_one %s", pkgname) #, self._cache.keys()
   ps = self._get_packages(pkgname, pfilter)
   if not ps:
      # also keep it in not found, to prevent further calls of resolve
      if pkgname not in self._notfound_cache_pkg:
          LOG.debug("blacklisted %s", pkgname)
          self._notfound_cache_pkg.append(pkgname)
          return None
   return ps[0]

def _get_packages(self, pkgname, pfilter=packagekit.FilterEnum.NONE):
    """ make sure we're ready and have a working cache """
    if not self._ready:
        return None
    """ resolve a package name into a PkPackage object or return None """
    LOG.debug("fetch packages for %s", pkgname) #, self._cache.keys()
    if pfilter in (packagekit.FilterEnum.NONE, packagekit.FilterEnum.NOT_SOURCE):
        cache_pkg_filter = self._cache_pkg_filter_none
    elif pfilter in (packagekit.FilterEnum.NEWEST,):
        cache_pkg_filter = self._cache_pkg_filter_newest
    else:
        cache_pkg_filter = None
    # if cache and cache_pkg_filter is not None and (pkgname in cache_pkg_filter.keys()):
    # return cache_pkg_filter[pkgname]
    pfilter = 1 << pfilter
    # we never want source packages
    pfilter |= 1 << packagekit.FilterEnum.NOT_SOURCE
    pkgs = []
    if pkgname in self._pkgs_cache:
        pkgs.append(self._pkgs_cache[pkgname])
    if pkgs:
        LOG.debug('Found package: %s' % pkgname)
    #print "Package: %s", self._pkgs_cache[pkgname]
    return pkgs
'''

def progress_cb(status, typ, data=None):
    pass
    #if status.get_property('package'):
        #print "Pachet ", status.get_property('package'), status.get_property('package-id')
        #if status.get_property('package'):
            #print status.get_property('package').get_name()
    #print typ, status.get_property('package')

def format_error(data):
    errstr = data[0].strip('\n')
    #errno = data[1]
    #detail = data[2]
    #if detail:
        # detail is a list of '\n' terminated strings
    return '{}:\n'.format(errstr) #+ ''.join(i for i in detail)
    #else:
    #    return errstr

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
        'EmitTransactionStart': (GObject.SIGNAL_RUN_FIRST, None, (GObject.TYPE_STRING,))
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
        self.previous_package = ''
        self.previous_percent = 0
        self.total_size = 0
        self.already_transferred = 0
        self.local_packages = set()
        self.aur_updates_checked = False
        self.aur_updates_pkgs = []
        self.localdb = None
        self.syncdbs = None
        self.cancelTransaction = None;
        self.client = packagekit.Client();

    def _get_installed(self, packages):
        result = self.client.resolve(packagekit.FilterEnum.INSTALLED, packages, None, self._progress_pcb, None)
        pkgs = result.get_package_array()
        return pkgs

    def _get_aviable(self, packages):
        result = self.client.resolve(packagekit.FilterEnum.NONE, packages, None, self._progress_pcb, None)
        pkgs = result.get_package_array()
        resultPkgs = []
        for name in packages:
            notInstalled = None
            for pkg in pkgs:
                if (pkg.get_name() == name):
                    if (pkg.get_info() == packagekit.InfoEnum.INSTALLED):
                        break
                    else:
                        notInstalled = pkg
            if notInstalled is not None:
                resultPkgs.append(notInstalled)
        return resultPkgs

    def _get_package_details(self, pkgs):
        pkgsId = []
        for pkg in pkgs:
            if (not (pkg.get_id() in pkgsId)):
                pkgsId.append(pkg.get_id())
        try:
            task = packagekit.Task()
            result = task.get_details_sync(pkgsId, None, self._progress_pcb, None)
        except GObject.GError as e:
            return None
        pkgsDetails = result.get_details_array()
        if not pkgsDetails:
            return None
        resultDetails = []
        currVal = 0
        for pkg in pkgs:
            for details in pkgsDetails:
                if (pkg.get_id() == details.get_property('package-id')):
                    resultDetails.append((pkg, details))
                    break
            if (len(resultDetails) == currVal):
                resultDetails.append((pkg, None))
            currVal = currVal + 1
        return resultDetails

    def get_local_packages(self, packages, loop, result):
        self.local_packages = set()
        result.append(self.local_packages)
        try:
            pkgs = self._get_installed(packages)
            if pkgs:
                for pkg in pkgs:
                    if (not (pkg.get_name() in self.local_packages)):
                        self.local_packages.add(pkg.get_name())
        except GLib.GError as e:
            print(e)
        sleep(0.1)
        loop.quit()

    def get_remote_packages(self, packages, loop, result):
        self.remote_packages = set()
        result.append(self.remote_packages)
        try:
            pkgs = self._get_aviable(packages)
            if pkgs:
                for pkg in pkgs:
                    if (not (pkg.get_name() in self.remote_packages)):
                        self.remote_packages.add(pkg.get_name())
        except GLib.GError as e:
            print(e)
        sleep(0.1)
        loop.quit()

    def prepare_remove(self, pkgNames, loop, result):
        ''' Returns a package names list of reverse dependencies
        which will be removed if the packages are removed.'''
        error = ''
        try:
            pkgs = self._get_installed(pkgNames)
            listToRemove = []
            listTupleRemove = []
            if pkgs:
                for pkg in pkgs:
                    if (not (pkg.get_name() in listToRemove)):
                        listToRemove.append(pkg.get_id())
                if len(listToRemove) > 0:
                    autoremove = False
                    # simulate RemovePackages()
                    res = self.client.remove_packages(2 ** packagekit.TransactionFlagEnum.SIMULATE,
                                                      listToRemove,
                                                      True, # allow deps
                                                      autoremove,
                                                      None,
                                                      self._progress_pcb, None)
                if res:
                    listPkgs = res.get_package_array()
                    details = self._get_package_details(listPkgs)
                    if details:
                        for p, det in details:
                            if (p.get_info() == packagekit.InfoEnum.INSTALLED):
                                if det is not None:
                                    listTupleRemove.append((p.get_name(), p.get_version(), 3, det.get_property('size')))
                                else:
                                    listTupleRemove.append((p.get_name(), p.get_version(), 3, -1))
                            else:
                                if det is not None:
                                    listTupleRemove.append((p.get_name(), p.get_version(), 2, det.get_property('size')))
                                else:
                                    listTupleRemove.append((p.get_name(), p.get_version(), 2, -1))

                result.append(listTupleRemove)

        except GLib.GError as e:
            error = format_error(e.args)
            result.append(error)
        finally:
            sleep(0.1)
            loop.quit()

    def prepare_add(self, pkgNames, loop, result):
        ''' Returns a package names list of reverse dependencies
        which will be installed if the packages are installed.'''
        error = ''
        try:
            pkgs = self._get_aviable(pkgNames)
            listToAdd = []
            listTupleAdd = []
            if pkgs:
                for pkg in pkgs:
                    if (not (pkg.get_name() in listToAdd)):
                        listToAdd.append(pkg.get_id())
                if len(listToAdd) > 0:
                    # simulate AddPackages()
                    res = self.client.install_packages(2 ** packagekit.TransactionFlagEnum.SIMULATE,
                                                       listToAdd,
                                                       None,
                                                       self._progress_pcb, None)

                if res:
                    listPkgs = res.get_package_array()
                    details = self._get_package_details(listPkgs)
                    if details:
                        for p, det in details:
                            if (p.get_info() == packagekit.InfoEnum.INSTALLED):
                                if det is not None:
                                    listTupleAdd.append((p.get_name(), p.get_version(), 3, det.get_property('size')))
                                else:
                                    listTupleAdd.append((p.get_name(), p.get_version(), 3, -1))
                            else:
                                if det is not None:
                                    listTupleAdd.append((p.get_name(), p.get_version(), 1, det.get_property('size')))
                                else:
                                    listTupleAdd.append((p.get_name(), p.get_version(), 1, -1))

            result.append(listTupleAdd)

        except GLib.GError as e:
            error = format_error(e.args)
            print(error)
            result.append(error)
        finally:
            sleep(0.1)
            loop.quit()

    def remove(self, pkgNames, loop, result):
        error = ''
        try:
            self.cancelTransaction = Gio.Cancellable();
            pkgs = self._get_installed(pkgNames)
            listToRemove = []
            if pkgs:
                for pkg in pkgs:
                    if (not (pkg.get_name() in listToRemove)):
                        listToRemove.append(pkg.get_id())
                if len(listToRemove) > 0:
                    autoremove = False
                    res = self.client.remove_packages(packagekit.TransactionFlagEnum.NONE,
                                                      listToRemove,
                                                      True, # allow deps
                                                      autoremove,
                                                      self.cancelTransaction,
                                                      self._progress_cb, None)
                if not res:
                    result.append(_("Fail to process the removal of package %s").format(pkgNames))

            if(self.cancelTransaction.is_cancelled()):
                error = _("Transaction Cancel")
                print("cancel")

        except GLib.GError as e:
            error = format_error(e.args)
        finally:
            result.append(error)
            sleep(0.1)
            loop.quit()

    def add(self, pkgNames, loop, result):
        error = ''
        try:
            self.cancelTransaction = Gio.Cancellable();
            pkgs = self._get_aviable(pkgNames)
            listToAdd = []
            if pkgs:
                for pkg in pkgs:
                    if (not (pkg.get_name() in listToAdd)):
                        listToAdd.append(pkg.get_id())
                if len(listToAdd) > 0:
                    res = self.client.install_packages(packagekit.TransactionFlagEnum.NONE,
                                                      listToAdd,
                                                      self.cancelTransaction,
                                                      self._progress_cb, None)
                if not res:
                    result.append(_("Fail to process the installation of package %s").format(pkgNames))

            if(self.cancelTransaction.is_cancelled()):
                error = _("Transaction Cancel")
                print("cancel")

        except GLib.GError as e:
            error = format_error(e.args)
        finally:
            result.append(error)
            sleep(0.1)
            loop.quit()
    '''
    def Interrupt(self, loop):
        def interrupt():
            try:
                pass
            except:
                pass
            finally:
                pass
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
    '''
    def Release(self, loop):
        try:
            if(self.cancelTransaction):
                self.cancelTransaction.cancel()
        except:
            pass
        sleep(0.1)
        ##loop.quit()

    def _progress_pcb(self, status, typ, data=None):
        action = self.previous_action
        action_long = self.previous_action_long
        icon = self.previous_icon
        if(typ.value_name == "PK_PROGRESS_TYPE_PERCENTAGE"):
           percent = status.get_property('percentage')
           if((percent > 0) and (percent != self.previous_percent)):
               self.previous_percent = percent
               self.EmitPercent(percent/100)
               self.EmitTarget(str(percent)+"%")
               #print("Preparing percentage: " + str(percent))
        elif(typ.value_name == "PK_PROGRESS_TYPE_STATUS"):
            if(status.get_property('status') == packagekit.StatusEnum.RUNNING):
                icon = 'cinnamon-installer-search'
                action = _('Resolving dependencies')+'...'
                action_long = action
        if icon != self.previous_icon:
            self.previous_icon = icon
            self.EmitIcon(icon)
        if action != self.previous_action:
            self.previous_action = action
            self.EmitAction(action)
        if action_long != self.previous_action_long:
            self.previous_action_long = action_long
            self.EmitActionLong(action_long)
        #if status.get_property('package'):
        #    print("Pachet " + status.get_property('package'))
        #    if status.get_property('package-id'):
        #        print("" + status.get_property('package').get_name() + " " + status.get_property('package-id'))
        #elif(typ.value_name == "PK_PROGRESS_TYPE_ROLE"):
        #    print(packagekit.role_enum_to_string(status.get_property('role')))
        #elif(typ.value_name == "PK_PROGRESS_TYPE_STATUS"):
        #    print(packagekit.status_enum_to_string(status.get_property('status')))
        #print("Preparing: " + str(typ) + " " + str(status.get_property('package')))


    def _progress_cb(self, status, typ, data=None):
        action = self.previous_action
        action_long = self.previous_action_long
        icon = self.previous_icon
        target = self.previous_target
        package = self.previous_package
        if(typ.value_name == "PK_PROGRESS_TYPE_PERCENTAGE"):
           percent = status.get_property('percentage')
           if((percent > 0) and (percent != self.previous_percent)):
               self.previous_percent = percent
               self.EmitPercent(percent/100)
               target = str(percent) + " %"
               #print("percent:" + str(percent))
        elif(typ.value_name == "PK_PROGRESS_TYPE_ROLE"):
            if(status.get_property('role') == packagekit.RoleEnum.DOWNLOAD_PACKAGES):
                action = _('Downloading')+'...'
            elif(status.get_property('role') == packagekit.RoleEnum.INSTALL_PACKAGES):
                action = _('Installing')+'...'
            elif(status.get_property('role') == packagekit.RoleEnum.REMOVE_PACKAGES):
                action = _('Removing')+'...'
        elif(typ.value_name == "PK_PROGRESS_TYPE_STATUS"):
            if(status.get_property('status') == packagekit.StatusEnum.DOWNLOAD):
                action = _('Downloading')+'...'
                action_long = action
                icon = 'cinnamon-installer-download'
            elif(status.get_property('status') == packagekit.StatusEnum.COMMIT):
                action = _('Commit')+'...'
                action_long = action
            elif(status.get_property('status') == packagekit.StatusEnum.TEST_COMMIT):
                action = _('Test commit')+'...'
                action_long = action
            elif(status.get_property('status') == packagekit.StatusEnum.SETUP):
                action = _('Configuring')+'...'
                action_long = action
            elif(status.get_property('status') == packagekit.StatusEnum.RUNNING):
                action = _('Running')+'...'
                action_long = action
            elif(status.get_property('status') == packagekit.StatusEnum.SIG_CHECK):
                action = _('Checking integrity')+'...'
                action_long = action
            elif(status.get_property('status') == packagekit.StatusEnum.INSTALL):
                action = _('Installing')+'...' 
                action_long = action
                icon = 'cinnamon-installer-add'
            elif(status.get_property('status') == packagekit.StatusEnum.DEP_RESOLVE):
                action = _('Resolving dependencies')+'...'
                action_long = action
            elif(status.get_property('status') == packagekit.StatusEnum.REMOVE):
                action = _('Removing')+'...'
                action_long = action
                icon = 'cinnamon-installer-delete'
            elif(status.get_property('status') == packagekit.StatusEnum.FINISHED):
                action = _('Finished')
                action_long = action
                self.previous_percent = -1
            elif(status.get_property('status') == packagekit.StatusEnum.WAITING_FOR_AUTH):
                action = _('Waiting for authorization')
                action_long = action
                icon = 'cinnamon-installer-setup'

        if(typ.value_name == "PK_PROGRESS_TYPE_PACKAGE"):
            package = status.get_property('package').get_name()
            if self.previous_package != package:
                self.previous_package = package
                send_log = ''
                if self.previous_action_long == _('Installing')+'...':
                    send_log = _('Installing {pkgname}').format(pkgname = package) + '...'
                elif self.previous_action_long == _('Removing')+'...':
                    send_log = _('Removing {pkgname}').format(pkgname = package) + '...'
                self.EmitActionLong(send_log)
        if package != self.previous_package:
            self.previous_package = package
        if target != self.previous_target:
            self.previous_target = target
            self.EmitTarget(target)
        if action != self.previous_action:
            self.previous_action = action
            self.EmitAction(action)
        if action_long != self.previous_action_long:
            self.previous_action_long = action_long
            self.EmitActionLong(action_long)
        if icon != self.previous_icon:
            self.previous_icon = icon
            self.EmitIcon(icon)

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
'''
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
'''
