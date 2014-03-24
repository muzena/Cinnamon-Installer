#!/usr/bin/env python
# -*- coding:utf-8 -*-

import urllib2, sys, os, shutil, tarfile, argparse, stat
from threading import Thread
from gi.repository import Gtk, Gdk, GObject, GLib, Pango

'''Important Constants'''
PROGRAM_NAME = "Cinnamon-Installer"
SELF_NAME = "Updater"
VERSION_FILE = "ver"
EXTENSION = ".tar.gz"

VERSION_URL = "https://raw.githubusercontent.com/lestcape/Cinnamon-Installer/master/ver"
WEB_SITE_URL = "https://github.com/lestcape/Cinnamon-Installer"
LAST_VERSION_URL = "https://github.com/lestcape/Cinnamon-Installer/archive/"
TEMP = "/tmp/"
ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH) + "/"
INSTALL_DIR = os.path.expanduser("~") + "/.local/share/" + PROGRAM_NAME + "/"

class MainApp():
    """Graphical updater for update Cinnamon Installer directly from github"""

    def __init__(self, currentVersion, fileD):
        self.currentVersion = currentVersion
        print "Current version: " + self.currentVersion
        self._fileD = fileD
        self.interface = Gtk.Builder()
        self.interface.set_translation_domain(PROGRAM_NAME)
        self.interface.add_from_file(DIR_PATH + '/gui/mainUpdater.ui')
        self._mainWindow = self.interface.get_object('mainWindow')
        self._appNameLabel = self.interface.get_object('appNameLabel')
        self._statusLabel = self.interface.get_object('statusLabel')
        self.progressBar = self.interface.get_object('progressBar')
        self._mainWindow.connect("destroy", self.closeWindows)
        self.loop = GObject.MainLoop()
        self.newVersion = None

    def show(self):
        self._mainWindow.show_all()
        self._mainWindow.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))
        self.refresh()

    def tryUpdaterGUI(self):
        # question dialog
        self._statusLabel.set_text("Starting")
        question_title = "Do you like to install Cinnamon Installer?"
        if float(self.currentVersion) > 0.0:
            question_title = "Do you like to update Cinnamon Installer?"
        question_description = "This is a requiere tools for install package on " + \
                               "<i>Configurable Menu</i>. \n" + \
                               "Note that your linux distribution can not be supported.\n" + \
                               "If you wish to contribute, please visit: " + \
                               "<a href='" + WEB_SITE_URL + "'>" + \
                               "Cinnamon Installer</a>."
        response = self._question_dialog(question_title, question_description)
        if response == Gtk.ResponseType.YES:
           result = []
           self.show()
           print "running GUI"
           thread = Thread(target = self._checkNewVersionGUI, args=(result,))
           thread.start()
           self.loop.run()
           self._handdledErrors(result)
        print "stop"

    def forceUpdaterGUI(self):
        self._statusLabel.set_text("Starting")
        result = []
        self.show()
        self._fileD.readFile(VERSION_URL, self.chunk_report, VERSION_FILE)
        self._isUpdateNeeded()
        thread = Thread(target = self._performUpdaterGUI, args=(result,))
        thread.start()
        self.loop.run()
        self._handdledErrors(result)

    def uninstallGUI(self):
        self._statusLabel.set_text("Starting")
        self.progressBar.set_fraction(10)
        result = []
        self.show()
        thread = Thread(target = self._performUninstall, args=(result,))
        thread.start()
        self.loop.run()

    def _checkNewVersionGUI(self, outList):
        self._statusLabel.set_text("Checking for a new version")
        try:
            self._fileD.readFile(VERSION_URL, self.chunk_report, VERSION_FILE)
            if self._isUpdateNeeded():
                self._performUpdaterGUI(outList)
            else:
                outList.append(-1)
            
        except urllib2.URLError:
            outList.append(1)
        except IOError:
            outList.append(2) 
            print "Fail to download"
        self.closeWindows(None) 

    def _performUpdaterGUI(self, outList):
       try:
           self.progressBar.set_fraction(0)
           urlD = LAST_VERSION_URL + self.newVersion + EXTENSION
           self._fileD.readFile(urlD, self.chunk_report, "out" + EXTENSION)
           self.installNewVersion()
           self.setPermissionToExecute()
           outList.append(0)
       except urllib2.URLError:
           outList.append(1)
       except IOError:
           outList.append(2)
       self.closeWindows(None)

    def _performUninstall(self, outList):
        self.progressBar.set_fraction(50)
        if os.path.exists(INSTALL_DIR):
            shutil.rmtree(INSTALL_DIR, onerror=self._del_rw)
        outList.append(0)
        self.progressBar.set_fraction(80)
        self.closeWindows(None)

    def installNewVersion(self):
        self.progressBar.set_fraction(0)
        self._statusLabel.set_text("Installing new version")
        if os.path.exists(INSTALL_DIR):
            shutil.rmtree(INSTALL_DIR, onerror=self._del_rw)
        if os.path.exists(INSTALL_DIR):
            return False
        print "Old Version Removed"
        if os.path.exists(TEMP + PROGRAM_NAME + "-" + self.newVersion):
            shutil.rmtree(TEMP + PROGRAM_NAME + "-" + self.newVersion, onerror=self._del_rw)
        self.progressBar.set_fraction(0.2)
        tar = tarfile.open(TEMP + self._fileD.fileName)
        tar.extractall(TEMP)
        tar.close()
        self.progressBar.set_fraction(0.3)
        print "Uncompress " + TEMP + PROGRAM_NAME + "-" + self.newVersion
        root_src_dir = TEMP + PROGRAM_NAME + "-" + self.newVersion
        root_target_dir = INSTALL_DIR
        for src_dir, dirs, files in os.walk(root_src_dir):
            dst_dir = src_dir.replace(root_src_dir, root_target_dir)
            print "create:" + dst_dir
            if not os.path.exists(dst_dir):
                os.mkdir(dst_dir)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    os.remove(dst_file)
                shutil.move(src_file, dst_dir)
        self.progressBar.set_fraction(0.6)
        if os.path.exists(TEMP + self._fileD.fileName):
            os.remove(TEMP + self._fileD.fileName)
        if os.path.exists(TEMP + PROGRAM_NAME + "-" + self.newVersion):
            shutil.rmtree(TEMP + PROGRAM_NAME + "-" + self.newVersion, onerror=self._del_rw)
        self.progressBar.set_fraction(0.8)
        print "New Version Installed"
        return True

    def setPermissionToExecute(self):
        self.progressBar.set_fraction(1)
        self._statusLabel.set_text("Finalized and validated")
        stO = os.stat(INSTALL_DIR + PROGRAM_NAME + ".py")
        stS = os.stat(INSTALL_DIR + SELF_NAME + ".py")
        os.chmod(INSTALL_DIR + PROGRAM_NAME + ".py", stO.st_mode | stat.S_IEXEC)
        os.chmod(INSTALL_DIR + SELF_NAME + ".py", stS.st_mode | stat.S_IEXEC)
        print "Set Permission to Execute : " + INSTALL_DIR + PROGRAM_NAME
        print "Set Permission to Execute : " + INSTALL_DIR + SELF_NAME

    def _del_rw(self):
        print "Error on dir removed"

    def _handdledErrors(self, result):
        if result[0] == 0:
            print "All finished with good result"
        if result[0] == 1:
            self._statusLabel.set_text("Found errors")
            title = "Can not be perform the installation."
            message = "Appear that you don't have internet connection...\n" + \
                      "Please try later." 
            self._custom_dialog(Gtk.MessageType.ERROR, title, message)
        elif result[0] == 2:
            self._statusLabel.set_text("Found errors")
            title = "Can not be perform the installation."
            message = "Appear that you don't have permission to write files on " + TEMP + "\n"\
                      "Please try later." 
            self._custom_dialog(Gtk.MessageType.ERROR, title, message)
        elif result[0] == -1:
            self._statusLabel.set_text("Not necessary update")
            question_title = "You have the latest version of the product..."
            question_description = "Do you want a reinstallation anyway?"
            response = self._question_dialog(question_title, question_description)
            if response == Gtk.ResponseType.YES:
                self.forceUpdaterGUI()

    def _on_clicked_cancelButton(self, button, transaction):
        self._fileD.cancel()
        self.loop.quit()

    def closeWindows(self, windows):
        self.loop.quit()

    def refresh(self, force_update = False):
	while Gtk.events_pending():
	    Gtk.main_iteration()
	while Gtk.events_pending():
	    Gtk.main_iteration()
	#Refresh(force_update)

    def chunk_report(self, bytes_so_far, total_size):
        percent = float(bytes_so_far) / total_size
        percent = round(percent*100, 2)
        if total_size != -1:
            if percent > 100:
                self.progressBar.pulse()
            else:
                self.progressBar.set_fraction(percent / 100.0)
            sys.stdout.write("Downloaded %d of %d bytes (%0.2f%%)\r" % 
                (bytes_so_far, total_size, percent))
        else:
            self.progressBar.pulse()
            sys.stdout.write("Downloaded %d of %s bytes (%s)%%\r" % 
                (bytes_so_far, "Unknow", "Unknow"))

        if bytes_so_far >= total_size:
            sys.stdout.write('\n')

    def _isUpdateNeeded(self):
        self.newVersion = self.readVersionFromFile(TEMP + VERSION_FILE)
        self._fileD.deleteFile(TEMP + VERSION_FILE)
        print self.newVersion
        if float(self.newVersion) > float(self.currentVersion):
            return True
        return False

    def _custom_dialog(self, dialog_type, title, message):
        '''
        This is a generic Gtk Message Dialog function.
        dialog_type = this is a Gtk type.
        '''
        dialog = Gtk.MessageDialog(self._mainWindow, 0, dialog_type,
            Gtk.ButtonsType.OK, "")
        dialog.set_markup("<b>%s</b>" % title)
        dialog.format_secondary_markup(message)
        dialog.run()
        dialog.destroy()

    def _question_dialog(self, title, message):
        '''
        This is a generic Gtk Message Dialog function
        for questions.
        '''
        dialog = Gtk.MessageDialog(self._mainWindow, 0, Gtk.MessageType.QUESTION,
            Gtk.ButtonsType.YES_NO, "")
        dialog.set_markup("<b>%s</b>" % title)
        dialog.format_secondary_markup(message)
        response = dialog.run()
        dialog.destroy()
        return response

    def readVersionFromFile(self, path):
        try:
            if os.path.isfile(path):
                infile = open(path, 'r')
                result = infile.readline().rstrip('\r\n')
                float(result) #Test info
                return result
        except Exception:
            pass
        return "0.0"

