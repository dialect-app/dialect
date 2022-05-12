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
    backend_instance = Gtk.Template.Child()
    backend_instance_row = Gtk.Template.Child()
    backend_instance_stack = Gtk.Template.Child()
    backend_instance_label = Gtk.Template.Child()
    backend_instance_edit = Gtk.Template.Child()
    backend_instance_save = Gtk.Template.Child()
    backend_instance_reset = Gtk.Template.Child()
    backend_instance_edit_box = Gtk.Template.Child()
    api_key = Gtk.Template.Child()
    api_key_row = Gtk.Template.Child()
    api_key_stack = Gtk.Template.Child()
    api_key_label = Gtk.Template.Child()
    api_key_edit = Gtk.Template.Child()
    api_key_save = Gtk.Template.Child()
    api_key_reset = Gtk.Template.Child()
    api_key_edit_box = Gtk.Template.Child()
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

        # Change translator instance
        Settings.get().connect('changed', self._on_settings_changed)
        self.backend_instance_edit.connect('clicked', self._on_edit_backend_instance)
        self.backend_instance_save.connect('clicked', self._on_save_backend_instance)
        self.backend_instance_reset.connect('clicked', self._on_reset_backend_instance)

        self.api_key_edit.connect('clicked', self._on_edit_api_key)
        self.api_key_save.connect('clicked', self._on_save_api_key)
        self.api_key_reset.connect('clicked', self._on_reset_api_key)

        self.__check_instance_or_api_key_support()

        self.instance_save_image = Gtk.Image.new_from_icon_name('emblem-ok-symbolic')
        self.backend_instance_save.set_child(self.instance_save_image)
        self.instance_save_spinner = Gtk.Spinner()

        self.api_key_save_image = Gtk.Image.new_from_icon_name('emblem-ok-symbolic')
        self.api_key_save.set_child(self.api_key_save_image)
        self.api_key_save_spinner = Gtk.Spinner()

        self.error_popover = Gtk.Popover(
            pointing_to=self.backend_instance.get_allocation(),
            can_focus=False,
        )
        self.error_label = Gtk.Label(label='Not a valid instance')
        error_icon = Gtk.Image.new_from_icon_name('dialog-error-symbolic')
        error_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            margin_start=8,
            margin_end=8,
            margin_top=8,
            margin_bottom=8,
            spacing=8
        )
        error_box.prepend(error_icon)
        error_box.prepend(self.error_label)
        self.error_popover.set_child(error_box)
        self.error_popover.set_position(Gtk.PositionType.BOTTOM)
        self.error_popover.hide()

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
        self.backend_instance_row.set_sensitive(not window.get_property('backend-loading'))
        self.api_key_row.set_sensitive(not window.get_property('backend-loading'))

        # Show or hide api key entry
        if not window.get_property('backend-loading') and window.translator:
            if window.translator.supported_features['api-key-supported']:
                self.api_key_row.set_visible(True)
                self.api_key_label.set_label(Settings.get().api_key or 'None')
            else:
                self.api_key_row.set_visible(False)

    def _on_edit_backend_instance(self, _button):
        self.backend_instance_stack.set_visible_child_name('edit')
        self.backend_instance.set_text(Settings.get().instance_url)

    def _on_save_backend_instance(self, _button):
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
                self.backend_instance.get_style_context().remove_class('error')
                self.backend_instance_stack.set_visible_child_name('view')
                # self.error_popover.popdown()
            else:
                self.backend_instance.get_style_context().add_class('error')
                error_text = _('Not a valid {backend} instance')
                error_text = error_text.format(backend=TRANSLATORS[backend].prettyname)
                self.error_label.set_label(error_text)
                # self.error_popover.popup()
                self.api_key_row.set_visible(False)
                self.api_key_label.set_label('None')

            self.backend.set_sensitive(True)
            self.backend_instance_row.set_sensitive(True)
            self.api_key_row.set_sensitive(True)
            self.backend_instance_save.set_child(self.instance_save_image)
            self.backend_instance_label.set_label(Settings.get().instance_url)
            self.instance_save_spinner.stop()

        old_value = Settings.get().instance_url
        new_value = self.backend_instance.get_text()

        url = re.compile(r'https?://(www\.)?')
        self.new_instance_url = url.sub('', new_value).strip().strip('/')

        # Validate
        if self.new_instance_url != old_value:
            # Progress feedback
            self.backend.set_sensitive(False)
            self.backend_instance_row.set_sensitive(False)
            self.api_key_row.set_sensitive(False)
            self.backend_instance_save.set_child(self.instance_save_spinner)
            self.instance_save_spinner.start()

            backend = Settings.get().active_translator
            validation_url = TRANSLATORS[backend].format_url(
                self.new_instance_url,
                TRANSLATORS[backend].validation_path
            )
            validation_message = Soup.Message.new('GET', validation_url)

            Session.get().send_and_read_async(validation_message, 0, None, on_validation_response)
        else:
            self.backend_instance_stack.set_visible_child_name('view')

    def _on_reset_backend_instance(self, _button):
        Settings.get().reset_instance_url()
        Settings.get().reset_api_key()
        self.backend_instance_label.set_label(Settings.get().instance_url)
        self.backend_instance_stack.set_visible_child_name('view')
        self.backend_instance.get_style_context().remove_class('error')
        self.error_popover.popdown()

    def _on_edit_api_key(self, _button):
        self.api_key_stack.set_visible_child_name('edit')
        self.api_key.set_text(Settings.get().api_key)

    def _on_save_api_key(self, _button):
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
                self.api_key.get_style_context().remove_class('error')
                self.api_key_stack.set_visible_child_name('view')
            else:
                self.api_key.get_style_context().add_class('error')
                error_text = _('Not a valid {backend} API key')
                error_text = error_text.format(backend=TRANSLATORS[backend].prettyname)
                self.error_label.set_label(error_text)

            self.backend.set_sensitive(True)
            self.backend_instance_row.set_sensitive(True)
            self.api_key_row.set_sensitive(True)
            self.api_key_save.set_child(self.api_key_save_image)
            self.api_key_label.set_label(Settings.get().api_key or 'None')
            self.instance_save_spinner.stop()

        old_value = Settings.get().api_key
        self.new_api_key = self.api_key.get_text()

        if self.new_api_key != old_value:
            # Progress feedback
            self.backend.set_sensitive(False)
            self.backend_instance_row.set_sensitive(False)
            self.api_key_row.set_sensitive(False)
            self.api_key_save.set_child(self.api_key_save_spinner)
            self.api_key_save_spinner.start()

            backend = Settings.get().active_translator
            validation_url = TRANSLATORS[backend].format_url(
                Settings.get().instance_url,
                TRANSLATORS[backend].api_test_path
            )
            (data, headers) = TRANSLATORS[backend].format_api_key_test(self.new_api_key)
            message = Session.create_message('POST', validation_url, data, headers)

            Session.get().send_and_read_async(message, 0, None, on_response)
        else:
            self.api_key_stack.set_visible_child_name('view')

    def _on_reset_api_key(self, _button):
        Settings.get().reset_api_key()
        self.api_key_label.set_label(Settings.get().api_key or 'None')
        self.api_key_stack.set_visible_child_name('view')
        self.api_key.get_style_context().remove_class('error')
        self.error_popover.popdown()

    def __check_instance_or_api_key_support(self):
        backend = Settings.get().active_translator
        if TRANSLATORS[backend].supported_features['change-instance']:
            self.backend_instance_row.set_visible(True)
            self.backend_instance_label.set_label(Settings.get().instance_url)
        else:
            self.backend_instance_row.set_visible(False)

        if TRANSLATORS[backend].supported_features['api-key-supported']:
            self.api_key_row.set_visible(True)
            self.api_key_label.set_label(Settings.get().api_key or 'None')
        else:
            self.api_key_row.set_visible(False)


class BackendObject(GObject.Object):
    __gtype_name__ = 'BackendObject'

    name = GObject.Property(type=str)
    prettyname = GObject.Property(type=str)

    def __init__(self, name, prettyname):
        super().__init__()

        self.set_property('name', name)
        self.set_property('prettyname', prettyname)
