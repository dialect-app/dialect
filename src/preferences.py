# Copyright 2020-2021 Mufeed Ali
# Copyright 2020-2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from gi.repository import Gio, Gtk, Handy

from dialect.define import RES_PATH


@Gtk.Template(resource_path=f'{RES_PATH}/preferences.ui')
class DialectPreferencesWindow(Handy.PreferencesWindow):
    __gtype_name__ = 'DialectPreferencesWindow'

    parent = NotImplemented
    settings = NotImplemented

    # Get preferences widgets
    dark_mode = Gtk.Template.Child()
    live_translation = Gtk.Template.Child()
    translate_accel = Gtk.Template.Child()
    backend = Gtk.Template.Child()
    search_provider = Gtk.Template.Child()

    def __init__(self, parent, settings, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        # Get GSettings object
        self.settings = settings

        self.setup()

    def setup(self):
        # Disable search, we have few preferences
        self.set_search_enabled(False)

        # Setup translate accel combo row
        model = Gio.ListStore.new(Handy.ValueObject)
        options = ['Ctrl + Enter', 'Enter']
        for count, value in enumerate(options):
            model.insert(count, Handy.ValueObject.new(value))
        self.translate_accel.bind_name_model(model,
                                             Handy.ValueObject.dup_string)

        # Setup backends combo row
        model = Gio.ListStore.new(Handy.ValueObject)
        options = ['Google Translate', 'LibreTranslate']
        for count, value in enumerate(options):
            model.insert(count, Handy.ValueObject.new(value))
        self.backend.bind_name_model(model,
                                     Handy.ValueObject.dup_string)

        # Bind preferences with GSettings
        self.settings.bind('dark-mode', self.dark_mode, 'active',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('live-translation', self.live_translation, 'active',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('translate-accel', self.translate_accel,
                           'selected-index', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('backend', self.backend,
                           'selected-index', Gio.SettingsBindFlags.DEFAULT)

        # Toggle dark mode
        self.dark_mode.connect('notify::active', self._toggle_dark_mode)

        # Set translate accel sensitivity by live translation state
        self.translate_accel.set_sensitive(not self.live_translation.get_active())
        self.live_translation.connect('notify::active', self._toggle_accel_pref)

        # Switch backends
        self.backend.connect('notify::selected-index', self._switch_backends)
        self.parent.connect('notify::backend-loading', self._on_backend_loading)

        # Search Provider
        if os.getenv('XDG_CURRENT_DESKTOP') != 'GNOME':
            self.search_provider.hide()

    def _toggle_dark_mode(self, switch, _active):
        gtk_settings = Gtk.Settings.get_default()
        active = switch.get_active()
        gtk_settings.set_property('gtk-application-prefer-dark-theme', active)

    def _toggle_accel_pref(self, switch, _active):
        self.translate_accel.set_sensitive(not switch.get_active())

    def _switch_backends(self, row, _value):
        value = row.get_selected_index()
        self.parent._change_backends(value)

    def _on_backend_loading(self, window, _value):
        self.backend.set_sensitive(not window.get_property('backend-loading'))
