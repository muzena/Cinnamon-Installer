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

import pyalpm, os, subprocess, sys, stat
from time import sleep

# uncomment to use GTK 2.0
#import gi
#gi.require_version('Gtk', '2.0')

from gi.repository import GObject, Gtk

MODULES = 'lib'
ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"
sys.path.append(DIR_PATH + MODULES)

import config, common, transaction, aur

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


def configure():
    st = os.stat(DIR_PATH + "/tools/configure.py")
    os.chmod(DIR_PATH + "/tools/configure.py", st.st_mode | stat.S_IEXEC)
    if ((not os.path.isfile("/usr/share/polkit-1/actions/org.cinnamon.installer.policy")) or
        (not os.path.isfile("/usr/sbin/cinnamon-installer"))):
        process = subprocess.Popen("pkexec '"+ DIR_PATH + "tools/configure.py'", shell=True, stdout=subprocess.PIPE)
        process.wait()
        sleep(1.2)
        return (process.returncode == 0)
    return True

def reloadAsRoot(options):
    if(configure()):
        pathRealod = "/usr/sbin/cinnamon-installer"
        pathCallBack = os.path.dirname(os.path.dirname(DIR_PATH)) + "/Cinnamon-Installer.py"
        subprocess.call(["pkexec", pathRealod, pathCallBack] + options)
        #os.execvp('pkexec', ['pkexec', pathRealod, options])
        return True
    return False

def findPackageByPath(path):
    '''Return the package that ships the given file.
    Return None if no package ships it.
    '''
    if path is not None:
        # resolve symlinks in directories
        (dir, name) = os.path.split(path)
        resolved_dir = os.path.realpath(dir)
        if os.path.isdir(resolved_dir):
            file = os.path.join(resolved_dir, name)

        if not likely_packaged(path):
            return None
        return get_file_package(path)
    return None

def likely_packaged(file):
    '''Check whether the given file is likely to belong to a package.'''
    pkg_whitelist = ['/bin/', '/boot', '/etc/', '/initrd', '/lib', '/sbin/',
                     '/opt', '/usr/', '/var']  # packages only ship executables in these directories

    whitelist_match = False
    for i in pkg_whitelist:
        if file.startswith(i):
            whitelist_match = True
            break
    return whitelist_match and not file.startswith('/usr/local/') and not \
        file.startswith('/var/lib/')