class Download():
    def __init__(self):
        self.executeAction = True
        self.fileName = ""
        self.total_size = -1
        self.total_size = -1

    def readFile(self, url, report=None, defaultFileName=""):
        self.fileName = defaultFileName
        response = urllib2.urlopen(url);
        #if report is None:
        #    report = self.chunk_report
        self.initializeRequest(response)
        return self.chunk_read(response, report_hook=report) is not None

    def chunk_report(self, bytes_so_far, total_size):
        percent = float(bytes_so_far) / total_size
        percent = round(percent*100, 2)
        if total_size != -1:
            sys.stdout.write("Downloaded %d of %d bytes (%0.2f%%)\r" % 
                (bytes_so_far, total_size, percent))
        else:
            sys.stdout.write("Downloaded %d of %s bytes (%s)%%\r" % 
                (bytes_so_far, "Unknow", "Unknow"))

        if bytes_so_far >= total_size:
            sys.stdout.write('\n')

    def cancel():
        self.cancelAction = False

    def initializeRequest(self, response):
        self.total_size = -1
        if response.info().has_key('Content-Length'):
            self.total_size = response.info().getheader('Content-Length').strip()
        self.total_size = int(self.total_size)
        self.bytes_so_far = 0
        try:
            if response.info().has_key('Content-Disposition'):
                realFileName = response.info()['Content-Disposition'].split('filename=')[1]
                if realFileName[0] == '"' or realFileName[0] == "'":
                    realFileName = realFileName[1:-1]
                if realFileName is not None:
                    self.fileName = realFileName
        except Exception:
            pass
        self.deleteFile(TEMP + self.fileName)

    def chunk_read(self, response, chunk_size=8192, report_hook=None):
        while self.executeAction:
           chunk = response.read(chunk_size)
           self.bytes_so_far += len(chunk)

           if not chunk:
              break

           self.saveData(chunk)

           if report_hook:
              report_hook(self.bytes_so_far, self.total_size)
        self.executeAction = True
        return self.bytes_so_far

    def saveData(self, data):
        if (len(data) > 0):
            f = open(TEMP + self.fileName, "a")
            for x in data:
                f.write(x)
            f.close()

    def deleteFile(self, path):
        if os.path.isfile(path):
            os.remove(path)
            #print "Clean file:" + path

