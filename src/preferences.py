# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gio, Gtk, Handy

from dialect.define import APP_ID, RES_PATH

@Gtk.Template(resource_path=f'{RES_PATH}/preferences.ui')
class DialectPreferencesWindow(Handy.PreferencesWindow):
    __gtype_name__ = 'DialectPreferencesWindow'

    # Get preferences widgets
    dark_mode = Gtk.Template.Child()
    live_translation = Gtk.Template.Child()
    translate_accel = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Get GSettings object
        self.settings = Gio.Settings.new(APP_ID)

        self.setup()

    def setup(self):
        # Disable search, we have few preferences
        self.set_search_enabled(False)

        # Setup translate accel combo row
        model = Gio.ListStore.new(Handy.ValueObject)
        options = ['Ctrl + Enter', 'Enter']
        for i, o in enumerate(options):
            model.insert(i, Handy.ValueObject.new(o))
        self.translate_accel.bind_name_model(model,
                                             Handy.ValueObject.dup_string)

        # Bind preferences with GSettings
        self.settings.bind('dark-mode', self.dark_mode, 'active',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('live-translation', self.live_translation, 'active',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('translate-accel', self.translate_accel,
                           'selected-index', Gio.SettingsBindFlags.DEFAULT)

        # Toggle dark mode
        self.dark_mode.connect('notify::active', self._toggle_dark_mode)

        # Set translate accel sensitivity by live translation state
        self.translate_accel.set_sensitive(
            not self.live_translation.get_active())
        self.live_translation.connect('notify::active', self._toggle_accel_pref)

    def _toggle_dark_mode(self, switch, active):
        gtk_settings = Gtk.Settings.get_default()
        active = switch.get_active()
        gtk_settings.set_property('gtk-application-prefer-dark-theme', active)

    def _toggle_accel_pref(self, switch, active):
        self.translate_accel.set_sensitive(not switch.get_active())
