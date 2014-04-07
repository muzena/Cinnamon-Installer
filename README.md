Cinnamon-Installer 0.64-Beta
==================

Last version release date: 6 April 2014

Author: [Lester Carballo Pérez](https://github.com/lestcape)

Special thanks to:
Manjaro users and developers they have given their support to make this project possible.

A GUI Packages Manager with the ability to support all distros, where you can install Cinnamon desktop.

This is a project of GUI packages Manager tools writing in python.

The idea it's allow have an installer and uninstaller of only one package at the same time,
but with the ability to support all distros, where Cinnamon desktop can be installed.

For now are planed add support to:

   - Debian base distros using: aptdaemon(https://launchpad.net/aptdaemon/) binding and aptdaemon.client example.
   - Manjaro and Arch Linux using: python alpm bindings and pamac like example(http://git.manjaro.org/core/pamac).
   - Several ways for install packages(http://www.freedesktop.org/software/PackageKit/pk-matrix.html) using the PackageKit service(http://www.freedesktop.org/software/PackageKit/index.html)

System detection:

  Ansible project https://github.com/ansible/ansible

Updater
--------------
This application come inside with another application caller Updater to allow update the main application. 


This program not longer has support for Arch Linux.
--------------
The comunity of Arch Linux do not want that I or other Cinnamon developer, publish about Cinnamon, and receive the users feedback (necessary on the developing any app). When the comunity of Arch Linux, want to be open to the free software world, sure that I want to support Arch Linux again...

Change log
--------------
0.6.1-Beta
   - Fixed some errors on the first load.

0.6-Beta
   - Improved the GUI.
   - Added support for Manjaro, and Arch Linux based distros...

0.5-Beta
   - Improve the search to allow space.
   - Fixed the bug of unistall package on ubuntu 14.04.


0.4-Beta
   - Added translation support.
   - Execution forced to python 3(Cinnamon compatibility).

0.3-Beta
   - Now can report the error to users.
   - Now can display the version.
   - Fixed problem of package no exist.

0.2-Beta
   - Removed the import of apport, now run native on Linux Mint(Cinnamon).

0.1-Beta
   - Initial Release

Anyone is wellcome to contribute...

Thanks. 
