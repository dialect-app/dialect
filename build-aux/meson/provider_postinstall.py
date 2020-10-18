#!/usr/bin/python3

from gi.repository import Gio, GLib

APP_ID = 'com.github.gi_lom.dialect'
APP_DESKTOP = APP_ID + '.desktop'

settings = Gio.Settings.new('org.gnome.desktop.search-providers')
disabled_providers = list(settings.get_value('disabled'))

if (APP_DESKTOP) not in disabled_providers:
    disabled_providers.append(APP_DESKTOP)
    settings.set_value('disabled', GLib.Variant('as', disabled_providers))
    settings.apply()

# APP_ID = 'com.github.gi_lom.dialect'
# user = environ.get('SUDO_USER')
# subprocess_args = ['sudo', '-u', user, 'dconf', 'read', '/org/gnome/desktop/search-providers/disabled']
# disabled_providers = check_output(subprocess_args, universal_newlines=True).strip()
# print(disabled_providers[:-1])

# if (APP_ID + '.desktop') not in disabled_providers:
#     print('Not in')
# else:
#     pass
