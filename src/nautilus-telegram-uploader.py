#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of nautilus-telegram-uploader
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
except Exception as e:
    print(e)
    exit(-1)
import os
import ConfigParser
from PIL import Image
import telebot
from telebot.apihelper import ApiException

from urllib import unquote_plus

from threading import Thread
from gi.repository import GObject

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Nautilus as FileManager

APP = '$APP$'
VERSION = '$VERSION$'
TOKEN = '270805444:AAEwqvaJAiQ8ZFKvgSrGM2-h2lTYwiUkl8Y'

CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config')
CONFIG_APP_DIR = os.path.join(CONFIG_DIR, APP)
CONFIG_FILE = os.path.join(CONFIG_APP_DIR, '{0}.conf'.format(APP))
if not os.path.exists(CONFIG_APP_DIR):
    os.makedirs(CONFIG_APP_DIR)

IMAGE_EXTENSIONS = ['.bmp', '.dds', '.exif', '.gif', '.jpg', '.jpeg', '.jp2',
                    '.jpx', '.pcx', '.png', '.pnm', '.ras', '.tga', '.tif',
                    '.tiff', '.xbm', '.xpm']
VIDEO_EXTENSIONS = ['.mp4']
AUDIO_EXTENSIONS = ['.mp3']


_ = str


class IdleObject(GObject.GObject):
    """
    Override GObject.GObject to always emit signals in the main thread
    by emmitting on an idle handler
    """
    def __init__(self):
        GObject.GObject.__init__(self)

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)


class UserIDDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, _('User ID'), parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                             Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_title(APP)
        #
        vbox = Gtk.VBox(spacing=5)
        self.get_content_area().add(vbox)
        hbox1 = Gtk.HBox()
        vbox.pack_start(hbox1, True, True, 10)
        #
        label = Gtk.Label(_('User ID') + ' :')
        hbox1.pack_start(label, True, True, 10)

        self.entry = Gtk.Entry()
        hbox1.pack_start(self.entry, True, True, 0)
        #
        self.show_all()


class DoItInBackground(IdleObject, Thread):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (bool,)),
        'start_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'end_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (float,)),
    }

    def __init__(self, user_id, files):
        IdleObject.__init__(self)
        Thread.__init__(self)
        self.tb = telebot.TeleBot(TOKEN)  # create a new Telegram Bot object
        self.user_id = user_id
        self.elements = files
        self.stopit = False
        self.ok = False
        self.daemon = True

    def stop(self, *args):
        self.stopit = True

    def send_file(self, file_in):
        filename, file_extension = os.path.splitext(file_in)
        if file_extension.lower() in IMAGE_EXTENSIONS:
            image_in = Image.open(file_in)
            basename, old_extension = os.path.splitext(file_in)
            if old_extension.lower() != '.jpg':
                temp_image = basename + '.jpg'
                image_in.save(temp_image)
                tb.send_photo(self.user_id, temp_image)
                os.remove(temp_image)
            else:
                tb.send_photo(self.user_id, file_in)
        elif file_extension.lower() in VIDEO_EXTENSIONS:
            tb.send_video(self.user_id, file_in)
        elif file_extension.lower() in AUDIO_EXTENSIONS:
            tb.send_audio(self.user_id, file_in)
        else:
            tb.send_data(self.user_id, file_in)

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
            print(e)
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
        fraction = self.value / self.max_value
        self.progressbar.set_fraction(fraction)
        if self.value >= self.max_value:
            self.hide()

    def set_element(self, anobject, element):
        self.label.set_text(_('Sending: %s') % element)


def get_duration(file_in):
    return os.path.getsize(file_in)


def get_files(files_in):
    files = []
    for file_in in files_in:
        file_in = unquote_plus(file_in.get_uri()[7:])
        if os.path.isfile(file_in):
            files.append(file_in)
    return files


