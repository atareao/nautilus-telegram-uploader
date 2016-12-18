#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file is part of nautilus-500px-uploader
#
# Copyright (C) 2016 Lorenzo Carbonell
# lorenzo.carbonell.cerezo@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#
import gi
try:
    gi.require_version('Gtk', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
    gi.require_version('Nautilus', '3.0')
    gi.require_version('WebKit', '3.0')
except Exception as e:
    print(e)
    exit(-1)
import os
import subprocess
import shlex
import tempfile
import shutil
from threading import Thread
from urllib import unquote_plus
from gi.repository import GObject
from gi.repository import WebKit
from gi.repository import GdkPixbuf
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Nautilus as FileManager

from requests_oauthlib import OAuth1Session
from requests_oauthlib import OAuth1
import json
import codecs
import requests

APP = 'nautilus-500px-uploader'
APPNAME = 'nautilus-500px-uploader'
ICON = 'nautilus-500px-uploader'
VERSION = '0.1.0'

CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config')
CONFIG_APP_DIR = os.path.join(CONFIG_DIR, APP)
TOKEN_FILE = os.path.join(CONFIG_APP_DIR, 'token')

REQUEST_TOKEN_URL = 'https://api.500px.com/v1/oauth/request_token'
AUTHORIZATION_URL = 'https://api.500px.com/v1/oauth/authorize'
ACCESS_TOKEN_URL = 'https://api.500px.com/v1/oauth/access_token'
CLIENT_ID = 'zmxFadkozE65DVCjVbcWjYh7VY8JKxNGmGPjfYG0'
CLIENT_SECTRET = 'vuKcLYBqWVRUIKnpnIBttD8H5SEZTEs4VQgN9HvM'
EXTENSIONS_FROM = ['.jpg']
PARAMS = {
        'access_token_key': '',
        'access_token_secret': ''}

_ = str

CATEGORIES = [[_('Uncategorized'), 0],
              [_('Abstract'), 10],
              [_('Animals'), 11],
              [_('Black and White'), 5],
              [_('Celebrities'), 1],
              [_('City and Architecture'), 9],
              [_('Commercial'), 15],
              [_('Concert'), 16],
              [_('Family'), 20],
              [_('Fashion'), 14],
              [_('Film'), 2],
              [_('Fine Art'), 24],
              [_('Food'), 23],
              [_('Journalism'), 3],
              [_('Landscapes'), 8],
              [_('Macro'), 12],
              [_('Nature'), 18],
              [_('Nude'), 4],
              [_('People'), 7],
              [_('Performing Arts'), 19],
              [_('Sport'), 17],
              [_('Still Life'), 6],
              [_('Street'), 21],
              [_('Transportation'), 26],
              [_('Travel'), 13],
              [_('Underwater'), 22],
              [_('Urban Exploration'), 27],
              [_('Wedding'), 25]]


class Token(object):

    def __init__(self):
        self.params = PARAMS
        self.read()

    def get(self, key):
        try:
            return self.params[key]
        except KeyError:
            self.params[key] = PARAMS[key]
            return self.params[key]

    def set(self, key, value):
        self.params[key] = value

    def read(self):
        try:
            f = codecs.open(TOKEN_FILE, 'r', 'utf-8')
        except IOError:
            self.save()
            f = open(TOKEN_FILE, 'r')
        try:
            self.params = json.loads(f.read())
        except ValueError:
            self.save()
        f.close()

    def save(self):
        if not os.path.exists(CONFIG_APP_DIR):
            os.makedirs(CONFIG_APP_DIR)
        f = open(TOKEN_FILE, 'w')
        f.write(json.dumps(self.params))
        f.close()

    def clear(self):
        self.paramas = PARAMS
        self.save()


class LoginDialog(Gtk.Dialog):
    def __init__(self, url, parent):
        self.code = None

        Gtk.Dialog.__init__(self, _('Login'), parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                             Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_title(APP)
        # self.set_icon_from_file(comun.ICON)
        #
        vbox = Gtk.VBox(spacing=5)
        self.get_content_area().add(vbox)
        hbox1 = Gtk.HBox()
        vbox.pack_start(hbox1, True, True, 0)
        #
        self.scrolledwindow1 = Gtk.ScrolledWindow()
        self.scrolledwindow1.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolledwindow1.set_shadow_type(Gtk.ShadowType.IN)
        hbox1.pack_start(self.scrolledwindow1, True, True, 0)
        self.viewer = WebKit.WebView()
        self.scrolledwindow1.add(self.viewer)
        self.scrolledwindow1.set_size_request(600, 600)
        self.viewer.connect('navigation-policy-decision-requested',
                            self.on_navigation_requested)
        self.viewer.open(url)
        #
        self.show_all()

    # ###################################################################
    # ########################BROWSER####################################
    # ###################################################################
    def on_navigation_requested(self, view, frame, req, nav, pol):
        try:
            uri = req.get_uri()
            print('---', uri, '---')
            pos = uri.find('https://localhost/?oauth_token=')
            if pos > -1:
                ans = uri.split('?')[1]
                self.oauth_token = ans.split('&')[0].split('=')[1]
                self.oauth_verifier = ans.split('&')[1].split('=')[1]
                self.response(Gtk.ResponseType.ACCEPT)
        except Exception as e:
            print(e)
            print('Error')

# class twitterDialog(Gtk.Dialog):


class IdleObject(GObject.GObject):
    """
    Override GObject.GObject to always emit signals in the main thread
    by emmitting on an idle handler
    """
    def __init__(self):
        GObject.GObject.__init__(self)

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)


class DoItInBackground(IdleObject, Thread):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (bool,)),
        'start_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'end_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (float,)),
    }

    def __init__(self, s00, files, name, description, category):
        IdleObject.__init__(self)
        Thread.__init__(self)
        self.elements = files
        self.s00 = s00
        self.name = name
        self.description = description
        self.category = category
        self.stopit = False
        self.ok = False
        self.daemon = True

    def stop(self, *args):
        self.stopit = True

    def send_file(self, file_in):
        ans = self.s00.upload_image(self.name,
                                    self.description,
                                    self.category,
                                    0,
                                    file_in)
        print(ans)

    def run(self):
        total = 0
        for element in self.elements:
            total += get_duration(element)
        self.emit('started', total)
        try:
            self.ok = True
            for element in self.elements:
                if self.stopit is True:
                    self.ok = False
                    break
                self.emit('start_one', element)
                self.send_file(element)
                self.emit('end_one', get_duration(element))
        except Exception as e:
            self.ok = False
        self.emit('ended', self.ok)


