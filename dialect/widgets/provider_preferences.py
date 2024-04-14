# Copyright 2023 Mufeed Ali
# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import re

from gi.repository import Adw, GObject, Gtk

from dialect.define import RES_PATH
from dialect.providers import ProviderCapability, ProviderFeature


@Gtk.Template(resource_path=f'{RES_PATH}/provider-preferences.ui')
class ProviderPreferences(Adw.NavigationPage):
    __gtype_name__ = 'ProviderPreferences'

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
    api_usage_group = Gtk.Template.Child()
    api_usage = Gtk.Template.Child()
    api_usage_label = Gtk.Template.Child()

    def __init__(self, scope, dialog, window, **kwargs):
        super().__init__(**kwargs)
        self.scope = scope
        self.provider = window.provider[scope]
        self.dialog = dialog
        self.window = window

        self.title.props.subtitle = self.provider.prettyname

        self.translation = ProviderCapability.TRANSLATION in self.provider.capabilities
        self.tts = ProviderCapability.TTS in self.provider.capabilities
        self.definitions = ProviderCapability.DEFINITIONS in self.provider.capabilities

        # Check what entries to show
        self._check_settings()

        # Load saved values
        self.instance_entry.props.text = self.provider.instance_url
        self.api_key_entry.props.text = self.provider.api_key

        # Main window progress
        self.window.connect('notify::translator-loading', self._on_translator_loading)            

    def _check_settings(self):
        def on_usage(usage, limit):
            level = usage / limit
            label = _('{usage:n} of {limit:n} characters').format(usage=usage, limit=limit)

            self.api_usage.props.value = level
            self.api_usage_label.props.label = label
            self.api_usage_group.props.visible = True

        def on_usage_fail(_error):
            pass

        self.instance_entry.props.visible = ProviderFeature.INSTANCES in self.provider.features
        self.api_key_entry.props.visible = ProviderFeature.API_KEY in self.provider.features

        self.api_usage_group.props.visible = False
        if ProviderFeature.API_KEY_USAGE in self.provider.features:
            self.provider.api_char_usage(on_usage, on_usage_fail)

    @Gtk.Template.Callback()
    def _on_instance_apply(self, _row):
        """ Called on self.instance_entry::apply signal """
        def on_done(valid):
            if valid:
                self.provider.instance_url = self.new_instance_url
                self.provider.reset_src_langs()
                self.provider.reset_dest_langs()
                self.instance_entry.remove_css_class('error')
                self.instance_entry.props.text = self.provider.instance_url
            else:
                self.instance_entry.add_css_class('error')
                error_text = _('Not a valid {provider} instance')
                error_text = error_text.format(provider=self.provider.prettyname)
                toast = Adw.Toast.new(error_text)
                self.dialog.add_toast(toast)

            self.instance_entry.props.sensitive = True
            self.api_key_entry.props.sensitive = True
            self.instance_stack.props.visible_child_name = 'reset'
            self.instance_spinner.stop()

        old_value = self.provider.instance_url
        new_value = self.instance_entry.props.text

        url = re.compile(r'https?://(www\.)?')
        self.new_instance_url = url.sub('', new_value).strip().strip('/')

        # Validate
        if self.new_instance_url != old_value:
            # Progress feedback
            self.instance_entry.props.sensitive = False
            self.api_key_entry.props.sensitive = False
            self.instance_stack.props.visible_child_name = 'spinner'
            self.instance_spinner.start()

            # TODO: Use on_fail to notify network error
            self.provider.validate_instance(self.new_instance_url, on_done, lambda _: on_done(False))
        else:
            self.instance_entry.remove_css_class('error')

    @Gtk.Template.Callback()
    def _on_instance_changed(self, _entry, _pspec):
        """ Called on self.instance_entry::notify::text signal """
        if self.instance_entry.props.text == self.provider.instance_url:
            self.instance_entry.props.show_apply_button = False
        elif not self.instance_entry.props.show_apply_button:
            self.instance_entry.props.show_apply_button = True

    @Gtk.Template.Callback()
    def _on_reset_instance(self, _button):
        if self.provider.instance_url != self.provider.defaults['instance_url']:
            self.provider.reset_instance_url()

        self.instance_entry.remove_css_class('error')
        self.instance_entry.props.text = self.provider.instance_url

    @Gtk.Template.Callback()
    def _on_api_key_apply(self, _row):
        """ Called on self.api_key_entry::apply signal """
        def on_done(valid):
            if valid:
                self.provider.api_key = self.new_api_key
                self.api_key_entry.remove_css_class('error')
                self.api_key_entry.props.text = self.provider.api_key
            else:
                self.api_key_entry.add_css_class('error')
                error_text = _('Not a valid {provider} API key')
                error_text = error_text.format(provider=self.provider.prettyname)
                toast = Adw.Toast.new(error_text)
                self.dialog.add_toast(toast)

            self.instance_entry.props.sensitive = True
            self.api_key_entry.props.sensitive = True
            self.api_key_stack.props.visible_child_name = 'reset'
            self.api_key_spinner.stop()

        old_value = self.provider.api_key
        self.new_api_key = self.api_key_entry.get_text()

        # Validate
        if self.new_api_key != old_value:
            # Progress feedback
            self.instance_entry.props.sensitive = False
            self.api_key_entry.props.sensitive = False
            self.api_key_stack.props.visible_child_name = 'spinner'
            self.api_key_spinner.start()

            # TODO: Use on_fail to notify network error
            self.provider.validate_api_key(self.new_api_key, on_done, lambda _: on_done(False))
        else:
            self.api_key_entry.remove_css_class('error')

    @Gtk.Template.Callback()
    def _on_reset_api_key(self, _button):
        """Called on self.api_key_reset::clicked signal"""
        if self.provider.api_key != self.provider.defaults['api_key']:
            self.provider.reset_api_key()

        self.api_key_entry.remove_css_class('error')
        self.api_key_entry.props.text = self.provider.api_key

    def _on_translator_loading(self, window, _value):
        self.page.props.sensitive = not window.translator_loading

        if not window.translator_loading:
            self.provider = self.window.provider[self.scope]
            self._check_settings()
