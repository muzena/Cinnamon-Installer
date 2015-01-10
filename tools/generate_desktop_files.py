#!/usr/bin/python

import commands, os

sourceFile = "usr/lib/cinnamon-settings/cinnamon-settings.py"

menuName = commands.getoutput("cat " + sourceFile + " | grep menuName")
menuName = menuName.replace("menuName", "")
menuName = menuName.replace("=", "")
menuName = menuName.replace("_(", "")
menuName = menuName.replace("\"", "")
menuName = menuName.replace(")", "")
menuName = menuName.strip()

menuComment = commands.getoutput("cat " + sourceFile + " | grep menuComment")
menuComment = menuComment.replace("menuComment", "")
menuComment = menuComment.replace("=", "")
menuComment = menuComment.replace("_(", "")
menuComment = menuComment.replace("\"", "")
menuComment = menuComment.replace(")", "")
menuComment = menuComment.strip()

desktopFile = open("usr/share/applications/cinnamon-settings.desktop", "w")
desktopFile.writelines("""[Desktop Entry]
Name=Cinnamon Settings
""")

import gettext
gettext.install("cinnamon", "/usr/share/locale")

for directory in os.listdir("/usr/share/locale"):
	if os.path.isdir(os.path.join("/usr/share/locale", directory)):
		try:
			language = gettext.translation('cinnamon-settings', "/usr/share/locale", languages=[directory])
			language.install()
			desktopFile.writelines("Name[%s]=%s\n" % (directory, _(menuName)))
		except:
			pass

desktopFile.writelines("Comment=Fine-tune Cinnamon settings\n")

for directory in os.listdir("/usr/share/locale"):
	if os.path.isdir(os.path.join("/usr/share/locale", directory)):
		try:
			language = gettext.translation('cinnamon-settings', "/usr/share/locale", languages=[directory])
			language.install()			
			desktopFile.writelines("Comment[%s]=%s\n" % (directory, _(menuComment)))
		except:
			pass

desktopFile.writelines("""Exec=cinnamon-settings
Icon=preferences-system
Terminal=false
Type=Application
Encoding=UTF-8
OnlyShowIn=X-Cinnamon;
Categories=GNOME;GTK;Settings;DesktopSettings;
StartupNotify=false
""")


