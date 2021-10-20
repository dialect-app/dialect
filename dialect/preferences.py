# Copyright 2020-2021 Mufeed Ali
# Copyright 2020-2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import re
import threading
from gettext import gettext as _

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from dialect.define import RES_PATH
from dialect.settings import Settings
from dialect.translators import TRANSLATORS
from dialect.tts import TTS


@Gtk.Template(resource_path=f'{RES_PATH}/preferences.ui')
class DialectPreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'DialectPreferencesWindow'

    parent = NotImplemented

    # Get preferences widgets
    appearance = Gtk.Template.Child()
    dark_mode = Gtk.Template.Child()
    live_translation = Gtk.Template.Child()
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

        # Show dark mode preference
        self.style_manager = self.parent.app.get_style_manager()
        if not self.style_manager.get_system_supports_color_schemes():
            self.appearance.set_visible(True)

        # Setup backends combo row
        self.backend_model = Gio.ListStore.new(BackendObject)
        backend_options = [
            BackendObject(translator.name, translator.prettyname) for translator in TRANSLATORS.values()
        ]
        selected_backend_index = 0
        for index, value in enumerate(backend_options):
            self.backend_model.insert(index, value)
            if value.name == Settings.get().backend:
                selected_backend_index = index
        self.backend.set_model(self.backend_model)

        # Bind preferences with GSettings
        Settings.get().bind('dark-mode', self.dark_mode, 'active',
                            Gio.SettingsBindFlags.DEFAULT)
        Settings.get().bind('live-translation', self.live_translation, 'active',
                            Gio.SettingsBindFlags.DEFAULT)
        Settings.get().bind('translate-accel', self.translate_accel,
                            'selected', Gio.SettingsBindFlags.DEFAULT)
        Settings.get().bind('src-auto', self.src_auto, 'active',
                            Gio.SettingsBindFlags.DEFAULT)

        # Setup TTS
        self.tts_row.set_visible(len(TTS) >= 1)
        self.tts.set_active(Settings.get().tts != '')

        # Toggle dark mode
        self.dark_mode.connect('notify::active', self._toggle_dark_mode)

        # Set translate accel sensitivity by live translation state
        self.translate_accel.set_sensitive(not self.live_translation.get_active())
        self.live_translation.connect('notify::active', self._toggle_accel_pref)

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
        self.__check_instance_support()

        self.instance_save_image = Gtk.Image.new_from_icon_name('emblem-ok-symbolic')
        self.backend_instance_save.set_child(self.instance_save_image)
        self.instance_save_spinner = Gtk.Spinner()
        self.instance_save_image.show()
        self.instance_save_spinner.show()

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
        Settings.get().unbind(self.dark_mode, 'active')
        Settings.get().unbind(self.live_translation, 'active')
        Settings.get().unbind(self.src_auto, 'active')

    def _on_settings_changed(self, _settings, key):
        backend = Settings.get().backend
        if key == 'backend-settings':
            if TRANSLATORS[backend].supported_features['change-instance']:
                # Update backend
                Settings.get().reset_src_langs(backend)
                Settings.get().reset_dest_langs(backend)
                self.parent.change_backends(backend)

    def _toggle_dark_mode(self, switch, _active):
        if not self.style_manager.get_system_supports_color_schemes():
            active = switch.get_active()
            if active:
                self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            else:
                self.style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def _toggle_accel_pref(self, switch, _active):
        self.translate_accel.set_sensitive(not switch.get_active())

    def _toggle_tts(self, switch, _active):
        value = ''
        if switch.get_active() and len(TTS) >= 1:
            tts = list(TTS.keys())
            value = str(tts[0])

        self.parent.src_voice_btn.set_sensitive(False)
        self.parent.src_voice_btn.set_visible(switch.get_active())
        self.parent.dest_voice_btn.set_sensitive(False)
        self.parent.dest_voice_btn.set_visible(switch.get_active())

        Settings.get().tts = value

        if switch.get_active():
            threading.Thread(
                target=self.parent.load_lang_speech,
                daemon=True
            ).start()

    def _switch_backends(self, row, _value):
        backend = self.backend_model[row.get_selected()].name
        Settings.get().backend = backend
        self.__check_instance_support()
        self.parent.change_backends(backend)

    def _on_backend_loading(self, window, _value):
        self.backend.set_sensitive(not window.get_property('backend-loading'))
        self.backend_instance_row.set_sensitive(not window.get_property('backend-loading'))

    def _on_edit_backend_instance(self, _button):
        backend = Settings.get().backend
        self.backend_instance_stack.set_visible_child_name('edit')
        self.backend_instance.set_text(Settings.get().get_instance_url(backend))

    def _on_save_backend_instance(self, _button):
        backend = Settings.get().backend
        old_value = Settings.get().get_instance_url(backend)
        new_value = self.backend_instance.get_text()

        url = re.compile(r"https?://(www\.)?")
        new_value = url.sub('', new_value).strip().strip('/')

        if new_value != old_value:
            # Validate
            threading.Thread(
                target=self.__validate_new_backend_instance,
                args=[new_value],
                daemon=True
            ).start()
        else:
            self.backend_instance_stack.set_visible_child_name('view')

    def _on_reset_backend_instance(self, _button):
        backend = Settings.get().backend
        Settings.get().reset_instance_url(backend)
        self.backend_instance_stack.set_visible_child_name('view')
        Gtk.StyleContext.remove_class(self.backend_instance.get_style_context(), 'error')
        self.error_popover.popdown()

    def __check_instance_support(self):
        backend = Settings.get().backend
        if TRANSLATORS[backend].supported_features['change-instance']:
            self.backend_instance_row.set_visible(True)
            self.backend_instance_label.set_label(Settings.get().get_instance_url(backend))
        else:
            self.backend_instance_row.set_visible(False)

    def __validate_new_backend_instance(self, url):
        def spinner_start():
            self.backend.set_sensitive(False)
            self.backend_instance_row.set_sensitive(False)
            self.backend_instance_save.remove(self.instance_save_image)
            self.backend_instance_save.add(self.instance_save_spinner)
            self.instance_save_spinner.start()

        def spinner_end():
            self.backend.set_sensitive(True)
            self.backend_instance_row.set_sensitive(True)
            self.backend_instance_save.remove(self.instance_save_spinner)
            self.backend_instance_save.add(self.instance_save_image)
            self.backend_instance_label.set_label(Settings.get().get_instance_url(backend))
            self.instance_save_spinner.stop()

        GLib.idle_add(spinner_start)
        backend = Settings.get().backend
        validate = TRANSLATORS[backend].validate_instance_url(url)
        if validate:
            Settings.get().set_instance_url(backend, url)
            GLib.idle_add(Gtk.StyleContext.remove_class, self.backend_instance.get_style_context(), 'error')
            GLib.idle_add(self.backend_instance_stack.set_visible_child_name, 'view')
            GLib.idle_add(self.error_popover.popdown)
        else:
            GLib.idle_add(Gtk.StyleContext.add_class, self.backend_instance.get_style_context(), 'error')
            error_text = _('Not a valid {backend} instance')
            error_text = error_text.format(backend=TRANSLATORS[backend].prettyname)
            GLib.idle_add(self.error_label.set_label, error_text)
            GLib.idle_add(self.error_popover.popup)

        GLib.idle_add(spinner_end)


class BackendObject(GObject.Object):
    __gtype_name__ = 'BackendObject'

    name = GObject.Property(type=str)
    prettyname = GObject.Property(type=str)

    def __init__(self, name, prettyname):
        super().__init__()

        self.set_property('name', name)
        self.set_property('prettyname', prettyname)