class Progreso(Gtk.Dialog, IdleObject):
    __gsignals__ = {
        'i-want-stop': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, title, parent, max_value):
        Gtk.Dialog.__init__(self, title, parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT)
        IdleObject.__init__(self)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(330, 30)
        self.set_resizable(False)
        self.connect('destroy', self.close)
        self.set_modal(True)
        vbox = Gtk.VBox(spacing=5)
        vbox.set_border_width(5)
        self.get_content_area().add(vbox)
        #
        frame1 = Gtk.Frame()
        vbox.pack_start(frame1, True, True, 0)
        table = Gtk.Table(2, 2, False)
        frame1.add(table)
        #
        self.label = Gtk.Label()
        table.attach(self.label, 0, 2, 0, 1,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK,
                     yoptions=Gtk.AttachOptions.EXPAND)
        #
        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_size_request(300, 0)
        table.attach(self.progressbar, 0, 1, 1, 2,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK,
                     yoptions=Gtk.AttachOptions.EXPAND)
        button_stop = Gtk.Button()
        button_stop.set_size_request(40, 40)
        button_stop.set_image(
            Gtk.Image.new_from_stock(Gtk.STOCK_STOP, Gtk.IconSize.BUTTON))
        button_stop.connect('clicked', self.on_button_stop_clicked)
        table.attach(button_stop, 1, 2, 1, 2,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK)
        self.stop = False
        self.show_all()
        self.max_value = float(max_value)
        self.value = 0.0

    def set_max_value(self, anobject, max_value):
        self.max_value = float(max_value)

    def get_stop(self):
        return self.stop

    def on_button_stop_clicked(self, widget):
        self.stop = True
        self.emit('i-want-stop')

    def close(self, *args):
        self.destroy()

    def increase(self, anobject, value):
        self.value += float(value)
        fraction = self.value/self.max_value
        self.progressbar.set_fraction(fraction)
        if self.value >= self.max_value:
            self.hide()

    def set_element(self, anobject, element):
        self.label.set_text(_('Sending: %s') % element)


