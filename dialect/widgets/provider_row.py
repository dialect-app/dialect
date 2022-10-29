# Copyright 2020-2022 Mufeed Ali
# Copyright 2020-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import re
from gettext import gettext as _

from gi.repository import Adw, Gtk

from dialect.define import RES_PATH
from dialect.session import Session
from dialect.settings import Settings


@Gtk.Template(resource_path=f'{RES_PATH}/provider-row.ui')
class ProviderRow(Adw.ExpanderRow):
    __gtype_name__ = 'ProviderRow'

    instance_entry = Gtk.Template.Child()
    instance_stack = Gtk.Template.Child()
    instance_reset = Gtk.Template.Child()
    instance_spinner = Gtk.Template.Child()
    api_key_entry = Gtk.Template.Child()
    api_key_reset = Gtk.Template.Child()

    def __init__(self, provider, **kwargs):
        super().__init__(**kwargs)
        self.p_class = provider.p_class
        self.settings = Settings.get().get_translator_settings(provider.name)
        self.props.title = provider.prettyname

        # Instance
        self.instance_entry.props.title = _('{provider} Instance').format(provider=provider.prettyname)
        self.instance_entry.connect('apply', self._on_instance_apply)
        self.instance_entry.connect('notify::text', self._on_instance_changed)
        self.instance_reset.connect('clicked', self._on_reset_instance)

        # API Key
        self.api_key_entry.connect('apply', self._on_api_key_apply)
        self.api_key_reset.connect('clicked', self._on_reset_api_key)

        # Check what entries to show
        self._check_settings()

        # Load saved values
        self.instance_entry.props.text = self.settings.get_string('instance-url')
        self.api_key_entry.props.text = self.settings.get_string('api-key')

    def _check_settings(self):
        if not self.p_class.change_instance and not self.p_class.api_key_supported:
            self.props.sensitive = False
            self.props.subtitle = _("This provider doesn't have settigns available.")

        if not self.p_class.api_key_supported:
            self.api_key_entry.props.visible = False

    def _on_instance_apply(self, _row):
        def on_validation_response(session, result):
            valid = False
            try:
                data = Session.get_response(session, result)
                valid = self.p_class.validate_instance(data)
            except Exception as exc:
                logging.error(exc)

            if valid:
                # Translator loading in main window
                self._loading_handler = self.get_root().parent.connect(
                    'notify::backend-loading',
                    self._on_translator_loading
                )

                self.settings.instance_url = self.new_instance_url
                self.instance_entry.remove_css_class('error')
                self.instance_entry.props.text = self.settings.instance_url
            else:
                self.instance_entry.add_css_class('error')
                error_text = _('Not a valid {backend} instance')
                error_text = error_text.format(backend=self.p_class.prettyname)
                toast = Adw.Toast.new(error_text)
                self.get_root().add_toast(toast)

            self.instance_entry.props.sensitive = True
            self.api_key_entry.props.sensitive = True
            self.instance_stack.props.visible_child_name = 'reset'
            self.instance_spinner.stop()

        old_value = self.settings.instance_url
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

            validation = self.p_class.format_validate_instance(self.new_instance_url)
            Session.get().send_and_read_async(validation, 0, None, on_validation_response)
        else:
            self.instance_entry.remove_css_class('error')

    def _on_instance_changed(self, _entry, _pspec):
        if self.instance_entry.props.text == self.settings.instance_url:
            self.instance_entry.props.show_apply_button = False
        elif not self.instance_entry.props.show_apply_button:
            self.instance_entry.props.show_apply_button = True

    def _on_reset_instance(self, _button):
        if self.settings.instance_url != self.p_class.defaults['instance_url']:
            # Translator loading in main window
            self._loading_handler = self.get_root().parent.connect(
                'notify::backend-loading',
                self._on_translator_loading
            )

            self.settings.instance_url = self.p_class.defaults['instance_url']

        self.instance_entry.remove_css_class('error')
        self.instance_entry.props.text = self.settings.instance_url

    def _on_api_key_apply(self, _row):
        old_value = self.settings.api_key
        self.new_api_key = self.api_key_entry.get_text()

        if self.new_api_key != old_value:
            self.settings.api_key = self.new_api_key
            self.api_key_entry.props.text = self.settings.api_key

    def _on_reset_api_key(self, _button):
        if self.settings.api_key != self.p_class.defaults['api_key']:
            self.settings.api_key = self.p_class.defaults['api_key']
        self.api_key_entry.props.text = self.settings.api_key

    def _on_translator_loading(self, window, _value):
        self.instance_entry.props.sensitive = not window.backend_loading
        self.api_key_entry.props.sensitive = not window.backend_loading

        if window.backend_loading:
            self.instance_stack.props.visible_child_name = 'spinner'
            self.instance_spinner.start()
        else:
            self.instance_stack.props.visible_child_name = 'reset'
            self.instance_spinner.stop()
            self.get_root().parent.disconnect(self._loading_handler)
