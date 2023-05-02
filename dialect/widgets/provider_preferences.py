# Copyright 2023 Mufeed Ali
# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import re
from gettext import gettext as _

from gi.repository import Adw, GObject, Gtk

from dialect.define import RES_PATH
from dialect.session import Session
from dialect.settings import Settings


@Gtk.Template(resource_path=f"{RES_PATH}/provider-preferences.ui")
class ProviderPreferences(Gtk.Box):
    __gtype_name__ = "ProviderPreferences"

    # Properties
    translation = GObject.Property(type=bool, default=False)
    tts = GObject.Property(type=bool, default=False)
    definitions = GObject.Property(type=bool, default=False)

    # Child widgets
    title = Gtk.Template.Child()
    page = Gtk.Template.Child()
    instance_entry = Gtk.Template.Child()
    instance_stack = Gtk.Template.Child()
    instance_reset = Gtk.Template.Child()
    instance_spinner = Gtk.Template.Child()
    api_key_entry = Gtk.Template.Child()
    api_key_stack = Gtk.Template.Child()
    api_key_reset = Gtk.Template.Child()
    api_key_spinner = Gtk.Template.Child()

    def __init__(self, providers, scope, **kwargs):
        super().__init__(**kwargs)
        self.providers = providers
        self.scope = scope
        self.provider = providers[scope]
        self.settings = Settings.get().get_translator_settings(self.provider.name)

        self.title.props.subtitle = self.provider.prettyname

        self.translation = self.provider.translation
        self.tts = self.provider.tts
        self.definitions = self.provider.definitions

        # Check what entries to show
        self._check_settings()

        # Load saved values
        self.instance_entry.props.text = self.settings.get_string("instance-url")
        self.api_key_entry.props.text = self.settings.get_string("api-key")

    @Gtk.Template.Callback()
    def _on_parent(self, _view, _pspec):
        # Main window progress
        if self.props.parent is not None:
            self.get_root().parent.connect("notify::translator-loading", self._on_translator_loading)

    def _check_settings(self):
        self.instance_entry.props.visible = self.provider.change_instance
        self.api_key_entry.props.visible = self.provider.api_key_supported

    @Gtk.Template.Callback()
    def _on_back(self, _button):
        """Called on self.back_btn::clicked signal"""
        self.get_root().close_subpage()

    @Gtk.Template.Callback()
    def _on_instance_apply(self, _row):
        """Called on self.instance_entry::apply signal"""

        def on_validation_response(session, result):
            valid = False
            try:
                data = Session.get_response(session, result)
                valid = self.provider.validate_instance(data)
            except Exception as exc:
                logging.error(exc)

            if valid:
                self.settings.instance_url = self.new_instance_url
                self.instance_entry.remove_css_class("error")
                self.instance_entry.props.text = self.settings.instance_url
            else:
                self.instance_entry.add_css_class("error")
                error_text = _("Not a valid {provider} instance")
                error_text = error_text.format(provider=self.provider.prettyname)
                toast = Adw.Toast.new(error_text)
                self.get_root().add_toast(toast)

            self.instance_entry.props.sensitive = True
            self.api_key_entry.props.sensitive = True
            self.instance_stack.props.visible_child_name = "reset"
            self.instance_spinner.stop()

        old_value = self.settings.instance_url
        new_value = self.instance_entry.props.text

        url = re.compile(r"https?://(www\.)?")
        self.new_instance_url = url.sub("", new_value).strip().strip("/")

        # Validate
        if self.new_instance_url != old_value:
            # Progress feedback
            self.instance_entry.props.sensitive = False
            self.api_key_entry.props.sensitive = False
            self.instance_stack.props.visible_child_name = "spinner"
            self.instance_spinner.start()

            validation = self.provider.format_validate_instance(self.new_instance_url)
            Session.get().send_and_read_async(validation, 0, None, on_validation_response)
        else:
            self.instance_entry.remove_css_class("error")

    @Gtk.Template.Callback()
    def _on_instance_changed(self, _entry, _pspec):
        """Called on self.instance_entry::notify::text signal"""
        if self.instance_entry.props.text == self.settings.instance_url:
            self.instance_entry.props.show_apply_button = False
        elif not self.instance_entry.props.show_apply_button:
            self.instance_entry.props.show_apply_button = True

    @Gtk.Template.Callback()
    def _on_reset_instance(self, _button):
        """Called on self.instance_reset::clicked signal"""
        if self.settings.instance_url != self.provider.defaults["instance_url"]:
            self.instance_stack.props.visible_child_name = "spinner"
            self.instance_spinner.start()
            self.settings.instance_url = self.provider.defaults["instance_url"]

        self.instance_entry.remove_css_class("error")
        self.instance_entry.props.text = self.settings.instance_url

    @Gtk.Template.Callback()
    def _on_api_key_apply(self, _row):
        """Called on self.api_key_entry::apply signal"""

        def on_validation_response(session, result):
            valid = False
            try:
                data = Session.get_response(session, result)
                self.provider.validate_api_key(data)
                valid = True
            except Exception as exc:
                logging.error(exc)

            if valid:
                self.settings.api_key = self.new_api_key
                self.api_key_entry.remove_css_class("error")
                self.api_key_entry.props.text = self.settings.api_key
            else:
                self.api_key_entry.add_css_class("error")
                error_text = _("Not a valid {provider} API key")
                error_text = error_text.format(provider=self.provider.prettyname)
                toast = Adw.Toast.new(error_text)
                self.get_root().add_toast(toast)

            self.instance_entry.props.sensitive = True
            self.api_key_entry.props.sensitive = True
            self.api_key_stack.props.visible_child_name = "reset"
            self.api_key_spinner.stop()

        old_value = self.settings.api_key
        self.new_api_key = self.api_key_entry.get_text()

        # Validate
        if self.new_api_key != old_value:
            # Progress feedback
            self.instance_entry.props.sensitive = False
            self.api_key_entry.props.sensitive = False
            self.api_key_stack.props.visible_child_name = "spinner"
            self.api_key_spinner.start()

            validation = self.provider.format_validate_api_key(self.new_api_key)
            Session.get().send_and_read_async(validation, 0, None, on_validation_response)
        else:
            self.api_key_entry.remove_css_class("error")

    @Gtk.Template.Callback()
    def _on_reset_api_key(self, _button):
        """Called on self.api_key_reset::clicked signal"""
        if self.settings.api_key != self.provider.defaults["api_key"]:
            self.api_key_stack.props.visible_child_name = "spinner"
            self.api_key_spinner.start()
            self.settings.api_key = self.provider.defaults["api_key"]
        self.api_key_entry.props.text = self.settings.api_key

    def _on_translator_loading(self, window, _value):
        self.page.props.sensitive = not window.translator_loading

        if not window.translator_loading:
            self.instance_stack.props.visible_child_name = "reset"
            self.instance_spinner.stop()
            self.api_key_stack.props.visible_child_name = "reset"
            self.api_key_spinner.stop()

            self.provider = self.providers[self.scope]
            self._check_settings()
