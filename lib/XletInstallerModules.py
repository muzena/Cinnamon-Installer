#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Cinnamon Installer
#
# Authors: Lester Carballo Pérez <lestcape@gmail.com>
#
# Froked from Cinnamon code at:
# https://github.com/linuxmint/Cinnamon
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

import sys
try:
    reload(sys)
    sys.setdefaultencoding('utf-8')
except Exception:
    pass
    #import importlib
    #importlib.reload(sys)

try:
    from gi.repository import Gtk, GObject, Gio
    import os, gettext, glob, locale
    import CApiInstaller
    from functools import cmp_to_key
    import SettingsInstallerWidgets
except Exception:
    e = sys.exc_info()[1]
    print(str(e))
    sys.exit(1)

ABS_PATH = os.path.abspath(__file__)
DIR_PATH = os.path.dirname(os.path.dirname(ABS_PATH)) + "/"

INSTALLER_MODULES = DIR_PATH + 'settings_modules'
INSTALLER_LIBS = DIR_PATH + 'lib'
CINNAMON_MODULES = '/usr/lib/cinnamon-settings/modules'
CINNAMON_LIBS = '/usr/lib/cinnamon-settings/bin'

WIN_WIDTH = 800
WIN_H_PADDING = 20
MIN_LABEL_WIDTH = 16
MAX_LABEL_WIDTH = 25
MIN_PIX_WIDTH = 100
MAX_PIX_WIDTH = 160