class Updater:
    def __init__(self):
        self.currentVersion = self.readVersionFromFile(INSTALL_DIR + VERSION_FILE)
        self.newVersion = 0;
        self._fileD = Download()
        #print "Current Version: " + self.currentVersion

    def checkNewVersionGUI(self):
        self.mainW = MainApp(self.currentVersion, self._fileD)
        self.mainW.tryUpdaterGUI();
        self.executeTest()

    def checkNewVersionSilent(self):
        try:
            self._fileD.readFile(VERSION_URL, None, VERSION_FILE)
            if self.isUpdateNeeded():
                print "update"
                print str(self.newVersion)
            else:
                print "ready"
        except Exception:
            print "internet"
            pass

    def forceUpdaterGUI(self):
        self.mainW = MainApp(self.currentVersion, self._fileD)
        self.mainW.forceUpdaterGUI();
        self.executeTest()

    def uninstallGUI(self):
        self.mainW = MainApp(self.currentVersion, self._fileD)
        self.mainW.uninstallGUI();

    def uninstallSilent(self):
        if os.path.exists(INSTALL_DIR):
            shutil.rmtree(INSTALL_DIR, onerror=self._del_rw)

    def executeTest(self):
        os.system(INSTALL_DIR + PROGRAM_NAME + ".py --qtest package")
        print "Run Test Import"

    def isUpdateNeeded(self):
        self.newVersion = self.readVersionFromFile(TEMP + VERSION_FILE)
        self._fileD.deleteFile(TEMP + VERSION_FILE)
        if float(self.newVersion) > float(self.currentVersion):
            return True
        return False

    def readVersionFromFile(self, path):
        try:
            if os.path.isfile(path):
                infile = open(path, 'r')
                result = infile.readline().rstrip('\r\n')
                float(result) #Test info
                return result
        except Exception:
            pass
        return "0.0"

    def _del_rw(self):
        print "Error on dir removed"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process the updater options.')
    group_action = parser.add_mutually_exclusive_group(required=True)
    group_action.add_argument('--qupdate', nargs='?', action='store', type=str, help='Query for update Cinnamon Installer[silent/gui/forced/test]')
    group_action.add_argument('--uninstall', nargs='?', action='store', type=str, help='Uninstall Cinnamon Installer[silent/gui]')
    args = parser.parse_args()

    updater = Updater()
    if args.qupdate:
       if args.qupdate == "silent":
          updater.checkNewVersionSilent()
       elif args.qupdate == "gui":
          updater.checkNewVersionGUI()
       elif args.qupdate == "forced":
          updater.forceUpdaterGUI()
       elif args.qupdate == "test":
          updater.executeTest()
    elif args.uninstall:
       if args.uninstall == "gui":
          updater.uninstallGUI()
       elif args.uninstall == "silent":
          updater.uninstallSilent()
