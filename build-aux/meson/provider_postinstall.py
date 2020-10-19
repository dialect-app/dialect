#!/usr/bin/python3

from time import sleep
from gi.repository import Gio, GLib

APP_ID = 'com.github.gi_lom.dialect'
APP_DESKTOP = APP_ID + '.desktop'

sleep(1)

settings = Gio.Settings.new('org.gnome.desktop.search-providers')
disabled_providers = list(settings.get_value('disabled'))

if (APP_DESKTOP) not in disabled_providers:
    disabled_providers.append(APP_DESKTOP)
    settings.set_value('disabled', GLib.Variant('as', disabled_providers))
    settings.apply()