class CinnamonSettingsSidePageHacker():
    def __init__(self, hacker):
        main_module = sys.modules["__main__"]
        if ("STANDALONE_MODULES" in main_module.__dict__):
            self.standalone_modules = main_module.STANDALONE_MODULES
            self.categories = main_module.CATEGORIES
            self.control_center_modules = main_module.CONTROL_CENTER_MODULES
        else:
            self.standalone_modules = []
            self.categories = []
            self.control_center_modules = []
        if not INSTALLER_LIBS in sys.path:
            sys.path.append(INSTALLER_LIBS)
        if not CINNAMON_LIBS in sys.path:
            sys.path.append(CINNAMON_LIBS)
        if not INSTALLER_MODULES in sys.path:
            sys.path.append(INSTALLER_MODULES)
        if not CINNAMON_MODULES in sys.path:
            sys.path.append(CINNAMON_MODULES)
        self.hacker = hacker
        self.modules = None
        self.explorer = False
        self.unsortedSidePages = []
        self.sidePages = []
        self.sidePagesIters = {}
        self.store = {}
        self.storeFilter = {}
        self.min_label_length = 0
        self.min_pix_length = 0
        self.content_box = self.hacker.sidePage.content_box
        self.modules_to_hack = {}
        self.modules_hacker = {}
        self.c_manager = self.content_box.c_manager
        self.load_modules()

    def load_modules(self):
        modules_files = self.load_modules_files(INSTALLER_MODULES, [])
        installer_mod = self.import_modules(modules_files)
        for mod in installer_mod:
            name = mod.__name__
            length = len(name)
            if length > 7 and name[length-8:length] == "_replace":
                real_name = name[0:length-8]
            else:
                real_name = name
            self.modules_to_hack[real_name] = mod
        self.modules_to_hack[self.hacker.fileName] = self.hacker
        self.module_to_hack_obj = {}
        modules_files = self.load_modules_files(CINNAMON_MODULES, self.modules_to_hack.keys())
        self.modules = self.import_modules(modules_files)
        self.sys_arg = None
        if len(sys.argv) > 1: #Sorry cinnamon settings you will not recive any thing...
            self.sys_arg = sys.argv[1]
            sys.argv[1] = "fake_argument"
        # Now we need to get the search entry focus and recover the real sys argument when this happen...

    def load_modules_files(self, path, exclude):
        try:
            mod_filter_files = []
            # Standard setting pages... this can be expanded to include applet dirs maybe?
            mod_files = glob.glob(os.path.join(path, '*.py'))
            mod_files.sort()
            if len(mod_files) is 0:
                raise Exception("No settings modules found!!")
            for i in range(len(mod_files)):
                mod_files[i] = os.path.basename(os.path.normpath(mod_files[i]))
                mod_files[i] = mod_files[i].split('.')[0]
                if mod_files[i][0:3] != "cs_":
                    raise Exception("Settings modules must have a prefix of 'cs_' !!")
                if not mod_files[i] in exclude:
                    mod_filter_files.append(mod_files[i])
            return mod_filter_files
        except Exception:
            e = sys.exc_info()[1]
            print(str(e))
            sys.exit(1)
        return None

    def import_modules(self, mod_files):
        try:
            modules = map(__import__, mod_files)
            return modules
        except Exception:
            e = sys.exc_info()[1]
            print(str(e))
            #sys.exit(1)
        return None

    def add_moduler_hacker(self):
        for mod_to_hack in self.modules_to_hack:
            try:
                if mod_to_hack != self.hacker.fileName:
                     mod = self.modules_to_hack[mod_to_hack].Module(self.hacker.content_installer_box)
                     if self.loadCheck(mod) and self.setParentRefsHacker(mod):
                         self.modules_hacker[mod_to_hack] = mod
                else:
                     mod = self.hacker
                     self.modules_hacker[mod_to_hack] = mod
                self.unsortedSidePages.append((self.hacker.sidePage, mod.name, mod.category, mod.sidePage.name, mod.sidePage))
            except:
                print("Failed to load module %s" % mod_to_hack)
                import traceback
                traceback.print_exc()

    def load_sidePage(self):
        try:#Python 3 needed
            for i in range(len(self.modules)):
                try:
                    mod = self.modules[i].Module(self.content_box)
                    if self.loadCheck(mod) and self.setParentRefs(mod):
                        self.unsortedSidePages.append((mod.sidePage, mod.name, mod.category, mod.sidePage.name, mod.sidePage))
                except:
                    print("Failed to load module %s" % self.modules[i])
                    import traceback
                    traceback.print_exc()
        except:
            pass
        self.add_moduler_hacker()

        for item in self.control_center_modules:
            ccmodule = SettingsInstallerWidgets.CCModule(item[0], item[1], item[2], item[3], item[4], self.content_box)
            if ccmodule.process(self.c_manager):
                self.unsortedSidePages.append((ccmodule.sidePage, ccmodule.name, ccmodule.category, ccmodule.sidePage.name, ccmodule.sidePage))

        for item in self.standalone_modules:
            samodule = SettingsInstallerWidgets.SAModule(item[0], item[1], item[2], item[3], item[4], self.content_box)
            if samodule.process():
                self.unsortedSidePages.append((samodule.sidePage, samodule.name, samodule.category, samodule.sidePage.name, samodule.sidePage))

        # sort the modules alphabetically according to the current locale
        sidePageNamesToSort = map(lambda m: m[3], self.unsortedSidePages)
        sortedSidePageNames = sorted(sidePageNamesToSort, key=cmp_to_key(locale.strcoll))
        for sidePageName in sortedSidePageNames:
            nextSidePage = None
            for trySidePage in self.unsortedSidePages:
                if(trySidePage[3] == sidePageName):
                    nextSidePage = trySidePage

            self.sidePages.append(nextSidePage);
        self.create_iterators()

    def create_iterators(self):
        self.sidePagesIters = {}
        for sidepage in self.sidePages:
            sp, sp_id, sp_cat, sp_name, real_sp = sidepage
            if not sp_cat in self.store:  #       Label         Icon    sidePage    Category    Real sidePage
                self.store[sidepage[2]] = Gtk.ListStore(str,          str,    object,     str,        object)
                for category in self.categories:
                    if category["id"] == sp_cat:
                        category["show"] = True

            # Don't allow item names (and their translations) to be more than 30 chars long. It looks ugly and it creates huge gaps in the icon views
            name = str(sp_name)
            try:
                name = unicode(name,'utf-8')
            except:
                pass
            if len(name) > 30:
                name = "%s..." % name[:30]
            self.sidePagesIters[sp_id] = (self.store[sp_cat].append([name, sp.icon, sp, sp_cat, real_sp]), sp_cat)
            #print("sidePagesIters " + sp_id)

    def loadCheck (self, mod):
        try:
            return mod._loadCheck()
        except:
            return True

    def setParentRefsHacker(self, mod):
        try:
            mod._setParentRef(self.window, self.builder)
        except AttributeError:
            pass
        return True

    def setParentRefs(self, mod):
        try:
            mod._setParentRef(self.window)
        except AttributeError:
            pass
        return True

    def _setParentRef(self, window, builder):
        self.window = window
        self.builder = builder
        self.side_view = {}
        if self.builder.get_object(Gtk.Buildable.get_name(window)) is None:
            listToFind = {"category_box": None, "side_view_sw": None, "content_box_sw": None, "button_back": None, "search_box": None, "top_bar": None}
            self.findGtkComponnents(window, listToFind)
            self.side_view_container = listToFind["category_box"]
            self.side_view_sw = listToFind["side_view_sw"]
            self.content_box_sw = listToFind["content_box_sw"]
            self.button_back = listToFind["button_back"]
            self.search_entry = listToFind["search_box"]
            self.top_bar = listToFind["top_bar"]
        else:
            self.side_view_container = self.builder.get_object("category_box")
            self.side_view_sw = self.builder.get_object("side_view_sw")
            self.content_box_sw = self.builder.get_object("content_box_sw")
            self.button_back = self.builder.get_object("button_back")
            self.search_entry = self.builder.get_object("search_box")
            self.top_bar = self.builder.get_object("top_bar")
        #self.search_entry.connect('focus-in-event', self._on_sys_arguments)
        self.side_view_container.connect('size_allocate', self._exploreButtons)
        self.prepare_swapper()
        self.calculate_bar_heights()
        self.load_sidePage()
        return self.modules_hacker


    def findGtkComponnents(self, window, listToFind):
        try:
            childs = window.get_children()
            for ch in childs:
                if Gtk.Buildable.get_name(ch) in listToFind:
                    listToFind[Gtk.Buildable.get_name(ch)] = ch
                self.findGtkComponnents(ch, listToFind)
        except Exception:
            pass

    def prepare_swapper(self):
        for key in self.store.keys():
            char, pix = self.get_label_min_width(self.store[key])
            self.min_label_length = max(char, self.min_label_length)
            self.min_pix_length = max(pix, self.min_pix_length)
            self.storeFilter[key] = self.store[key].filter_new()
            self.storeFilter[key].set_visible_func(self.filter_visible_function)

        self.min_label_length += 2
        self.min_pix_length += 4

        self.min_label_length = max(self.min_label_length, MIN_LABEL_WIDTH)
        self.min_pix_length = max(self.min_pix_length, MIN_PIX_WIDTH)

        self.min_label_length = min(self.min_label_length, MAX_LABEL_WIDTH)
        self.min_pix_length = min(self.min_pix_length, MAX_PIX_WIDTH)

    def get_id_for_category_label(self, label):
        for category in self.categories:
            if category["label"] == label:
                return category["id"]
        return ""

    def get_label_min_width(self, model):
        min_width_chars = 0
        min_width_pixels = 0
        icon_view = Gtk.IconView()
        iter = model.get_iter_first()
        while iter != None:
            string = model.get_value(iter, 0)
            split_by_word = string.split(" ")
            for word in split_by_word:
                layout = icon_view.create_pango_layout(word)
                item_width, item_height = layout.get_pixel_size()
                if item_width > min_width_pixels:
                    min_width_pixels = item_width
                if len(word) > min_width_chars:
                    min_width_chars = len(word)
            iter = model.iter_next(iter)
        return min_width_chars, min_width_pixels

    def filter_visible_function(self, model, iter, user_data = None):
        sidePage = model.get_value(iter, 2)
        text = self.search_entry.get_text().lower()       
        if sidePage.name.lower().find(text) > -1 or \
           sidePage.keywords.lower().find(text) > -1:
            return True
        else:
            return False

    def _exploreButtons(self, parent, event, *data):
        if not self.explorer:
            self._try_to_check_sys_arg()
            categories = self.side_view_container.get_children()
            for category in categories:
                if isinstance(category, Gtk.Box):
                   children = category.get_children()
                   for child in children:
                       if isinstance(child, Gtk.Label):
                           last_category_id = self.get_id_for_category_label(child.get_text())
                if isinstance(category, Gtk.IconView):
                    self.reconnect_categories(category, last_category_id)
        self.explorer = True

    def reconnect_categories(self, category, category_id):
       self.side_view[category_id] = category
       GObject.signal_handlers_destroy(self.side_view[category_id])
                
       self.side_view[category_id].connect("item-activated", self.side_view_nav, category_id)
       self.side_view[category_id].connect("button-release-event", self.button_press, category_id)
       self.side_view[category_id].connect("keynav-failed", self.on_keynav_failed, category_id)
       self.side_view[category_id].connect("selection-changed", self.on_selection_changed, category_id)
       self.create_cinnamon_order(category_id)

    def _try_to_check_sys_arg(self):
        if len(sys.argv) > 1 and self.sys_arg:
            sys.argv[1] = self.sys_arg
            if sys.argv[1] in self.sidePagesIters.keys():
                (iter, cat) = self.sidePagesIters[sys.argv[1]]
                path = self.store[cat].get_path(iter)
                if path:
                    self.go_to_sidepage(cat, path)

    def create_cinnamon_order(self, last_category_id): #This function reorder the side page if not have a good order....
        sidePages = []
        model = self.side_view[last_category_id].get_model()
        iter = model.get_iter_first()
        if last_category_id in self.store:
            storeModel = self.store[last_category_id]
            iterator = storeModel.get_iter_first()
            while iter is not None:
                sp_origin = model.get_value(iter, 2)
                sp_new = storeModel.get_value(iterator, 4)
                if not self.compare_sidePage(sp_origin, sp_new):
                    iter_found = self.find_side_page_iter(sp_origin, storeModel, iterator, 4)
                    if iter_found:
                        storeModel.swap(iterator, iter_found)
                        iterator = iter_found
                iter = model.iter_next(iter)
                iterator = storeModel.iter_next(iterator)

    def find_side_page_iter(self, sidePage, model, iter, pos):
        while iter is not None:
            sp_new = model.get_value(iter, pos)
            if self.compare_sidePage(sidePage, sp_new):
                return iter
            iter = model.iter_next(iter)
        return None
    
    def compare_sidePage(self, sp_origin, sp_new):
        if not sp_origin.module and sp_new.module:
            return False
        if sp_origin.module and not sp_new.module:
            return False
        if sp_origin.module and sp_new.module:
            return self.compare_modules(sp_origin.module, sp_new.module)
        if sp_origin.icon != sp_new.icon:
             return False
        if sp_origin.name != sp_new.name:
             return False
        if sp_origin.is_c_mod != sp_new.is_c_mod:
             return False
        if sp_origin.is_standalone != sp_new.is_standalone:
             return False
        if sp_origin.exec_name != sp_new.exec_name:
             return False
        if sp_origin.keywords != sp_new.keywords:
             return False
        return True

    def compare_modules(self, mod_origin, mod_new):
        if mod_origin.__module__ != mod_new.__module__ and mod_origin.__module__ + "_replace" != mod_new.__module__:
            return False
        return True

    def side_view_nav(self, side_view, path, cat):
        selected_items = side_view.get_selected_items()
        if len(selected_items) > 0:
            self.deselect(cat)

            '''
            model = side_view.get_model()
            filtered_path = model.convert_path_to_child_path(selected_items[0])
            tree_iter = model.get_iter(filtered_path)
            value = model.get_value(tree_iter, 2)
            #self.go_to_sidepage_my(self, name, icon=None, cat=None)
            if value.module:
                print("holaaaaaaaaaa " + str(filtered_path) + str(value.module.__module__))
            '''

            filtered_path = side_view.get_model().convert_path_to_child_path(selected_items[0])
            if filtered_path is not None:
                self.go_to_sidepage(cat, filtered_path)

    def button_press(self, widget, event, category):
        if event.button == 1:
            self.side_view_nav(widget, None, category)

    def on_selection_changed(self, widget, category):
        sel = widget.get_selected_items()
        if len(sel) > 0:
            self.current_cat_widget = widget
            self.bring_selection_into_view(widget)
        for iv in self.side_view:
            if self.side_view[iv] == self.current_cat_widget:
                continue
            self.side_view[iv].unselect_all()

    def bring_selection_into_view(self, iconview):
        sel = iconview.get_selected_items()
        if sel:
            path = sel[0]
            found, rect = iconview.get_cell_rect(path, None)

            cw = self.side_view_container.get_window()
            cw_x, cw_y = cw.get_position()

            ivw = iconview.get_window()
            iv_x, iv_y = ivw.get_position()

            final_y = rect.y + (rect.height / 2) + cw_y + iv_y

            adj = self.side_view_sw.get_vadjustment()
            page = adj.get_page_size()
            current_pos = adj.get_value()

            if final_y > current_pos + page:
                adj.set_value(iv_y + rect.y)
            elif final_y < current_pos:
                adj.set_value(iv_y + rect.y)

    def on_keynav_failed(self, widget, direction, category):
        num_cats = len(self.categories)
        current_idx = self.get_cur_cat_index(category)
        new_cat = self.categories[current_idx]
        ret = False
        dist = 1000
        sel = None

        if direction == Gtk.DirectionType.DOWN and current_idx < num_cats - 1:
            new_cat = self.categories[current_idx + 1]
            col = self.get_cur_column(widget)
            new_cat_view = self.side_view[new_cat["id"]]
            model = new_cat_view.get_model()
            iter = model.get_iter_first()
            while iter is not None:
                path = model.get_path(iter)
                c = new_cat_view.get_item_column(path)
                d = abs(c - col)
                if d < dist:
                    sel = path
                    dist = d
                iter = model.iter_next(iter)
            self.reposition_new_cat(sel, new_cat_view)
            ret = True
        elif direction == Gtk.DirectionType.UP and current_idx > 0:
            new_cat = self.categories[current_idx - 1]
            col = self.get_cur_column(widget)
            new_cat_view = self.side_view[new_cat["id"]]
            model = new_cat_view.get_model()
            iter = model.get_iter_first()
            while iter is not None:
                path = model.get_path(iter)
                c = new_cat_view.get_item_column(path)
                d = abs(c - col)
                if d <= dist:
                    sel = path
                    dist = d
                iter = model.iter_next(iter)
            self.reposition_new_cat(sel, new_cat_view)
            ret = True
        return ret

    def get_cur_cat_index(self, category):
        i = 0
        for cat in self.categories:
            if category == cat["id"]:
                return i
            i += 1

    def get_cur_column(self, iconview):
        s, path, cell = iconview.get_cursor()
        if path:
            col = iconview.get_item_column(path)
            return col

    def reposition_new_cat(self, sel, iconview):
        iconview.set_cursor(sel, None, False)
        iconview.select_path(sel)
        iconview.grab_focus()

    '''
    def go_to_sidepage_my(self, name, icon=None, cat=None):
        sidePage = self.get_sidepage(name, icon, cat)
        if sidePage:
            if not sidePage.is_standalone:
                self.side_view_sw.hide()
                self.search_entry.hide()
                self.window.set_title(sidePage.name)
                sidePage.build()
                self.content_box_sw.show()
                self.button_back.show()
                self.current_sidepage = sidePage
                self.maybe_resize(sidePage)
            else:
                sidePage.build()

    def get_sidepage(self, name, icon=None, cat=None):
        for sidePage in self.unsortedSidePages:
            if (cat == None or sidePage[2] == cat) and (icon == None or icon == sidePage[0].icon) and (sidePage[1] == name):
                return sidePage[0]
        return None
    '''
    def go_to_sidepage(self, cat, path):
        iterator = self.store[cat].get_iter(path)
        sidePage = self.store[cat].get_value(iterator, 2)
        if not sidePage.is_standalone:
            hacker_mod = None
            self.side_view_sw.hide()
            self.search_entry.hide()
            self.window.set_title(sidePage.name)
            if self.hacker.sidePage == sidePage:
                hacker_mod = self.get_hacker_module(cat, path)
                if hacker_mod:
                    self.hacker.set_current_module(hacker_mod)
                    self.window.set_title(hacker_mod.sidePage.name)
            sidePage.build()
            self.content_box_sw.show()
            self.button_back.show()
            self.current_sidepage = sidePage
            if hacker_mod:
                self.maybe_resize(hacker_mod.sidePage)
            else:
                self.maybe_resize(sidePage)
        else:
            sidePage.build()

    def get_hacker_module(self, cat, path):
        key = self.get_real_sidePage_id(cat, path)
        if key and key != self.hacker.name:
            for file_name in self.modules_hacker:
                if self.modules_hacker[file_name].name == key:
                    return self.modules_hacker[file_name]
        return None

    def get_real_sidePage_id(self, cat, path):
        for key in self.sidePagesIters:
            (iter, cat_side) = self.sidePagesIters[key]
            if cat_side == cat and self.store[cat].get_path(iter) == path:
                return key
        return None

    def maybe_resize(self, sidePage):
        m, n = self.content_box.get_preferred_size()
        use_width = WIN_WIDTH
        if n.width > WIN_WIDTH:
            use_width = n.width
        if not sidePage.size:
            self.window.resize(use_width, n.height + self.bar_heights + WIN_H_PADDING)
        elif sidePage.size > -1:
            self.window.resize(use_width, sidePage.size + self.bar_heights + WIN_H_PADDING)

    def deselect(self, cat):
        for key in self.side_view.keys():
            if key is not cat:
                self.side_view[key].unselect_all()

    def calculate_bar_heights(self):
        h = 0
        m, n = self.top_bar.get_preferred_size()
        h += n.height
        self.bar_heights = h