class S00pxDialog(Gtk.Dialog):

    def __init__(self, parent=None, fileimage=None):
        Gtk.Dialog.__init__(self,
                            _('Send images to 500px'),
                            parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                             Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.set_icon_name(ICON)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        frame = Gtk.Frame()
        frame.set_border_width(5)
        grid = Gtk.Grid()
        grid.set_border_width(5)
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        frame.add(grid)
        self.get_content_area().add(frame)

        label = Gtk.Label(_('Name')+' :')
        label.set_xalign(0)
        grid.attach(label, 0, 0, 1, 1)
        self.entry_name = Gtk.Entry()
        grid.attach(self.entry_name, 1, 0, 1, 1)

        label = Gtk.Label(_('Description')+' :')
        label.set_xalign(0)
        grid.attach(label, 0, 1, 1, 1)
        self.entry_description = Gtk.Entry()
        grid.attach(self.entry_description, 1, 1, 1, 1)

        label = Gtk.Label(_('Category')+' :')
        label.set_xalign(0)
        grid.attach(label, 0, 2, 1, 1)
        listmodel = Gtk.ListStore(str, int)
        for i in range(len(CATEGORIES)):
            listmodel.append(CATEGORIES[i])
        self.combobox = Gtk.ComboBox(model=listmodel)
        cell = Gtk.CellRendererText()
        self.combobox.pack_start(cell, True)
        self.combobox.add_attribute(cell, 'text', 0)
        self.combobox.set_active(0)
        grid.attach(self.combobox, 1, 2, 1, 1)

        label = Gtk.Label(_('Image')+' :')
        label.set_xalign(0)
        grid.attach(label, 0, 3, 1, 1)
        button = Gtk.Button(_('Load image'))
        button.connect('clicked', self.on_button_clicked)
        grid.attach(button, 1, 3, 1, 1)
        self.scrolledwindow1 = Gtk.ScrolledWindow()
        self.scrolledwindow1.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.scrolledwindow1.set_hexpand(True)
        self.scrolledwindow1.set_vexpand(True)
        grid.attach(self.scrolledwindow1, 0, 4, 2, 2)
        self.tweet_image = Gtk.Image()
        self.scrolledwindow1.add(self.tweet_image)
        self.scrolledwindow1.set_size_request(600, 400)

        if fileimage is not None:
            self.load_image(fileimage)

        self.show_all()

    def get_name(self):
        return self.entry_name.get_text()

    def get_description(self):
        return self.entry_description.get_text()

    def get_filename(self):
        return self.fileimage

    def get_category(self):
        index = self.combobox.get_active()
        model = self.combobox.get_model()
        return model[index][1]

    def update_preview_cb(self, file_chooser, preview):
        filename = file_chooser.get_preview_filename()
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 128, 128)
            preview.set_from_pixbuf(pixbuf)
            have_preview = True
        except:
            have_preview = False
        file_chooser.set_preview_widget_active(have_preview)
        return

    def on_button_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(_(
            'Select one or more images to upload to 500px'),
            self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)
        dialog.set_current_folder(os.getenv('HOME'))
        filter = Gtk.FileFilter()
        filter.set_name(_('Images'))
        filter.add_mime_type('image/jpeg')
        filter.add_pattern('*.jpg')
        dialog.add_filter(filter)
        preview = Gtk.Image()
        dialog.set_preview_widget(preview)
        dialog.connect('update-preview', self.update_preview_cb, preview)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filenames = dialog.get_filenames()
            if len(filenames) > 0:
                self.load_image(filenames[0])
        dialog.destroy()

    def load_image(self, image):
        self.fileimage = image
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.fileimage)
        w = pixbuf.get_width()
        h = pixbuf.get_height()
        sw, sh = self.scrolledwindow1.get_size_request()
        zw = float(w)/float(sw)
        zh = float(h)/float(sh)
        if zw > zh:
            z = zw
        else:
            z = zh
        if z > 1:
            pixbuf = pixbuf.scale_simple(
                w/z, h/z,  GdkPixbuf.InterpType.BILINEAR)
        print(zw, zh)
        self.tweet_image.set_from_pixbuf(pixbuf)


