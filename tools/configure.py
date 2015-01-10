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

import os, argparse, sys, gettext, locale, shutil, stat

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(os.path.dirname(ABS_PATH)) + "/"

importerError = []

def checkInstall():
    pathSysPolicy = "/usr/share/polkit-1/actions/org.cinnamon.installer.policy"
    if not os.path.isfile(pathSysPolicy):
        pathPolicy = DIR_PATH + "config/policy/org.cinnamon.installer.policy"
        #os.system("cp %s %s" % (pathPolicy, pathSysPolicy))
        shutil.copyfile(pathPolicy, pathSysPolicy)

    pathSysInit = "/usr/sbin/cinnamon-installer"
    if not os.path.isfile(pathSysInit):
        generateInitFile(pathSysInit)
        st = os.stat(pathSysInit)
        os.chmod(pathSysInit, st.st_mode | stat.S_IEXEC)

    pathSysSchema = "/usr/share/glib-2.0/schemas/org.cinnamon.installer.xml"
    if not os.path.isfile(pathSysSchema):
        pathSchema = DIR_PATH + "config/schemas/org.cinnamon.installer.xml"
        shutil.copyfile(pathSchema, pathSysSchema)
        #os.system("cp %s %s" % (pathSchema, pathSysSchema))
        os.system("glib-compile-schemas /usr/share/glib-2.0/schemas/")
    print("install")

def generateInitFile(fileName):
    f = open(fileName, "a")
    f.write("#!/usr/bin/python3\n")
    f.write("# -*- coding:utf-8 -*-\n\n")
    f.write("import os, sys\n\n")
    f.write("os.execvp(\"sudo\", (\"python3\", sys.argv[1],) + tuple(sys.argv[2:]))")
    f.close()

if __name__ == "__main__":
    checkInstall()
