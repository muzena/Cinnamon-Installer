#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#
# Authors: Lester Carballo Pérez <lestcape@gmail.com>
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
    import sys, py_compile, os, shutil, stat
    from distutils.core import setup
    from distutils import cmd
    from distutils.command.install_data import install_data as _install_data
    from distutils.command.build import build as _build
except Exception:
    e = sys.exc_info()[1]
    print(str(e))
    sys.exit(1)

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(os.path.dirname(ABS_PATH)) + "/"

INSTALL_PATH = "/usr/lib/cinnamon-installer/"
LOCAL_PATH = os.path.expanduser("~") + "/.local/share/Cinnamon-Installer/"

POLKIT_PATH = "/usr/share/polkit-1/actions/"
SCHEMAS_PATH = "/usr/share/glib-2.0/schemas/"
CROND_PATH = "/etc/cron.daily/"

try:
    import msgfmt.make
except Exception:
    def make(src, dest):
        if src.filename[:3] == 'po/':
            parts = os.path.splitext(src.filename)
            if parts[1] == '.po':
                this_locale_dir = os.path.join(dest, parts[0][3:], 'LC_MESSAGES')
                rec_mkdir(this_locale_dir)
                subprocess.call(["msgfmt", "-c", os.path.join(dirname, src.filename), "-o", os.path.join(this_locale_dir, '%s.mo' % uuid)])
        
#os.chmod(out, 0644)

def reloadAsRoot(options):
    os.execvp('pkexec', ['pkexec', ABS_PATH, options])
    print("reload as root")

def copyTree(src, out):
    source = os.listdir(src)
    for filename in source:
        srcfile = os.path.join(src, filename)
        outfile = os.path.join(out, filename)
        if os.path.isfile(srcfile):
            shutil.copy(srcfile, out)
            print("copy " + srcfile)
        else:
            if not os.path.exists(outfile):
                os.makedirs(outfile)
            copyTree(srcfile, outfile)

def setPermisions():
    tragetFile = os.path.join(INSTALL_PATH, "Cinnamon-Installer.py")
    st = os.stat(tragetFile)
    os.chmod(tragetFile, st.st_mode | stat.S_IEXEC)
    tragetTools = os.path.join(INSTALL_PATH, "tools")
    source = os.listdir(tragetTools)
    for filename in source:
        tragetFile = os.path.join(tragetTools, filename)
        st = os.stat(tragetFile)
        os.chmod(tragetFile, st.st_mode | stat.S_IEXEC)

def compilePy(folderModules):
    traget = os.path.join(INSTALL_PATH, folderModules)
    source = os.listdir(traget)
    for filename in source:
        lastPos = len(filename)
        if (filename[lastPos-3:lastPos] == ".py") and (filename[0:3] == "ci_"):
            tragetFile = os.path.join(traget, filename)
            py_compile.compile(tragetFile)

def installPolicy():
    traget = os.path.join(DIR_PATH, "config/policy")
    source = os.listdir(traget)
    for filename in source:
        srcFile = os.path.join(traget, filename)
        outFile = os.path.join(POLKIT_PATH, filename)
        shutil.copyfile(srcFile, outFile)

def installSchema():
    traget = os.path.join(DIR_PATH, "config/schemas")
    source = os.listdir(traget)
    for filename in source:
        srcFile = os.path.join(traget, filename)
        outFile = os.path.join(SCHEMAS_PATH, filename)
        shutil.copyfile(srcFile, outFile)
        os.system("glib-compile-schemas " + SCHEMAS_PATH)

def installCronD():
    srcFile = os.path.join(DIR_PATH, "tools/cinnamon-installer")
    outFile = os.path.join(CROND_PATH, "cinnamon-installer")
    shutil.copyfile(srcFile, outFile)
    st = os.stat(srcFile)
    os.chmod(outFile, st.st_mode | stat.S_IEXEC)

def installLocale():
    po_dir = os.path.join(DIR_PATH, 'po')
    for path, names, filenames in os.walk(po_dir):
        for f in filenames:
            if f.endswith('.po'):
                lang = f[:-3]
                src = os.path.join(path, f)
                dest_path = os.path.join(DIR_PATH, "locale", lang, "LC_MESSAGES")
                dest = os.path.join(dest_path, 'cinnamon-installer.mo')
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)
                if not os.path.exists(dest):
                    print("Compiling %s" % src)
                    make(src, dest)
                else:
                    src_mtime = os.stat(src)[8]
                    dest_mtime = os.stat(dest)[8]
                    if src_mtime > dest_mtime:
                        print("Compiling %s" % src)
                        make(src, dest)

if __name__ == "__main__":
    INSTALL_PATHER = LOCAL_PATH
    if (len(sys.argv) > 1) and (sys.argv[1] == "-i") and (os.geteuid() != 0):
        reloadAsRoot("-i")
    else:
        copyTree(DIR_PATH, INSTALL_PATH)
        setPermisions()
        compilePy("settings_modules")
        compilePy("installer_modules")
        if (len(sys.argv) > 1) and (sys.argv[1] == "-i"):
            installPolicy()
            installSchema()
            installCronD()