class TelegramUploaderMenuProvider(GObject.GObject, FileManager.MenuProvider):

    def __init__(self):
        config = ConfigParser.ConfigParser()
        config.read(CONFIG_FILE)
        if len(config.sections()) == 0:
            self.user_id = None
        else:
            try:
                self.user_id = config.getint('User', 'ID')
            except ValueError as e:
                print(e)
                self.user_id = None

    def all_files_are_files(self, items):
        for item in items:
            if os.path.isfile(unquote_plus(item.get_uri()[7:])):
                return False
        return True

    def send_files(self, menu, selected, window):
        files = get_files(selected)
        if len(files) > 0:
            diib = DoItInBackground(self.user_id,
                                    files)
            progreso = Progreso(_('Send files to telegram'),
                                window,
                                len(files))
            diib.connect('started', progreso.set_max_value)
            diib.connect('start_one', progreso.set_element)
            diib.connect('end_one', progreso.increase)
            diib.connect('ended', progreso.close)
            progreso.connect('i-want-stop', diib.stop)
            diib.start()
            progreso.run()

    def login_to_telegram(self, menu, window):
        uid = UserIDDialog(window)
        if uid.run() == Gtk.ResponseType.ACCEPT:
            self.user_id = int(uid.entry.get_text())
            uid.destroy()
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            config = ConfigParser.ConfigParser()
            config.add_section('User')
            config.set('User', 'ID', user_id)
            with open(CONFIG_FILE, 'w') as configfile:
                config.write(configfile)

    def unlogin_from_telegram(self, menu):
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        self.user_id = None

    def get_file_items(self, window, sel_items):
        top_menuitem = FileManager.MenuItem(
            name='TelegramUploaderMenuProvider::Gtk-telegram-top',
            label=_('telegram...'),
            tip=_('Send files to telegram'))
        submenu = FileManager.Menu()
        top_menuitem.set_submenu(submenu)

        sub_menuitem_00 = FileManager.MenuItem(
            name='TelegramUploaderMenuProvider::Gtk-telegram-sub-00',
            label=_('Send...'),
            tip='Send files to telegram')
        sub_menuitem_00.connect('activate', self.send_files, sel_items,
                                window)
        submenu.append_item(sub_menuitem_00)

        if self.all_files_are_files(sel_items) and self.is_login:
            sub_menuitem_00.set_property('sensitive', True)
        else:
            sub_menuitem_00.set_property('sensitive', False)
        if self.user_id is None:
            sub_menuitem_01 = FileManager.MenuItem(
                name='TelegramUploaderMenuProvider::Gtk-telegram-sub-01',
                label=_('Login'),
                tip='Login to telegram to send images')
            sub_menuitem_01.connect('activate', self.login_to_telegram, window)
        else:
            sub_menuitem_01 = FileManager.MenuItem(
                name='TelegramUploaderMenuProvider::Gtk-telegram-sub-01',
                label=_('Unlogin'),
                tip='Unlogin from telegram')
            sub_menuitem_01.connect('activate', self.unlogin_from_telegram)
        submenu.append_item(sub_menuitem_01)

        sub_menuitem_02 = FileManager.MenuItem(
            name='TelegramUploaderMenuProvider::Gtk-telegram-sub-02',
            label=_('About'),
            tip=_('About'))
        sub_menuitem_02.connect('activate', self.about, window)
        submenu.append_item(sub_menuitem_02)

        return top_menuitem,

    def about(self, widget, window):
        ad = Gtk.AboutDialog(parent=window)
        ad.set_name(APP)
        ad.set_version(VERSION)
        ad.set_copyright('Copyrignt (c) 2017\nLorenzo Carbonell')
        ad.set_comments(APP)
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
        ad.set_icon_name(APP)
        ad.set_logo_icon_name(APP)
        ad.run()
        ad.destroy()


if __name__ == '__main__':
    import telebot
    from telebot.apihelper import ApiException
    config = ConfigParser.ConfigParser()
    config.read(CONFIG_FILE)
    if len(config.sections()) == 0:
        config.add_section('User')
        config.set('User', 'ID', '')
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
            user_id = -1
    else:
        try:
            user_id = config.getint('User', 'ID')
            print(user_id)
        except ValueError as e:
            print(e)
            user_id = -1
    if user_id == -1:
        uid = UserIDDialog(None)
        if uid.run() == Gtk.ResponseType.ACCEPT:
            user_id = int(uid.entry.get_text())
            uid.destroy()
            config.set('User', 'ID', user_id)
            with open(CONFIG_FILE, 'w') as configfile:
                config.write(configfile)
    TOKEN = '270805444:AAEwqvaJAiQ8ZFKvgSrGM2-h2lTYwiUkl8Y'
    try:
        tb = telebot.TeleBot(TOKEN) #create a new Telegram Bot object
        tb.send_message(user_id, 'sample 2')
        photo = open('/home/lorenzo/Escritorio/telegram-cli.jpg')
        tb.send_photo(user_id, photo)
    except ApiException as e:
        print(e)
        
    '''
    uid = UserIDDialog(None)
    if uid.run() == Gtk.ResponseType.ACCEPT:
        code = int(uid.entry.get_text())
        uid.destroy()
        TOKEN = '270805444:AAEwqvaJAiQ8ZFKvgSrGM2-h2lTYwiUkl8Y'
        try:
            tb = telebot.TeleBot(TOKEN) #create a new Telegram Bot object
            tb.send_message(code, 'sample 2')
            photo = open('/home/lorenzo/Escritorio/telegram-cli.jpg')
            tb.send_photo(code, photo)
        except ApiException as e:
            print(e)
    '''
    '''
    def temporal(ipt):
        print('aqui')
        cd = CodeDialog(None)
        if cd.run() == Gtk.ResponseType.ACCEPT:
            code =cd.entry.get_text()
            cd.destroy()
            print(code)
            ipt.set(code)
    pd = PhoneDialog(None)
    if pd.run() == Gtk.ResponseType.ACCEPT:
        phone = pd.entry.get_text()
        pd.destroy()
        time.sleep(1)
        print(phone)
        ipt = InputPhoneThread(phone)
        ipt.connect('code', temporal)
        ipt.run()

        cd = CodeDialog(None)
        if cd.run() == Gtk.ResponseType.ACCEPT:
            code =cd.entry.get_text()
            cd.destroy()
            print(code)
            ipt.set(code)
        '''

