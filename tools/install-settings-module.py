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
    import sys, py_compile, os, shutil
except Exception:
    e = sys.exc_info()[1]
    print(str(e))
    sys.exit(1)

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(os.path.dirname(ABS_PATH)) + "/"

PATH_INSTALL = "/usr/lib/cinnamon-settings/modules/cs_installer.py"
shutil.copytree(os.path.join(DIR_PATH, "cs_installer.py"), PATH_INSTALL)

'''
#now test that
#os.system("python /usr/lib/cinnamon-settings/cinnamon-settings.py")
#os.system("python /usr/lib/cinnamon-settings/cinnamon-settings.py desklets")
#os.system("python /usr/lib/cinnamon-settings/cinnamon-settings.py applets configurableMenu@lestcape configurableMenu@lestcape")
#os.system("python /usr/lib/cinnamon-settings/cinnamon-settings.py applets configurableMenu@lest")
