# Copyright 2020-2022 Mufeed Ali
# Copyright 2020-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from gi.repository import Adw, Gio, Gtk

from dialect.define import RES_PATH
from dialect.settings import Settings
from dialect.providers import ProvidersListModel, TTS
from dialect.widgets import ProvidersList


@Gtk.Template(resource_path=f'{RES_PATH}/preferences.ui')
class DialectPreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'DialectPreferencesWindow'

    parent = NotImplemented

    # Child widgets
    live_translation = Gtk.Template.Child()
    sp_translation = Gtk.Template.Child()
    translate_accel = Gtk.Template.Child()
    src_auto = Gtk.Template.Child()
    translator = Gtk.Template.Child()
    tts = Gtk.Template.Child()
    search_provider = Gtk.Template.Child()
    providers: ProvidersList = Gtk.Template.Child()

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent

        # Bind preferences with GSettings
        Settings.get().bind('live-translation', self.live_translation, 'enable-expansion',
                            Gio.SettingsBindFlags.DEFAULT)
        Settings.get().bind('sp-translation', self.sp_translation, 'active',
                            Gio.SettingsBindFlags.DEFAULT)
        Settings.get().bind('translate-accel', self.translate_accel,
                            'selected', Gio.SettingsBindFlags.DEFAULT)
        Settings.get().bind('src-auto', self.src_auto, 'active',
                            Gio.SettingsBindFlags.DEFAULT)

        # Setup translator chooser
        trans_model = ProvidersListModel('translators')
        with self.translator.freeze_notify():
            self.translator.set_model(trans_model)
            self.translator.props.selected = trans_model.get_index_by_name(Settings.get().active_translator)

        # Setup TTS chooser
        if (len(TTS) >= 1):
            tts_model = ProvidersListModel('tts', True)
            with self.tts.freeze_notify():
                self.tts.set_model(tts_model)
                self.tts.props.selected = tts_model.get_index_by_name(Settings.get().active_tts)
        else:
            self.tts.props.visible = False

        # Providers Settings
        providers_model = ProvidersListModel()
        self.providers.bind_model(providers_model)

        # Translator loading
        self.parent.connect('notify::translator-loading', self._on_translator_loading)

        # Search Provider
        if os.getenv('XDG_CURRENT_DESKTOP') != 'GNOME':
            self.search_provider.hide()

    @Gtk.Template.Callback()
    def is_not_true(self, _widget, boolean):
        """ Check if boolean is not true
            template binding closure function
        """
        return not boolean

    @Gtk.Template.Callback()
    def _switch_translator(self, row, _value):
        """ Called on self.translator::notify::selected signal """
        provider = self.translator.get_selected_item().name
        if provider != Settings.get().active_translator:
            self.parent.save_settings()
            Settings.get().active_translator = provider
            self.parent.reload_translator()

    @Gtk.Template.Callback()
    def _switch_tts(self, row, _value):
        """ Called on self.tts::notify::selected signal """
        provider = self.tts.get_selected_item().name
        if provider != Settings.get().active_tts:
            Settings.get().active_tts = provider
            self.parent.load_tts()

    def _on_translator_loading(self, window, _value):
        self.translator.props.sensitive = not window.translator_loading
        self.tts.props.sensitive = not window.translator_loading
