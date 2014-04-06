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

import os, argparse, sys, gettext, locale, shutil, stat

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(ABS_PATH)

importerError = []

def checkInstall():
    pathSysPolicy = "/usr/share/polkit-1/actions/org.cinnamon.installer.policy"
    if not os.path.isfile(pathSysPolicy):
        pathPolicy = os.path.dirname(DIR_PATH) + "/policy/org.cinnamon.installer.policy"
        shutil.copyfile(pathPolicy, pathSysPolicy)

    pathSysInit = "/usr/sbin/cinnamon-installer"
    if not os.path.isfile(pathSysInit):
        generateInitFile(pathSysInit)
        st = os.stat(pathSysInit)
        os.chmod(pathSysInit, st.st_mode | stat.S_IEXEC)
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
