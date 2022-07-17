# Copyright 2020-2022 Mufeed Ali
# Copyright 2020-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import re
import threading
from gettext import gettext as _

from gi.repository import Adw, Gio, GObject, Gtk, Soup

from dialect.define import RES_PATH
from dialect.session import Session
from dialect.settings import Settings
from dialect.translators import TRANSLATORS
from dialect.tts import TTS


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
    instance_entry = Gtk.Template.Child()
    instance_stack = Gtk.Template.Child()
    instance_reset = Gtk.Template.Child()
    instance_spinner = Gtk.Template.Child()
    api_key_entry = Gtk.Template.Child()
    api_key_stack = Gtk.Template.Child()
    api_key_reset = Gtk.Template.Child()
    api_key_spinner = Gtk.Template.Child()
    tts = Gtk.Template.Child()
    tts_row = Gtk.Template.Child()
    search_provider = Gtk.Template.Child()

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent

        self.setup()

    def setup(self):
        # Disable search, we have few preferences
        self.set_search_enabled(False)

        # Setup backends combo row
        self.backend_model = Gio.ListStore.new(BackendObject)
        backend_options = [
            BackendObject(translator.name, translator.prettyname) for translator in TRANSLATORS.values()
        ]
        selected_backend_index = 0
        for index, value in enumerate(backend_options):
            self.backend_model.insert(index, value)
            if value.name == Settings.get().active_translator:
                selected_backend_index = index
        self.backend.set_model(self.backend_model)

        # Bind preferences with GSettings
        Settings.get().bind('live-translation', self.live_translation, 'enable-expansion',
                            Gio.SettingsBindFlags.DEFAULT)
        Settings.get().bind('sp-translation', self.sp_translation, 'active',
                            Gio.SettingsBindFlags.DEFAULT)
        Settings.get().bind('translate-accel', self.translate_accel,
                            'selected', Gio.SettingsBindFlags.DEFAULT)
        Settings.get().bind('src-auto', self.src_auto, 'active',
                            Gio.SettingsBindFlags.DEFAULT)

        # Setup TTS
        self.tts_row.set_visible(len(TTS) >= 1)
        self.tts.set_active(Settings.get().active_tts != '')

        # Set translate accel sensitivity by live translation state
        self.translate_accel.set_sensitive(not self.live_translation.get_enable_expansion())
        self.live_translation.connect('notify::enable-expansion', self._toggle_accel_pref)

        # Switch backends
        self.backend.set_selected(selected_backend_index)
        self.backend.connect('notify::selected', self._switch_backends)
        self.parent.connect('notify::backend-loading', self._on_backend_loading)

        # Toggle TTS
        self.tts.connect('notify::active', self._toggle_tts)

        # Connect to settings changes
        Settings.get().connect('changed', self._on_settings_changed)

        # Instance
        self.instance_entry.connect('apply', self._on_instance_apply)
        self.instance_reset.connect('clicked', self._on_reset_instance)

        # API Key
        self.api_key_entry.connect('apply', self._on_api_key_apply)
        self.api_key_reset.connect('clicked', self._on_reset_api_key)

        self.__check_instance_or_api_key_support()

        # Search Provider
        if os.getenv('XDG_CURRENT_DESKTOP') != 'GNOME':
            self.search_provider.hide()

    def _unbind_settings(self,  *args, **kwargs):
        Settings.get().unbind(self.live_translation, 'active')
        Settings.get().unbind(self.src_auto, 'active')

    def _on_settings_changed(self, _settings, key):
        backend = Settings.get().active_translator
        if key in ('translator-instance-url', 'translator-api-key'):
            # Update backend
            if key == 'translator-instance-url' and TRANSLATORS[backend].supported_features['change-instance']:
                Settings.get().reset_src_langs()
                Settings.get().reset_dest_langs()
            self.parent.reload_backends()

    def _toggle_accel_pref(self, row, _active):
        self.translate_accel.set_sensitive(not row.get_enable_expansion())

    def _toggle_tts(self, switch, _active):
        value = ''
        if switch.get_active() and len(TTS) >= 1:
            tts = list(TTS.keys())
            value = str(tts[0])

        self.parent.src_voice_btn.set_sensitive(False)
        self.parent.src_voice_btn.set_visible(switch.get_active())
        self.parent.dest_voice_btn.set_sensitive(False)
        self.parent.dest_voice_btn.set_visible(switch.get_active())

        Settings.get().active_tts = value

        if switch.get_active():
            threading.Thread(
                target=self.parent.load_lang_speech,
                daemon=True
            ).start()

    def _switch_backends(self, row, _value):
        backend = self.backend_model[row.get_selected()].name
        Settings.get().active_translator = backend
        self.__check_instance_or_api_key_support()
        self.parent.reload_backends()

    def _on_backend_loading(self, window, _value):
        self.backend.set_sensitive(not window.get_property('backend-loading'))
        self.instance_entry.set_sensitive(not window.get_property('backend-loading'))
        self.api_key_entry.set_sensitive(not window.get_property('backend-loading'))

        if not window.get_property('backend-loading'):
            self.instance_stack.set_visible_child_name('reset')
            self.instance_spinner.stop()
            self.api_key_stack.set_visible_child_name('reset')
            self.api_key_spinner.stop()

            # Show or hide api key entry
            if window.translator:
                if window.translator.supported_features['api-key-supported']:
                    self.api_key_entry.set_visible(True)
                    self.api_key_entry.set_text(Settings.get().api_key)
                else:
                    self.api_key_entry.set_visible(False)

    def _on_instance_apply(self, _row):
        def on_validation_response(session, result):
            valid = False
            backend = Settings.get().active_translator
            try:
                data = Session.get_response(session, result)
                valid = TRANSLATORS[backend].validate_instance(data)
            except Exception as exc:
                logging.error(exc)

            if valid:
                Settings.get().instance_url = self.new_instance_url
                self.instance_entry.remove_css_class('error')
                self.instance_entry.set_text(Settings.get().instance_url)
            else:
                self.instance_entry.add_css_class('error')
                error_text = _('Not a valid {backend} instance')
                error_text = error_text.format(backend=TRANSLATORS[backend].prettyname)
                toast = Adw.Toast.new(error_text)
                self.add_toast(toast)
                self.api_key_entry.set_visible(False)
                self.api_key_entry.set_text('')

            self.backend.set_sensitive(True)
            self.instance_entry.set_sensitive(True)
            self.api_key_entry.set_sensitive(True)
            self.instance_stack.set_visible_child_name('reset')
            self.instance_spinner.stop()

        old_value = Settings.get().instance_url
        new_value = self.instance_entry.get_text()

        url = re.compile(r'https?://(www\.)?')
        self.new_instance_url = url.sub('', new_value).strip().strip('/')

        # Validate
        if self.new_instance_url != old_value:
            # Progress feedback
            self.backend.set_sensitive(False)
            self.instance_entry.set_sensitive(False)
            self.api_key_entry.set_sensitive(False)
            self.instance_stack.set_visible_child_name('spinner')
            self.instance_spinner.start()

            backend = Settings.get().active_translator
            validation_url = TRANSLATORS[backend].format_url(
                self.new_instance_url,
                TRANSLATORS[backend].validation_path
            )
            validation_message = Soup.Message.new('GET', validation_url)

            Session.get().send_and_read_async(validation_message, 0, None, on_validation_response)
        else:
            self.instance_entry.remove_css_class('error')

    def _on_reset_instance(self, _button):
        backend = Settings.get().active_translator
        if Settings.get().instance_url != TRANSLATORS[backend].instance_url:
            Settings.get().reset_instance_url()
            Settings.get().reset_api_key()
            self.instance_stack.set_visible_child_name('spinner')
            self.instance_spinner.start()
        self.instance_entry.remove_css_class('error')
        self.instance_entry.set_text(Settings.get().instance_url)

    def _on_api_key_apply(self, _row):
        def on_response(session, result):
            valid = False
            try:
                data = Session.get_response(session, result)
                self.parent.translator.get_translation(data)
                valid = True
            except Exception as exc:
                logging.warning(exc)

            if valid:
                Settings.get().api_key = self.new_api_key
                self.api_key_entry.remove_css_class('error')
                self.api_key_entry.set_text(Settings.get().instance_url)
            else:
                self.api_key_entry.add_css_class('error')
                error_text = _('Not a valid {backend} API key')
                error_text = error_text.format(backend=TRANSLATORS[backend].prettyname)
                toast = Adw.Toast.new(error_text)
                self.add_toast(toast)
                self.api_key_entry.grab_focus()

            self.backend.set_sensitive(True)
            self.instance_entry.set_sensitive(True)
            self.api_key_entry.set_sensitive(True)
            self.api_key_stack.set_visible_child_name('reset')
            self.api_key_spinner.stop()

        old_value = Settings.get().api_key
        self.new_api_key = self.api_key_entry.get_text()

        if self.new_api_key != old_value:
            # Progress feedback
            self.backend.set_sensitive(False)
            self.instance_entry.set_sensitive(False)
            self.api_key_entry.set_sensitive(False)
            self.api_key_stack.set_visible_child_name('spinner')
            self.api_key_spinner.start()

            backend = Settings.get().active_translator
            validation_url = TRANSLATORS[backend].format_url(
                Settings.get().instance_url,
                TRANSLATORS[backend].api_test_path
            )
            (data, headers) = TRANSLATORS[backend].format_api_key_test(self.new_api_key)
            message = Session.create_message('POST', validation_url, data, headers)

            Session.get().send_and_read_async(message, 0, None, on_response)
        else:
            self.api_key_entry.remove_css_class('error')

    def _on_reset_api_key(self, _button):
        backend = Settings.get().active_translator
        if Settings.get().api_key != TRANSLATORS[backend].api_key:
            Settings.get().reset_api_key()
            self.api_key_stack.set_visible_child_name('spinner')
            self.api_key_spinner.start()
        self.api_key_entry.remove_css_class('error')
        self.api_key_entry.set_text(Settings.get().api_key)

    def __check_instance_or_api_key_support(self):
        backend = Settings.get().active_translator
        if TRANSLATORS[backend].supported_features['change-instance']:
            self.instance_entry.set_visible(True)
            self.instance_entry.set_text(Settings.get().instance_url)
        else:
            self.instance_entry.set_visible(False)

        if TRANSLATORS[backend].supported_features['api-key-supported']:
            self.api_key_entry.set_visible(True)
            self.api_key_entry.set_text(Settings.get().api_key)
        else:
            self.api_key_entry.set_visible(False)


class BackendObject(GObject.Object):
    __gtype_name__ = 'BackendObject'

    name = GObject.Property(type=str)
    prettyname = GObject.Property(type=str)

    def __init__(self, name, prettyname):
        super().__init__()

        self.set_property('name', name)
        self.set_property('prettyname', prettyname)