def get_file_package(file):
    '''Return the package a file belongs to.
    Return None if the file is not shipped by any package.
    '''
    # check if the file is a diversion
    dpkg = subprocess.Popen(['pacman', '-Qo', file],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = dpkg.communicate()[0].decode('UTF-8')
    if dpkg.returncode == 0 and out:
        outList = out.split()
        pkg = outList[-2]# + "-" +outList[-1]
        return pkg

    fname = os.path.splitext(os.path.basename(file))[0].lower()

    all_lists = []
    likely_lists = []
    for f in glob.glob('/var/lib/dpkg/info/*.list'):
        p = os.path.splitext(os.path.basename(f))[0].lower().split(':')[0]
        if p in fname or fname in p:
            likely_lists.append(f)
        else:
            all_lists.append(f)

    # first check the likely packages
    match = __fgrep_files(file, likely_lists)
    if not match:
        match = __fgrep_files(file, all_lists)

    if match:
        return os.path.splitext(os.path.basename(match))[0].split(':')[0]

    return None

def __fgrep_files(pattern, file_list):
    '''Call fgrep for a pattern on given file list and return the first
    matching file, or None if no file matches.'''

    match = None
    slice_size = 100
    i = 0

    while not match and i < len(file_list):
        p = subprocess.Popen(['fgrep', '-lxm', '1', '--', pattern] +
                             file_list[i:(i + slice_size)], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.communicate()[0].decode('UTF-8')
        if p.returncode == 0:
            match = out
        i += slice_size

    return match

def searchUnistalledPackages(pattern):
    try:
        handle = config.handle()
        syncdbs = handle.get_syncdbs()
        localdb = handle.get_localdb()
        unInstalledPackages = []
        names_list = []
        for repo in syncdbs:
            for pkg in repo.pkgcache:
                if((pattern in pkg.name) and (not pkg.name in names_list)):
                    names_list.append(pkg.name)
                    if not localdb.get_pkg(pkg.name):
                        unInstalledPackages.append(pkg)
    except Exception as e:
        print(e)
    return unInstalledPackages

def packageExistArch(pkgName, cache):
    lenght = len(pkgName)
    if pkgName[lenght-5:lenght] == ":i386":
        try:
            pkg = cache[pkgName[0:lenght-5]]
            if pkg.is_installed:
                #print("Installed: " + pkgName)
                return True
        except Exception:
            return False
    return False

class ControlWindow(object):
    def __init__(self, mainApp):
        self.mainApp = mainApp
        self.packageName = None
        '''
#att requeridos
        self.debconf = True
        self.show_terminal = True
        self._expanded_size = None
        self._transaction = None
#att requeridos
        interface = self.mainApp.interface
        self.mainWindow = (interface.get_object("Installer"))
        self.progressBar = interface.get_object("progressBar")
        self.expander = interface.get_object("terminalExpander")
        self.labelRole = interface.get_object("roleLabel")
        self.labelStatus = interface.get_object("statusLabel")
        self.cancelButton = interface.get_object("cancelButton")
        self._signals = []

        self.labelStatus.set_ellipsize(Pango.EllipsizeMode.END)
        self.labelStatus.set_max_width_chars(15)
        self._signalsLabelStatus = []

        self.cancelButton.set_use_stock(True)
        self.cancelButton.set_label(Gtk.STOCK_CANCEL)
        self.cancelButton.set_sensitive(True)
        self._signalsCancelButton = []

        self.progressBar.set_ellipsize(Pango.EllipsizeMode.END)
        self.progressBar.set_text(" ")
        self.progressBar.set_pulse_step(0.05)
        self._signalsProgressBar = []

        self.expander.set_sensitive(False)
        self.expander.set_expanded(False)
        #if self.show_terminal:
        #    self.terminal = AptTerminal()
        #else:
        #    self.terminal = None
        #self.download_view = AptDownloadsView()
        self.download_scrolled = Gtk.ScrolledWindow()
        self.download_scrolled.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.download_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        #self.download_scrolled.add(self.download_view)
        hbox = Gtk.HBox()
        hbox.pack_start(self.download_scrolled, True, True, 0)
        #if self.terminal:
        #    hbox.pack_start(self.terminal, True, True, 0)
        self.expander.add(hbox)
        self.expander.connect("notify::expanded", self._on_expanded)
        
        #self.set_title("")
        self.progressBar.set_size_request(350, -1)

        self._signalsExpander = []

        #self.terminal.hide()
        '''
        self.trans = transaction.Transaction(self.mainApp)
        '''Begin Manjaro'''

        self.signals = {'on_ChooseButton_clicked' : self.trans.on_ChooseButton_clicked,
                        'on_progress_textview_size_allocate' : self.trans.on_progress_textview_size_allocate,
                        'on_choose_renderertoggle_toggled'   : self.trans.on_choose_renderertoggle_toggled,
                        'on_PreferencesCloseButton_clicked'  : self.trans.on_PreferencesCloseButton_clicked,
                        'on_PreferencesWindow_delete_event'  : self.trans.on_PreferencesWindow_delete_event,
                        'on_PreferencesValidButton_clicked'  : self.trans.on_PreferencesValidButton_clicked,
                        'on_TransValidButton_clicked'    : self.on_TransValidButton_clicked,
                        'on_TransCancelButton_clicked'   : self.on_TransCancelButton_clicked,
                        'on_ProgressCloseButton_clicked' : self.on_ProgressCloseButton_clicked,
                        'on_ProgressCancelButton_clicked': self.on_ProgressCancelButton_clicked}

    def preformUninstall(self, packageName):
        if (os.geteuid() != 0):
            if (not reloadAsRoot(["--upackage", packageName])):
                print("fail on install:" + str(packageName))
            else:
                print("reload as root")
        else:
            print("uninstall: " + str(packageName))
            self.trans.mainApp._roleLabel.set_text("Uninstall: " + str(packageName))
            self.trans.mainApp.interface.connect_signals(self.signals)
            self.trans.config_signals()
            self.config_signals()
            self.transaction_done = False
            self.trans.get_handle()
            result = []
            self.mainApp._mainWindow.show_all()
            self.uninstall([packageName])
            #self.trans.get_updates()
            Gtk.main()

    def preformInstall(self, packageName):
        if (os.geteuid() != 0):
            if (not reloadAsRoot(["--ipackage", packageName])):
                print("fail on install:" + str(packageName))
            else:
                print("reload as root")
        else:
            print("install:" + str(packageName))
            self.trans.mainApp._roleLabel.set_text("Install: " + str(packageName))
            self.trans.mainApp.interface.connect_signals(self.signals)
            self.trans.config_signals()
            self.config_signals()
            self.transaction_done = False
            self.trans.get_handle()
            result = []
            self.mainApp._mainWindow.show_all()
            self.install([packageName])
            #self.trans.get_updates()
            Gtk.main()

    def _on_expanded(self, expander, param):
        # Make the dialog resizable if the expander is expanded
        # try to restore a previous size
        if not expander.get_expanded():
            self._expanded_size = (self.terminal.get_visible(),
                                   self.mainWindow.get_size())
            self.mainWindow.set_resizable(False)
        elif self._expanded_size:
            self.mainWindow.set_resizable(True)
            term_visible, (stored_width, stored_height) = self._expanded_size
            # Check if the stored size was for the download details or
            # the terminal widget
            if term_visible != self.terminal.get_visible():
                # The stored size was for the download details, so we need
                # get a new size for the terminal widget
                self._resize_to_show_details()
            else:
                self.mainWindow.resize(stored_width, stored_height)
        else:
            self.mainWindow.set_resizable(True)
            self._resize_to_show_details()

    def _resize_to_show_details(self):
        win_width, win_height = self.mainWindow.get_size()
        exp_width = self.expander.get_allocation().width
        exp_height = self.expander.get_allocation().height
        if self.terminal and self.terminal.get_visible():
            terminal_width = self.terminal.get_char_width() * 80
            terminal_height = self.terminal.get_char_height() * 24
            self.mainWindow.resize(terminal_width - exp_width ,
                               terminal_height - exp_height )
        else:
            print(str(win_height))
            self.mainWindow.resize(win_width + 100, win_height)

    def _on_status_changed(self, trans, status):
        # Also resize the window if we switch from download details to
        # the terminal window
        print(status)
        #if (status == STATUS_COMMITTING and self.terminal and 
        #        self.terminal.get_visible()):
        #    self._resize_to_show_details()

    '''Begin Manjaro'''

    def exiting(self, msg):
        self.trans.stopDaemon()
        print(msg)
        Gtk.main_quit()

    def handle_error(self, obj, error):
        GObject.idle_add(self.show_Error, (error))
        sleep(0.1)

    def handle_reply(self, obj, replay):
        GObject.idle_add(self.exec_replay, (replay,))
        sleep(0.1)

    def handle_updates(self, obj, syncfirst, updates):
        GObject.idle_add(self.exec_update, (syncfirst, updates,))
        sleep(0.1)

    def show_Error(self, error):
        self.trans.mainApp._mainWindow.hide()
        self.updateGtk()
        if error:
            self.trans.mainApp._errorDialog.format_secondary_text(error)
            response = self.trans.mainApp._errorDialog.run()
            if response:
                self.trans.mainApp._errorDialog.hide()
        self.exiting(error)

    def exec_replay(self, reply):
        self.trans.mainApp._closeButton.set_visible(True)
        self.trans.mainApp._actionImage.set_from_icon_name('dialog-information', Gtk.IconSize.BUTTON)
        self.trans.mainApp._roleLabel.set_text(str(reply))
        self.trans.mainApp._statusLabel.set_text(str(reply))
        self.trans.mainApp._progressBar.set_text('')
        end_iter = self.trans._terminalTextBuffer.get_end_iter()
        self.trans._terminalTextBuffer.insert(end_iter, str(reply))
        self.updateGtk()

    def exec_update(self, syncfirst=True, updates=None):
        #syncfirst, updates = update_data
        if self.transaction_done:
            self.exiting('')
        elif updates:
            self.trans.mainApp._errorDialog.format_secondary_text(_('Some updates are available.\nPlease update your system first'))
            response = self.trans.mainApp._errorDialog.run()
            if response:
                self.trans.mainApp._errorDialog.hide()
                self.exiting('')
        else:
            pkgs_to_install = ["hddtemp"]
            self.install(pkgs_to_install)

    def on_TransValidButton_clicked(self, *args):
        GObject.idle_add(self.exec_Transaction)
        sleep(0.1)

    def exec_Transaction(self):
        self.trans.mainApp._confDialog.hide()
        self.updateGtk()
        self.trans.finalize()
        self.updateGtk()
        if not self.trans.details:
           self.trans.release()
           self.exiting('')

    def on_TransCancelButton_clicked(self, *args):
        self.trans.mainApp._confDialog.hide()
        self.updateGtk()
        self.trans.release()
        self.exiting('')

    def on_ProgressCloseButton_clicked(self, *args):
        self.trans.mainApp._mainWindow.hide()
        self.updateGtk()
        self.transaction_done = True
        self.trans.checkUpdates()

    def on_ProgressCancelButton_clicked(self, *args):
        self.trans.interrupt()
        self.trans.mainApp._mainWindow.hide()
        self.updateGtk()
        self.exiting('')

    def get_pkgs(self, pkgs):
        error = ''
        for name in pkgs:
            if '.pkg.tar.' in name:
                full_path = abspath(name)
                self.trans.to_load.add(full_path)
            elif self.trans.get_syncpkg(name):
                self.trans.to_add.add(name)
            else:
                aur_pkg = None
                if config.enable_aur:
                    aur_pkg = aur.info(name)
                    if aur_pkg:
                        self.trans.to_build.append(aur_pkg)
                if not aur_pkg:
                    if error:
                        error += '\n'
                        error += _('{pkgname} is not a valid path or package name').format(pkgname = name)
        if error:
            self.handle_error(None, error)
            return False
        elif ((len(self.trans.to_add) > 0) or (len(self.trans.to_load) > 0) or (len(self.trans.to_build) > 0)):
            return True
        error = _('{pkgname} is not a valid path or package name').format(pkgname = name)
        self.handle_error(None, error)
        return False

    def get_pkgs_uninstall(self, pkgs):
        liststore = Gtk.ListStore(object)
        for name in pkgs:
            if self.trans.get_localpkg(name):
                self.trans.to_remove.add(name)
        if len(self.trans.to_remove) > 0:
            return True
        error = _('{pkgname} is not a valid path or package name').format(pkgname = name)
        self.handle_error(None, error)
        return False

    def install(self, pkgs):
        if self.get_pkgs(pkgs):
            self.trans.action_handler(None, _('Preparing')+'...')
            self.trans.icon_handler(None, 'package-setup.png')
            self.updateGtk()
            #common.write_pid_file()
            error = self.trans.run()
            self.updateGtk()
            if error:
                self.handle_error(None, error)

    def uninstall(self, pkgs):
        if self.get_pkgs_uninstall(pkgs):
            self.trans.action_handler(None, _('Preparing')+'...')
            self.trans.icon_handler(None, 'package-setup.png')
            self.updateGtk()
            #common.write_pid_file()
            error = self.trans.run()
            self.updateGtk()
            if error:
                self.handle_error(None, error)


    def config_signals(self):
        self.trans.service.connect("EmitTransactionDone", self.handle_reply)
        self.trans.service.connect("EmitTransactionError", self.handle_error)
        self.trans.service.connect("EmitAvailableUpdates", self.handle_updates)

    def updateGtk(self):
        while Gtk.events_pending():
            Gtk.main_iteration()

