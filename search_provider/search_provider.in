#!/usr/bin/python3
# Copyright 2020 gi-lom
# Copyright 2020 Nikita Kravets
# SPDX-License-Identifier: GPL-3.0-or-later

import dbus
import dbus.service
import threading

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib, Gio
from googletrans import LANGUAGES, Translator

APP_ID = 'com.github.gi_lom.dialect'

search_bus_name = 'org.gnome.Shell.SearchProvider2'
sbn = dict(dbus_interface=search_bus_name)

class TranslateService(dbus.service.Object):
    bus_name = 'com.github.gi_lom.dialect.SearchProvider'
    _object_path = '/' + bus_name.replace('.', '/')

    def __init__(self):
        # init dbus
        self.session_bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(self.bus_name, bus=self.session_bus)
        dbus.service.Object.__init__(self, bus_name, self._object_path)

        # Translations running now
        self.translations = dict()
        self.settings = Gio.Settings.new(APP_ID)

        self.active_thread = None
        self.trans_queue = []

        self.translator = Translator()

    @dbus.service.method(in_signature='as', out_signature='as', **sbn)
    def GetInitialResultSet(self, terms):
        """
        Join separate terms in one ID line, start translation and send this line back
        on start of input
        """
        text = ' '.join(terms)
        self.translation(text)
        return [text]

    @dbus.service.method(in_signature='as', out_signature='aa{sv}', **sbn)
    def GetResultMetas(self, ids):
        """Send translated text"""
        translate_id = ids[0]

        # wait for the translation to finish
        if translate_id in self.translations:
            while self.translations[translate_id] == '':
                pass

            name = self.translations[translate_id]
            self.translations.clear()

            return [
                dict(
                    id=id,
                    name=name,
                    gicon='com.github.gi_lom.dialect',
                )
                for id in ids
            ]
        else:
            # if there is no translation of this text send the original text
            return [
                dict(
                    id=id,
                    name=id,
                    gicon='com.github.gi_lom.dialect',
                )
                for id in ids
            ]

    @dbus.service.method(in_signature='asas', out_signature='as', **sbn)
    def GetSubsearchResultSet(self, previous_results, new_terms):
        """
        Join separate terms in one ID line, start translation and send this line back
        on update of text
        """
        text = ' '.join(new_terms)
        self.translation(text)
        return [text]

    @dbus.service.method(in_signature='sasu', **sbn)
    def ActivateResult(self, id, terms, timestamp):
        pass

    @dbus.service.method(in_signature='asu', terms='as', timestamp='u', **sbn)
    def LaunchSearch(self, terms, timestamp):
        pass

    def translation(self, src_text):
        """
        Start a new translation
        """
        self.translations[src_text] = ''

        # set dest_language to last used language and src_language to auto detection
        src_language = 'auto'
        dest_language = list(self.settings.get_value('dest-langs'))[0]

        if self.trans_queue:
            self.trans_queue.pop(0)
        self.trans_queue.append({
            'src_text': src_text,
            'src_language': src_language,
            'dest_language': dest_language
        })

        # Check if there are any active threads.
        if self.active_thread is not None:
            self.active_thread.join()
            del self.active_thread
        self.active_thread = threading.Thread(target=self.run_translation)
        self.active_thread.start()

    def run_translation(self):
        """
        Translate all text in the queue
        """
        while self.trans_queue:
            # If the first language is revealed automatically, let's set it
            trans_dict = self.trans_queue.pop(0)
            src_text = trans_dict['src_text']
            src_language = trans_dict['src_language']
            dest_language = trans_dict['dest_language']

            try:
                if src_language == 'auto' and src_text != '':
                    src_language = str(self.translator.detect(src_text).lang)

                # If the two languages are the same, nothing is done
                if src_language != dest_language:
                    dest_text = ''
                    # THIS IS WHERE THE TRANSLATION HAPPENS. The try is necessary to circumvent a bug of the used API
                    if src_text != '':
                        dest_text = self.translator.translate(
                            src_text,
                            src=src_language,
                            dest=dest_language
                        ).text
                    else:
                        pass
                    if src_text in self.translations:
                        self.translations[src_text] = dest_text
                else:
                    self.translations[src_text] = src_text
            except Exception:
                self.translations[src_text] = '_error_'
                return

if __name__ == "__main__":
    DBusGMainLoop(set_as_default=True)
    TranslateService()
    GLib.MainLoop().run()