def get_duration(file_in):
    return os.path.getsize(file_in)


def get_files(files_in):
    files = []
    for file_in in files_in:
        file_in = unquote_plus(file_in.get_uri()[7:])
        if os.path.isfile(file_in):
            files.append(file_in)
    return files


class S00pxUploaderMenuProvider(GObject.GObject, FileManager.MenuProvider):

    def __init__(self):
        token = Token()
        access_token_key = token.get('access_token_key')
        access_token_secret = token.get('access_token_secret')
        if len(access_token_key) == 0 or len(access_token_secret) == 0:
            self.is_login = False
        else:
            self.is_login = True

    def all_files_are_images(self, items):
        for item in items:
            fileName, fileExtension = os.path.splitext(unquote_plus(
                item.get_uri()[7:]))
            if fileExtension.lower() not in EXTENSIONS_FROM:
                return False
        return True

    def send_images(self, menu, selected, window):
        files = get_files(selected)
        if len(files) > 0:
            if len(files) == 1:
                s00pxd = S00pxDialog(window, files[0])
                if s00pxd.run() == Gtk.ResponseType.ACCEPT:
                    name = s00pxd.get_name()
                    description = s00pxd.get_description()
                    category = s00pxd.get_category()
                    filename = s00pxd.get_filename()
                    files = [filename]
                    s00pxd.destroy()
                else:
                    s00pxd.destroy()
                    return
            else:
                name = ''
                description = ''
                category = 0
            s00px = oauth(window)
            if s00px is not None:
                diib = DoItInBackground(s00px,
                                        files,
                                        name,
                                        description,
                                        category)
                progreso = Progreso(_('Send files to 500px'),
                                    window,
                                    len(files))
                diib.connect('started', progreso.set_max_value)
                diib.connect('start_one', progreso.set_element)
                diib.connect('end_one', progreso.increase)
                diib.connect('ended', progreso.close)
                progreso.connect('i-want-stop', diib.stop)
                diib.start()
                progreso.run()

    def login_to_500px(self, menu, window):
        s00px = oauth(window)
        if s00px is not None:
            self.is_login = True
        else:
            self.is_login = False

    def unlogin_from_500px(self, menu):
        token = Token()
        token.clear()
        self.is_login = False

    def get_file_items(self, window, sel_items):
        top_menuitem = FileManager.MenuItem(
            name='S00pxUploaderMenuProvider::Gtk-500px-top',
            label=_('500px...'),
            tip=_('Send images to 500px'))
        submenu = FileManager.Menu()
        top_menuitem.set_submenu(submenu)

        sub_menuitem_00 = FileManager.MenuItem(
            name='S00pxUploaderMenuProvider::Gtk-500px-sub-00',
            label=_('Send...'),
            tip='Send images to 500px')
        sub_menuitem_00.connect('activate', self.send_images, sel_items,
                                window)
        submenu.append_item(sub_menuitem_00)
        if self.all_files_are_images(sel_items) and self.is_login:
            sub_menuitem_00.set_property('sensitive', True)
        else:
            sub_menuitem_00.set_property('sensitive', False)
        if self.is_login:
            sub_menuitem_01 = FileManager.MenuItem(
                name='S00pxUploaderMenuProvider::Gtk-500px-sub-01',
                label=_('Unlogin'),
                tip='Unlogin from 500px')
            sub_menuitem_01.connect('activate', self.unlogin_from_500px)
        else:
            sub_menuitem_01 = FileManager.MenuItem(
                name='S00pxUploaderMenuProvider::Gtk-500px-sub-01',
                label=_('Login'),
                tip='Login to 500px to send images')
            sub_menuitem_01.connect('activate', self.login_to_500px, window)
        submenu.append_item(sub_menuitem_01)

        sub_menuitem_02 = FileManager.MenuItem(
            name='S00pxUploaderMenuProvider::Gtk-500px-sub-02',
            label=_('About'),
            tip=_('About'))
        sub_menuitem_02.connect('activate', self.about, window)
        submenu.append_item(sub_menuitem_02)

        return top_menuitem,

    def about(self, widget, window):
        ad = Gtk.AboutDialog(parent=window)
        ad.set_name(APPNAME)
        ad.set_version(VERSION)
        ad.set_copyright('Copyrignt (c) 2016\nLorenzo Carbonell')
        ad.set_comments(APPNAME)
        ad.set_license('''
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
''')
        ad.set_website('http://www.atareao.es')
        ad.set_website_label('http://www.atareao.es')
        ad.set_authors([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_documenters([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_icon_name(ICON)
        ad.set_logo_icon_name(APPNAME)
        ad.run()
        ad.destroy()


def oauth(window=None):
    token = Token()
    access_token_key = token.get('access_token_key')
    access_token_secret = token.get('access_token_secret')
    if len(access_token_key) == 0 or len(access_token_secret) == 0:
        try:
            oauth_client = OAuth1Session(CLIENT_ID,
                                         client_secret=CLIENT_SECTRET)
            resp = oauth_client.fetch_request_token(REQUEST_TOKEN_URL)
            print(resp)
        except ValueError as e:
            print(e)
            return None
        url = oauth_client.authorization_url(AUTHORIZATION_URL)
        print(url)
        ld = LoginDialog(url, window)
        if ld.run() == Gtk.ResponseType.ACCEPT:
            oauth_token = ld.oauth_token
            oauth_verifier = ld.oauth_verifier
            ld.destroy()
            print('***', oauth_token, oauth_verifier, '***')
            if len(oauth_token) > 0 and len(oauth_verifier) > 0:
                try:
                    oauth_client = OAuth1Session(
                        CLIENT_ID,
                        client_secret=CLIENT_SECTRET,
                        resource_owner_key=resp.get('oauth_token'),
                        resource_owner_secret=resp.get('oauth_token_secret'),
                        verifier=oauth_verifier)
                    resp = oauth_client.fetch_access_token(ACCESS_TOKEN_URL)
                    print('****', resp, '****')
                except ValueError as e:
                    print(e)
                    ld.destroy()
                    return None
                token.set('access_token_key',
                          resp.get('oauth_token'))
                token.set('access_token_secret',
                          resp.get('oauth_token_secret'))
                token.save()
                return S00px()
        ld.destroy()
    else:
        return S00px()
    return None


class S00px():
    def __init__(self):
        token = Token()
        access_token_key = token.get('access_token_key')
        access_token_secret = token.get('access_token_secret')
        if len(access_token_key) > 0 and len(access_token_secret) > 0:
            auth = OAuth1(
                CLIENT_ID,
                CLIENT_SECTRET,
                token.get('access_token_key'),
                token.get('access_token_secret'))
        self.session = requests.Session()
        self.session.auth = auth

    def upload_image(self, name, description, category, privacy, filename):
        params = {'name': name,
                  'description': description,
                  'category': category,
                  'privacy': privacy}
        try:
            files = {'file': open(filename, 'rb')}
            r = self.session.request('POST',
                                     'https://api.500px.com/v1/photos/upload',
                                     params=params,
                                     files=files)
            return r.text
        except Exception as e:
            print(e)
        return None

if __name__ == '__main__':
    '''
    s00px = S00px()
    ans = s00px.upload_image('name', 'description', 0, 0,
                             '/home/lorenzo/Escritorio/ejemplo.jpg')
    print(ans)
    '''
    window = None
    files = []
    afile = '/home/lorenzo/Escritorio/ejemplo.jpg'
    files.append(afile)
    s00pxd = S00pxDialog(window, files[0])
    if s00pxd.run() == Gtk.ResponseType.ACCEPT:
        name = s00pxd.get_name()
        description = s00pxd.get_description()
        category = s00pxd.get_category()
        filename = s00pxd.get_filename()
        files = [filename]
        s00pxd.destroy()
    else:
        s00pxd.destroy()
        exit()
    s00px = oauth(window)
    print(s00px)
    if s00px is not None:
        diib = DoItInBackground(s00px,
                                files,
                                name,
                                description,
                                category)
        progreso = Progreso(_('Send files to 500px'),
                            window,
                            len(files))
        diib.connect('started', progreso.set_max_value)
        diib.connect('start_one', progreso.set_element)
        diib.connect('end_one', progreso.increase)
        diib.connect('ended', progreso.close)
        progreso.connect('i-want-stop', diib.stop)
        diib.start()
        progreso.run()
