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


import subprocess, os, fnmatch, signal, re, sys, os
from gi.repository import Gtk, GObject
from time import sleep
from threading import Thread

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"
sys.path.append(DIR_PATH)
GUI_PATH = os.path.dirname(os.path.dirname(os.path.dirname(DIR_PATH))) + "/"

import config, common, aur, executer

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
        self.inUpdate = False
        self.cancel_download = False
        self.build_proc = None
        self.details = False
        self.service = executer.InstallerService()
        self.available_updates = (False, [])
        self.to_add = set()
        self.to_remove = set()
        self.to_update = set()
        self.to_load = set()
        self.to_mark_as_dep = set()
        self.make_depends = set()
        self.build_depends = set()
        self.to_build = []
        self._terminalTextBuffer = self.mainApp._terminalTextView.get_buffer()
        self.base_devel = ('autoconf', 'automake', 'binutils', 'bison', 'fakeroot', 
                           'file', 'findutils', 'flex', 'gawk', 'gcc', 'gettext', 
                           'grep', 'groff', 'gzip', 'libtool', 'm4', 'make', 'patch', 
                           'pkg-config', 'sed', 'sudo', 'texinfo', 'util-linux', 'which')
        self.colors_regexp = re.compile('\\033\[(\d;)?\d*m')
        self.loop = GObject.MainLoop()
        #self.mainApp.interface.connect_signals(self)

    def refresh(self, force_update = False):
        self.updateGtk()
        self.action_handler(None, _('Refreshing')+'...')
        self.icon_handler(None, 'cinnamon-installer-refresh')
        self.target_handler(None, '')
        self.percent_handler(None, 0)
        self.mainApp._cancelButton.set_visible(True)
        self.mainApp._closeButton.set_visible(False)
        self.mainApp._terminalExpander.set_visible(True)
        self.mainApp._mainWindow.show()
        self.updateGtk()
        self.Refresh(force_update)

    def Refresh(self, force_update):
        thread = Thread(target = self.service.Refresh, args=(force_update, self.loop,))
        thread.start()
        self.loop.run()
        #self.service.Refresh(force_update)

    def updateGtk(self):
        while Gtk.events_pending():
            Gtk.main_iteration()

    def checkUpdates(self):
        thread = Thread(target = self.service.CheckUpdates, args=(None, None, self.loop))
        thread.start()
        self.loop.run()
        #self.service.CheckUpdates(None, None)

    def init(self, **options):
        result = []
        thread = Thread(target = self.service.Init, args=(options, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0]
        #return self.service.Init(**options)

    def sysUpgrade(self, downgrade):
        result = []
        thread = Thread(target = self.service.Sysupgrade, args=(downgrade, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0]
        #return self.service.Sysupgrade(downgrade)

    def sysupgrade(self, show_updates = True, downgrade = False):
        syncfirst, updates = self.available_updates
        if updates:
            self.to_update.clear()
            self.to_add.clear()
            self.to_remove.clear()
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
            for name, version, db, tarpath, size in updates:
                if db == 'AUR':
                    # call AURPkg constructor directly to avoid a request to AUR
                    infos = {'name': name, 'version': version, 'Description': '', 'URLPath': tarpath}
                    pkg = aur.AURPkg(infos)
                    self.to_build.append(pkg)
                else:
                    self.to_update.add(name)
            error = ''
            if syncfirst:
                self.mainApp._cancelButton.set_visible(True)
                error += self.init_transaction()
                if not error:
                    for name in self.to_update:
                        error += self.add(name)
                        if not error:
                            error += self.prepare()
            else:
                if self.to_build:
                    # check if packages in to_build have deps or makedeps which need to be install first 
                    # grab errors differently here to not break regular updates
                    _error = self.check_to_build()
                if self.to_update or self.to_add:
                    self.mainApp._cancelButton.set_visible(True)
                    error += self.init_transaction()
                    if not error:
                        if self.to_update:
                            error += self.sysUpgrade(downgrade)
                        _error = ''
                        for name in self.to_add:
                            _error += self.add(name)
                        if _error:
                            print(_error)
                        if not error:
                            error += self.prepare()
            if not error:
                    self.set_transaction_sum(show_updates = show_updates)
                    if show_updates:
                        self.mainApp._confDialog.show_all()
                        self.updateGtk()
                    else:
                        if len(self.mainApp._transactionSum) != 0:
                            self.mainApp._confDialog.show_all()
                            self.updateGtk()
                        else:
                            print("callllll")
                            self.finalize()
            if error:
                    self.mainApp._mainWindow.hide()
                    self.release()
            return error

    def remove(self, pkgname):
        result = []
        thread = Thread(target = self.service.Remove, args=(pkgname, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0];
        #return self.service.Remove(pkgname)

    def add(self, pkgname):
        result = []
        thread = Thread(target = self.service.Add, args=(pkgname, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0];
        #return self.service.Add(pkgname)

    def load(self, tarball_path):
        result = []
        thread = Thread(target = self.service.Load, args=(tarball_path, self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0];
        #return self.service.Load(tarball_path)

    def Prepare(self):
        result = []
        thread = Thread(target = self.service.Prepare, args=(self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0];
        #return self.service.Prepare()

    def prepare(self, trans_flags):
        error = ''
        ret = self.Prepare()
        # ret type is a(ass) so [([''], '')]
        if ret[0][0]: # providers are emitted
            print("Run release")
            self.release()
            print("Exit release")
            for item in ret:
                self.choose_provides(item)
            error += self.init_transaction(**trans_flags)
            if not error:
                for name in self.to_add:
                    error += self.add(name)
                for name in self.to_remove:
                    error += self.remove(name)
                for path in self.to_load:
                    error += self.load(path)
                if not error:
                    ret = self.Prepare()
                    if ret[0][1]:
                        error = str(ret[0][1])
        elif ret[0][1]: # an error is emitted
            error = str(ret[0][1])
        return(error)

    def to_Remove(self):
        result = []
        thread = Thread(target = self.service.To_Remove, args=(self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0];
        #return self.service.To_Remove()

    def to_Add(self):
        result = []
        thread = Thread(target = self.service.To_Add, args=(self.loop, result,))
        thread.start()
        self.loop.run()
        return result[0];
        #return self.service.To_Add()

    def commit(self, sender=None, connexion=None):
        thread = Thread(target = self.service.Commit, args=(self.loop,))
        thread.start()
        self.loop.run();
        #self.service.Commit(sender, connexion)

    def interrupt(self):
        thread = Thread(target = self.service.Interrupt, args=(self.loop,))
        thread.start()
        self.loop.run()
        #self.service.Interrupt()

    def release(self):
        self.loop.quit()
        thread = Thread(target = self.service.Release, args=(self.loop,))
        thread.start()
        self.loop.run()
        #self.service.Release()

    def stopDaemon(self):
        pass
        #self.service.StopDaemon()

    def setPkgReason(self, pkgname, reason):
        result = []
        thread = Thread(target = self.service.Release, args=(pkgname, reason, self.loop, result))
        thread.start()
        self.loop.run()
        return result[0]
        #self.service.SetPkgReason(pkgname, reason, sender, connexion)

    def writeConfig(self, array, sender=None, connexion=None):
        result = []
        thread = Thread(target = self.service.WriteConfig, args=(array, self.loop, result))
        thread.start()
        self.loop.run()
        return result[0]
        #self.service.WriteConfig(array, sender, connexion)

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
        self.mainApp._statusLabel.set_text(action)
        self.updateGtk()

    def action_long_handler(self, obj, action_long):
        GObject.idle_add(self.exec_action_long, (action_long))
        sleep(0.1)

    def exec_action_long(self, action_long):
        end_iter = self._terminalTextBuffer.get_end_iter()
        self._terminalTextBuffer.insert(end_iter, action_long)
        self.updateGtk()


    def need_details_handler(self, obj, need):
        GObject.idle_add(self.exec_need_details, (need))
        sleep(0.1)

    def exec_need_details(self, need):
        self.mainApp._terminalExpander.set_expanded(need)
        self.details = need;
        self.updateGtk()

    def icon_handler(self, obj, icon):
        self.mainApp._actionImage.set_from_icon_name(icon, Gtk.IconSize.BUTTON)
        self.updateGtk()

    def target_handler(self, obj, target):
        self.mainApp._progressBar.set_text(target)
        self.updateGtk()

    def percent_handler(self, obj, percent):
        #GObject.idle_add(self.print_percent, (percent))
        try:
            if percent > 1:
                self.mainApp._progressBar.pulse()
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
        data = []
        if self.mainApp._enableAURButton.get_active() != config.enable_aur:
            data.append(('EnableAUR', str(self.mainApp._enableAURButton.get_active())))
        if self.mainApp._removeUnrequiredDepsButton.get_active() != config.recurse:
            data.append(('RemoveUnrequiredDeps', str(self.mainApp._removeUnrequiredDepsButton.get_active())))
        if self.mainApp._refreshPeriodSpinButton.get_value() != config.refresh_period:
            data.append(('RefreshPeriod', str(self.mainApp._refreshPeriodSpinButton.get_value_as_int())))
        if data:
            self.writeConfig(data)
        self.mainApp._preferencesWindow.hide()

    def on_PreferencesCloseButton_clicked(self, *args):
        self.mainApp._preferencesWindow.hide()

    def on_PreferencesWindow_delete_event(self, *args):
        self.mainApp._preferencesWindow.hide()
        # return True is needed to not destroy the window
        return True

    def get_handle(self):
        self.handle = config.handle()
        self.syncdbs = self.handle.get_syncdbs()
        self.localdb = self.handle.get_localdb()

    def get_localpkg(self, name):
        return self.localdb.get_pkg(name)

    def get_syncpkg(self, name):
        for repo in self.syncdbs:
            pkg = repo.get_pkg(name)
            if pkg:
                return pkg

    def init_transaction(self, **options):
        return self.init(**options)

    def check_to_build(self):
        self.make_depends = set()
        self.build_depends = set()
        # check if base_devel packages are installed
        for name in self.base_devel:
            if not executer.pyalpm.find_satisfier(self.localdb.pkgcache, name):
                self.make_depends.add(name)
        already_checked = set()
        build_order = []
        i = 0
        error = ''
        while i < len(self.to_build):
            self.updateGtk()
            pkg = self.to_build[i]
            # if current pkg is not in build_order add it at the end of the list
            if not pkg.name in build_order:
                build_order.append(pkg.name)
            # download end extract tarball from AUR
            srcdir = aur.get_extract_tarball(pkg)
            if srcdir:
                # get PKGBUILD and parse it to create a new pkg object with makedeps and deps 
                new_pkgs = aur.get_pkgs(srcdir + '/PKGBUILD')
                for new_pkg in new_pkgs:
                    self.updateGtk()
                    print('checking', new_pkg.name)
                    # check if some makedeps must be installed
                    for makedepend in new_pkg.makedepends:
                        self.updateGtk()
                        if not makedepend in already_checked:
                            if not executer.pyalpm.find_satisfier(self.localdb.pkgcache, makedepend):
                                print('found make dep:',makedepend)
                                for db in self.syncdbs:
                                    provider = executer.pyalpm.find_satisfier(db.pkgcache, makedepend)
                                    if provider:
                                        break
                                if provider:
                                    self.make_depends.add(provider.name)
                                    already_checked.add(makedepend)
                                else:
                                    # current makedep need to be built
                                    raw_makedepend = common.format_pkg_name(makedepend)
                                    if raw_makedepend in build_order:
                                        # add it in build_order before pkg
                                        build_order.remove(raw_makedepend)
                                        index = build_order.index(pkg.name)
                                        build_order.insert(index, raw_makedepend)
                                    else:
                                        # get infos about it
                                        makedep_pkg = aur.info(raw_makedepend)
                                        if makedep_pkg:
                                            # add it in to_build so it will be checked 
                                            self.to_build.append(makedep_pkg)
                                            # add it in build_order before pkg
                                            index = build_order.index(pkg.name)
                                            build_order.insert(index, raw_makedepend)
                                            # add it in already_checked and to_add_as_as_dep 
                                            already_checked.add(raw_makedepend)
                                            self.to_mark_as_dep.add(raw_makedepend)
                                        else:
                                            if error:
                                                error += '\n'
                                            error += _('{pkgname} depends on {dependname} but it is not installable').format(pkgname = pkg.name, dependname = makedepend)
                    # check if some deps must be installed or built
                    for depend in new_pkg.depends:
                        self.updateGtk()
                        if not depend in already_checked:
                            if not executer.pyalpm.find_satisfier(self.localdb.pkgcache, depend):
                                print('found dep:',depend)
                                for db in self.syncdbs:
                                    provider = executer.pyalpm.find_satisfier(db.pkgcache, depend)
                                    if provider:
                                        break
                                if provider:
                                    # current dep need to be installed
                                    self.build_depends.add(provider.name)
                                    already_checked.add(depend)
                                else:
                                    # current dep need to be built
                                    raw_depend = common.format_pkg_name(depend)
                                    if raw_depend in build_order:
                                        # add it in build_order before pkg
                                        build_order.remove(raw_depend)
                                        index = build_order.index(pkg.name)
                                        build_order.insert(index, raw_depend)
                                    else:
                                        # get infos about it
                                        dep_pkg = aur.info(raw_depend)
                                        if dep_pkg:
                                            # add it in to_build so it will be checked 
                                            self.to_build.append(dep_pkg)
                                            # add it in build_order before pkg
                                            index = build_order.index(pkg.name)
                                            build_order.insert(index, raw_depend)
                                            # add it in already_checked and to_add_as_as_dep 
                                            already_checked.add(raw_depend)
                                            self.to_mark_as_dep.add(raw_depend)
                                        else:
                                            if error:
                                                error += '\n'
                                            error += _('{pkgname} depends on {dependname} but it is not installable').format(pkgname = pkg.name, dependname = depend)
            else:
                if error:
                    error += '\n'
                error += _('Failed to get {pkgname} archive from AUR').format(pkgname = pkg.name)
            i += 1
        if error:
            return error
        # add pkgname in make_depends and build_depends in to_add and to_mark_as_dep
        for name in self.make_depends:
            self.to_add.add(name)
            self.to_mark_as_dep.add(name)
        for name in self.build_depends:
            self.to_add.add(name)
            self.to_mark_as_dep.add(name)
        # reorder to_build following build_order
        self.to_build.sort(key = lambda pkg: build_order.index(pkg.name))
        #print('order:', build_order)
        print('to build:',self.to_build)
        print('makedeps:',self.make_depends)
        print('builddeps:',self.build_depends)
        return error

    def run(self, cascade = True, recurse = False):
        if self.to_add or self.to_remove or self.to_load or self.to_build:
            self.action_handler(None, _('Preparing')+'...')
            self.icon_handler(None, 'cinnamon-installer-setup')
            self.target_handler(None, '')
            self.percent_handler(None, 0)
            self._terminalTextBuffer.delete(self._terminalTextBuffer.get_start_iter(), self._terminalTextBuffer.get_end_iter())
            self.mainApp._cancelButton.set_visible(False)
            self.mainApp._closeButton.set_visible(False)
            self.mainApp._terminalExpander.set_visible(True)
            self.mainApp._mainWindow .show()
            self.updateGtk()
            # we need to give some time to the window to refresh
            sleep(0.1)
            error = ''
            if self.to_build:
                # check if packages in to_build have deps or makedeps which need to be install first
                error += self.check_to_build()
            if not error:
                if self.to_add or self.to_remove or self.to_load:
                    self.mainApp._cancelButton.set_visible(True)
                    self.updateGtk()
                    trans_flags = {'cascade': cascade, 'recurse': recurse}
                    error += self.init_transaction(**trans_flags)
                    if not error:
                        for name in self.to_add:
                            error += self.add(name)
                        for name in self.to_remove:
                            error += self.remove(name)
                        for path in self.to_load:
                            error += self.load(path)
                        if not error:
                            error += self.prepare(trans_flags)
                if not error:
                    self.set_transaction_sum()
                    self.mainApp._confDialog.show_all()
                    self.updateGtk()
                    sleep(0.4)
            if error:
                self.release()
                return(error)
        else:
            return (_('Nothing to do'))

    def check_finished_build(self, data):
        def handle_timeout(*args):
            raise Exception('timeout')
        def no_handle_timeout(*args):
            try:
                pass
            except:
                pass
        path = data[0]
        pkg = data[1]
        if self.build_proc.poll() is None:
            # Build no finished : read stdout to push it to text_buffer
            # add a timeout to stop reading stdout if too long
            # so the gui won't freeze
            signal.signal(signal.SIGALRM, handle_timeout)
            signal.setitimer(signal.ITIMER_REAL, 0.05) # 50 ms timeout
            try:
                line = self.build_proc.stdout.readline().decode(encoding='UTF-8')
                line = re.sub(self.colors_regexp, '', line)
                #print(line.rstrip('\n'))
                self._terminalTextBuffer.insert_at_cursor(line)
            except Exception:
                pass
            else:
                signal.signal(signal.SIGALRM, no_handle_timeout)
            finally:
                self.mainApp._progressBar.pulse()
                self.updateGtk()
                return True
        elif self.build_proc.poll() == 0:
            # Build successfully finished
            built = []
            # parse again PKGBUILD to have new pkg objects in case of a pkgver() function
            # was used so pkgver was changed during build process
            new_pkgs = aur.get_pkgs(path + '/PKGBUILD')
            # find built packages
            for new_pkg in new_pkgs:
                for item in os.listdir(path):
                    if os.path.isfile(os.path.join(path, item)):
                        # add a * before pkgver if there an epoch variable
                        if fnmatch.fnmatch(item, '{}-*{}-*.pkg.tar.?z'.format(new_pkg.name, new_pkg.version)):
                            built.append(os.path.join(path, item))
                            break
            if built:
                print('successfully built:', built)
                self.build_proc = None
                if pkg in self.to_build:
                    self.to_build.remove(pkg)
                # install built packages
                error = ''
                error += self.init_transaction()
                if not error:
                    for pkg_path in built:
                        error += self.load(pkg_path)
                    if not error:
                        error += self.prepare()
                        if not error:
                            if self.to_Remove():
                                self.set_transaction_sum()
                                self.mainApp._confDialog.show_all()
                                self.updateGtk()
                            else:
                                print("yo te llame")
                                self.finalize()
                    if error:
                        self.release()
                        self.mainApp._cancelButton.set_visible(False)
                        self.mainApp._closeButton.set_visible(True)
                        self.log_error(error)
            else:
                self.mainApp._cancelButton.set_visible(False)
                self.mainApp._closeButton.set_visible(True)
                self.action_long_handler(None, _('Build process failed.'))
            return False
        elif self.build_proc.poll() == 1:
            # Build finish with an error
            self.mainApp._cancelButton.set_visible(False)
            self.mainApp._closeButton.set_visible(True)
            self.action_long_handler(None, _('Build process failed.'))
            return False

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
            self.mainApp._mainWindow .show()
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

    def build_next(self):
        pkg = self.to_build[0]
        path = os.path.join(aur.srcpkgdir, pkg.name)
        new_pkgs = aur.get_pkgs(path + '/PKGBUILD')
        # sources are identicals for splitted packages
        # (not complete) download(new_pkgs[0].source, path)
        action = _('Building {pkgname}').format(pkgname = pkg.name)+'...'
        self.action_handler(action)
        self.action_long_handler(None, action+'\n')
        self.icon_handler(None, 'cinnamon-installer-setup')
        self.target_handler(None, '')
        self.percent_handler(None, 0)
        self.mainApp._cancelButton.set_visible(True)
        self.mainApp._closeButton.set_visible(False)
        self.mainApp._terminalExpander.set_visible(True)
        self.mainApp._terminalExpander.set_expanded(True)
        self.mainApp._mainWindow.show()
        self.build_proc = subprocess.Popen(["makepkg", "-cf"], cwd = path, stdout = subprocess.PIPE, stderr=subprocess.STDOUT)
        self.updateGtk()
        GObject.idle_add(self.check_finished_build, (path, pkg))
        sleep(0.1)

    def finalize(self):
        if self.to_Add() or self.to_Remove():
            try:
                self.commit()
            except Exception as e:
                print(e)
                self.release()
        elif self.to_build:
            # packages in to_build have no deps or makedeps 
            # so we build and install the first one
            # the next ones will be built by the caller
            self.build_next()

    def mark_needed_pkgs_as_dep(self):
        for name in self.to_mark_as_dep.copy():
            if self.get_localpkg(name):
                error = self.setPkgReason(name, executer.pyalpm.PKG_REASON_DEPEND)
                if error:
                    print(error)
                else:
                    self.to_mark_as_dep.discard(name)

    def get_updates(self):
      try:
        self.updateGtk()
        self.action_handler(None, _('Checking for updates')+'...')
        self.icon_handler(None, 'cinnamon-installer-search')
        self.target_handler(None, '')
        self.percent_handler(None, 0)
        self.mainApp._cancelButton.set_visible(False)
        self.mainApp._closeButton.set_visible(False)
        self.mainApp._terminalExpander.set_visible(False)
        self.mainApp._mainWindow.show_all()
        self.updateGtk()
        self.checkUpdates()
      except Exception as e:
        print(e)

    def get_transaction_sum(self):
        transaction_dict = {'to_remove': [], 'to_build': [], 'to_install': [], 'to_update': [], 'to_reinstall': [], 'to_downgrade': []}
        for pkg in self.to_build:
            transaction_dict['to_build'].append(pkg.name+' '+pkg.version)
        _to_remove = sorted(self.to_Remove())
        for name, version in _to_remove:
            transaction_dict['to_remove'].append(name+' '+version)
        others = sorted(self.to_Add())
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
        #~ if transaction_dict['to_build']:
            #~ print('To build:', [name for name in transaction_dict['to_build']])
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
        if transaction_dict['to_build']:
            self.mainApp._transactionSum.append([_('To build')+':', transaction_dict['to_build'][0]])
            i = 1
            while i < len(transaction_dict['to_build']):
                self.mainApp._transactionSum.append(['', transaction_dict['to_build'][i]])
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
            self.mainApp._sumBottomLabel.set_markup('<b>{} {}</b>'.format(_('Total download size:'), common.format_size(dsize)))
