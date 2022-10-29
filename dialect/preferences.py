# Copyright 2020-2022 Mufeed Ali
# Copyright 2020-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import threading

from gi.repository import Adw, Gio, Gtk

from dialect.define import RES_PATH
from dialect.settings import Settings
from dialect.providers import ProvidersListModel, TTS
from dialect.widgets import ProvidersList


@Gtk.Template(resource_path=f'{RES_PATH}/preferences.ui')
class DialectPreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'DialectPreferencesWindow'

    parent = NotImplemented

    # Get preferences widgets
    live_translation = Gtk.Template.Child()
    sp_translation = Gtk.Template.Child()
    translate_accel = Gtk.Template.Child()
    src_auto = Gtk.Template.Child()
    backend = Gtk.Template.Child()
    tts = Gtk.Template.Child()
    search_provider = Gtk.Template.Child()
    providers: ProvidersList = Gtk.Template.Child()

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent

        self.setup()

    def setup(self):
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
        self.backend.set_model(trans_model)
        self.backend.props.selected = trans_model.get_index_by_name(Settings.get().active_translator)
        self.backend.connect('notify::selected', self._switch_backends)

        # Setup TTS chooser
        if (len(TTS) >= 1):
            tts_model = ProvidersListModel('tts', True)
            self.tts.set_model(tts_model)
            self.tts.props.selected = tts_model.get_index_by_name(Settings.get().active_tts)
            self.tts.connect('notify::selected', self._switch_tts)
        else:
            self.tts.props.visible = False

        # Providers Settings
        providers_model = ProvidersListModel()
        self.providers.bind_model(providers_model)

        # Translator loading
        self.parent.connect('notify::backend-loading', self._on_backend_loading)

        # Search Provider
        if os.getenv('XDG_CURRENT_DESKTOP') != 'GNOME':
            self.search_provider.hide()

    @Gtk.Template.Callback()
    def is_not_true(self, _widget, boolean):
        return not boolean

    def _unbind_settings(self, *args, **kwargs):
        Settings.get().unbind(self.live_translation, 'active')
        Settings.get().unbind(self.src_auto, 'active')

    def _toggle_tts(self, switch, _active):
        value = ''
        active = switch.props.active

        if active and len(TTS) >= 1:
            tts = list(TTS.keys())
            value = str(tts[0])

        self.parent.src_voice_btn.props.sensitive = False
        self.parent.src_voice_btn.props.visible = active
        self.parent.dest_voice_btn.props.sensitive = False
        self.parent.dest_voice_btn.props.visible = active

        Settings.get().active_tts = value

        if active:
            threading.Thread(
                target=self.parent.load_lang_speech,
                daemon=True
            ).start()

    def _switch_backends(self, row, _value):
        self.parent.save_settings()
        backend = self.backend.get_selected_item().name
        Settings.get().active_translator = backend
        self.parent.reload_backends()

    def _switch_tts(self, row, _value):
        provider = self.tts.get_selected_item().name
        Settings.get().active_tts = provider

        self.parent.load_tts()

    def _on_backend_loading(self, window, _value):
        self.backend.props.sensitive = not window.backend_loading
        self.tts.props.sensitive = not window.backend_loading
