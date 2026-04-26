# Copyright 2023 Mufeed Ali
# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import re
import typing

from gi.repository import Adw, GObject, Gtk

from dialect.asyncio import background_task
from dialect.define import RES_PATH
from dialect.providers import ProviderCapability, RequestError

if typing.TYPE_CHECKING:
    from dialect.window import DialectWindow


@Gtk.Template(resource_path=f"{RES_PATH}/widgets/provider_preferences.ui")
class ProviderPreferences(Adw.NavigationPage):
    __gtype_name__ = "ProviderPreferences"

    # Properties
    translation: bool = GObject.Property(type=bool, default=False)  # type: ignore
    tts: bool = GObject.Property(type=bool, default=False)  # type: ignore
    definitions: bool = GObject.Property(type=bool, default=False)  # type: ignore

    # Child widgets
    title: Adw.WindowTitle = Gtk.Template.Child()  # type: ignore
    page: Adw.PreferencesPage = Gtk.Template.Child()  # type: ignore
    instance_entry: Adw.EntryRow = Gtk.Template.Child()  # type: ignore
    instance_stack: Gtk.Stack = Gtk.Template.Child()  # type: ignore
    instance_reset: Gtk.Button = Gtk.Template.Child()  # type: ignore
    api_key_entry: Adw.PasswordEntryRow = Gtk.Template.Child()  # type: ignore
    api_key_stack: Gtk.Stack = Gtk.Template.Child()  # type: ignore
    api_key_reset: Gtk.Button = Gtk.Template.Child()  # type: ignore
    api_usage_group: Adw.PreferencesGroup = Gtk.Template.Child()  # type: ignore
    api_usage: Gtk.LevelBar = Gtk.Template.Child()  # type: ignore
    api_usage_label: Gtk.Label = Gtk.Template.Child()  # type: ignore
    advanced_group: Adw.PreferencesGroup = Gtk.Template.Child()  # type: ignore
    model_name_entry: Adw.EntryRow = Gtk.Template.Child()  # type: ignore
    temperature_spin: Adw.SpinRow = Gtk.Template.Child()  # type: ignore
    system_prompt_expander: Adw.ExpanderRow = Gtk.Template.Child()  # type: ignore
    system_prompt_entry: Adw.EntryRow = Gtk.Template.Child()  # type: ignore

    def __init__(self, scope: str, dialog: Adw.PreferencesDialog, window: DialectWindow, **kwargs):
        super().__init__(**kwargs)
        self.scope = scope
        self.provider = window.provider[scope]
        self.dialog = dialog
        self.window = window

        if self.provider:
            self.title.props.subtitle = self.provider.prettyname

            if self.provider.capabilities is not None:
                self.translation = ProviderCapability.TRANSLATION in self.provider.capabilities
                self.tts = ProviderCapability.TTS in self.provider.capabilities
                self.definitions = ProviderCapability.DEFINITIONS in self.provider.capabilities

            # Check what entries to show
            self._check_settings()
            self._check_advanced_options()

            # Load saved values
            self.instance_entry.props.text = self.provider.instance_url
            self.api_key_entry.props.text = self.provider.api_key

        self.temperature_spin.get_adjustment().connect("value-changed", self._on_temperature_changed)

        # Main window progress
        self.window.connect("notify::translator-loading", self._on_translator_loading)

    def _check_settings(self):
        if not self.provider:
            return

        self.instance_entry.props.visible = self.provider.supports_instances
        self.api_key_entry.props.visible = self.provider.supports_api_key

        self.api_usage_group.props.visible = False
        if self.provider.supports_api_usage:
            self._load_api_usage()

    def _check_advanced_options(self):
        """Show OpenAI-compatible advanced settings when applicable."""
        if not self.provider:
            self.advanced_group.props.visible = False
            return

        self.advanced_group.props.visible = self.provider.name == "openai_compatible"
        if self.provider.name != "openai_compatible":
            return

        self.model_name_entry.props.text = self.provider.settings.model_name
        self.temperature_spin.set_value(self.provider.settings.temperature)
        self.system_prompt_entry.props.text = self.provider.settings.system_prompt

    @background_task
    async def _load_api_usage(self):
        if not self.provider:
            return

        try:
            usage, limit = await self.provider.api_char_usage()
            level = usage / limit
            label = _("{usage:n} of {limit:n} characters").format(usage=usage, limit=limit)

            self.api_usage.props.value = level
            self.api_usage_label.props.label = label
            self.api_usage_group.props.visible = True
        except Exception as exc:
            logging.error(exc)

    @Gtk.Template.Callback()
    @background_task
    async def _on_instance_apply(self, _row):
        """Called on self.instance_entry::apply signal"""
        if not self.provider:
            return

        old_value = self.provider.instance_url
        new_value = self.instance_entry.props.text

        url = re.compile(r"https?://(www\.)?")
        self.new_instance_url = url.sub("", new_value).strip().strip("/")

        # Validate
        if self.new_instance_url != old_value:
            # Progress feedback
            self.instance_entry.props.sensitive = False
            self.api_key_entry.props.sensitive = False
            self.instance_stack.props.visible_child_name = "spinner"

            try:
                if await self.provider.validate_instance(self.new_instance_url):
                    self.provider.instance_url = self.new_instance_url
                    self.provider.reset_src_langs()
                    self.provider.reset_dest_langs()
                    self.instance_entry.remove_css_class("error")
                    self.instance_entry.props.text = self.provider.instance_url
                else:
                    self.instance_entry.add_css_class("error")
                    error_text = _("Not a valid {provider} instance")
                    error_text = error_text.format(provider=self.provider.prettyname)
                    toast = Adw.Toast(title=error_text)
                    self.dialog.add_toast(toast)
            except RequestError as exc:
                logging.error(exc)
                toast = Adw.Toast(title=_("Failed validating instance, check for network issues"))
                self.dialog.add_toast(toast)
            finally:
                self.instance_entry.props.sensitive = True
                self.api_key_entry.props.sensitive = True
                self.instance_stack.props.visible_child_name = "reset"
        else:
            self.instance_entry.remove_css_class("error")

    @Gtk.Template.Callback()
    def _on_instance_changed(self, _entry, _pspec):
        """Called on self.instance_entry::notify::text signal"""
        if not self.provider:
            return

        if self.instance_entry.props.text == self.provider.instance_url:
            self.instance_entry.props.show_apply_button = False
        elif not self.instance_entry.props.show_apply_button:
            self.instance_entry.props.show_apply_button = True

    @Gtk.Template.Callback()
    def _on_reset_instance(self, _button):
        if not self.provider:
            return

        if self.provider.instance_url != self.provider.defaults["instance_url"]:
            self.provider.reset_instance_url()

        self.instance_entry.remove_css_class("error")
        self.instance_entry.props.text = self.provider.instance_url

    @Gtk.Template.Callback()
    @background_task
    async def _on_api_key_apply(self, _row):
        """Called on self.api_key_entry::apply signal"""
        if not self.provider:
            return

        old_value = self.provider.api_key
        self.new_api_key = self.api_key_entry.get_text()

        # Validate
        if self.new_api_key != old_value:
            # Progress feedback
            self.instance_entry.props.sensitive = False
            self.api_key_entry.props.sensitive = False
            self.api_key_stack.props.visible_child_name = "spinner"

            try:
                if await self.provider.validate_api_key(self.new_api_key):
                    self.provider.api_key = self.new_api_key
                    self.api_key_entry.remove_css_class("error")
                    self.api_key_entry.props.text = self.provider.api_key
                else:
                    self.api_key_entry.add_css_class("error")
                    error_text = _("Not a valid {provider} API key")
                    error_text = error_text.format(provider=self.provider.prettyname)
                    toast = Adw.Toast(title=error_text)
                    self.dialog.add_toast(toast)
            except RequestError as exc:
                logging.error(exc)
                toast = Adw.Toast(title=_("Failed validating API key, check for network issues"))
                self.dialog.add_toast(toast)
            finally:
                self.instance_entry.props.sensitive = True
                self.api_key_entry.props.sensitive = True
                self.api_key_stack.props.visible_child_name = "reset"
        else:
            self.api_key_entry.remove_css_class("error")

    @Gtk.Template.Callback()
    def _on_reset_api_key(self, _button):
        """Called on self.api_key_reset::clicked signal"""
        if not self.provider:
            return

        if self.provider.api_key != self.provider.defaults["api_key"]:
            self.provider.reset_api_key()

        self.api_key_entry.remove_css_class("error")
        self.api_key_entry.props.text = self.provider.api_key

    @Gtk.Template.Callback()
    def _on_model_name_apply(self, _row):
        """Called on self.model_name_entry::apply signal"""
        if not self.provider or self.provider.name != "openai_compatible":
            return

        model_name = self.model_name_entry.props.text.strip()
        if model_name:
            self.provider.settings.model_name = model_name
            return

        self.model_name_entry.props.text = self.provider.settings.model_name

    def _on_temperature_changed(self, _adjustment):
        """Called on self.temperature_spin adjustment::value-changed signal."""
        if not self.provider or self.provider.name != "openai_compatible":
            return

        self.provider.settings.temperature = self.temperature_spin.get_value()

    @Gtk.Template.Callback()
    def _on_system_prompt_apply(self, _row):
        """Called on self.system_prompt_entry::apply signal"""
        if not self.provider or self.provider.name != "openai_compatible":
            return

        custom_prompt = self.system_prompt_entry.props.text
        self.provider.settings.system_prompt = custom_prompt

        missing = [
            placeholder
            for placeholder in ("{source_lang}", "{target_lang}")
            if placeholder not in custom_prompt
        ]
        if custom_prompt and missing:
            placeholders = ", ".join(missing)
            toast = Adw.Toast(
                title=_("Prompt missing {placeholders}; language context will be appended automatically").format(
                    placeholders=placeholders,
                )
            )
            self.dialog.add_toast(toast)

    @Gtk.Template.Callback()
    def _on_reset_system_prompt(self, _button):
        """Called on system_prompt_reset::clicked signal"""
        if not self.provider or self.provider.name != "openai_compatible":
            return

        self.provider.settings.system_prompt = ""
        self.system_prompt_entry.props.text = ""
        self.system_prompt_entry.remove_css_class("error")

    def _on_translator_loading(self, window: DialectWindow, _value):
        self.page.props.sensitive = not window.translator_loading

        if not window.translator_loading:
            self.provider = self.window.provider[self.scope]
            self._check_settings()
            self._check_advanced_options()
