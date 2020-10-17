#!/usr/bin/python3
# Copyright 2020 gi-lom
# Copyright 2020 Nikita Kravets
# SPDX-License-Identifier: GPL-3.0-or-later

import dbus
import dbus.service

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

search_bus_name = "org.gnome.Shell.SearchProvider2"
sbn = dict(dbus_interface=search_bus_name)

class TranslateService(dbus.service.Object):
    bus_name = 'com.github.gi_lom.dialect.SearchProvider'
    _object_path = '/' + bus_name.replace('.', '/')

    def __init__(self):
        self.session_bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(self.bus_name, bus=self.session_bus)
        dbus.service.Object.__init__(self, bus_name, self._object_path)

        # running translations
        self.translations = dict()

    @dbus.service.method(in_signature='as', out_signature='as', **sbn)
    def GetInitialResultSet(self, terms):
        text = ' '.join(terms)
        self.translation(text)
        return [text]

    @dbus.service.method(in_signature='as', out_signature='aa{sv}', **sbn)
    def GetResultMetas(self, ids):
        translate_id = ids[0]

        if translate_id in self.translations:
            while self.translations[translate_id] == '':
                pass
        else:
            return [dict()for id in ids]

        name = self.translations[translate_id]
        self.translations.pop(name) #########################

        return [
            dict(
                id=id,
                name=name,
                gicon='com.github.gi_lom.dialect',
            )
            for id in ids
        ]

    @dbus.service.method(in_signature='asas', out_signature='as', **sbn)
    def GetSubsearchResultSet(self, previous_results, new_terms):
        text = ' '.join(new_terms)
        self.translation(text)
        return [text]

    @dbus.service.method(in_signature='sasu', **sbn)
    def ActivateResult(self, id, terms, timestamp):
        pass

    @dbus.service.method(in_signature='asu', terms='as', timestamp='u', **sbn)
    def LaunchSearch(self, terms, timestamp):
        pass

    def translation(self, text):
        pass

    def run_translation(self, text):
        pass
