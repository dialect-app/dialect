# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import json

from gi.repository import GLib, Soup

from dialect.translators.basetrans import Detected, TranslatorBase, TranslationError, Translation


class Translator(TranslatorBase):
    name = 'libretranslate'
    prettyname = 'LibreTranslate'
    client = None
    history = []
    languages = []
    supported_features = {
        'mistakes': False,
        'pronunciation': False,
        'change-instance': True,
        'suggestions': False,
        'api-key-supported': False,
        'api-key-required': False,
    }
    instance_url = 'translate.api.skitzen.com'
    api_key = ''

    _data = {
        'q': None,
        'source': None,
        'target': None,
        'api_key': api_key,
    }

    def __init__(self, base_url=None, api_key='', **kwargs):
        if base_url is not None:
            self.instance_url = base_url

        self.api_key = api_key
        self.session = Soup.Session()

        lang_response_data = self._get(self.lang_url) or []
        for lang in lang_response_data:
            self.languages.append(lang['code'])

        frontend_settings_response_data = self._get(self._frontend_settings_url)

        self.supported_features['suggestions'] = frontend_settings_response_data.get('suggestions', False)
        self.supported_features['api-key-supported'] = frontend_settings_response_data.get('apiKeys', False)
        self.supported_features['api-key-required'] = frontend_settings_response_data.get('keyRequired', False)

    @property
    def _frontend_settings_url(self):
        if self.instance_url.startswith('localhost:'):
            return 'http://' + self.instance_url + '/frontend/settings'
        return 'https://' + self.instance_url + '/frontend/settings'

    @property
    def detect_url(self):
        if self.instance_url.startswith('localhost:'):
            return 'http://' + self.instance_url + '/detect'
        return 'https://' + self.instance_url + '/detect'

    @property
    def lang_url(self):
        if self.instance_url.startswith('localhost:'):
            return 'http://' + self.instance_url + '/languages'
        return 'https://' + self.instance_url + '/languages'

    @property
    def suggest_url(self):
        if self.instance_url.startswith('localhost:'):
            return 'http://' + self.instance_url + '/suggest'
        return 'https://' + self.instance_url + '/suggest'

    @property
    def translate_url(self):
        if self.instance_url.startswith('localhost:'):
            return 'http://' + self.instance_url + '/translate'
        return 'https://' + self.instance_url + '/translate'

    @staticmethod
    def validate_instance_url(url):
        if url.startswith('localhost:'):
            spec_url = 'http://' + url + '/spec'
            frontend_settings_url = 'http://' + url + '/frontend/settings'
        else:
            spec_url = 'https://' + url + '/spec'
            frontend_settings_url = 'https://' + url + '/frontend/settings'

        session = Soup.Session()
        try:
            validation_message = Soup.Message.new('GET', spec_url)
            validation_response = session.send_and_read(validation_message, None)
            validation_response_data = json.loads(
                validation_response.get_data()
            ) if validation_response else {}

            frontend_settings_message = Soup.Message.new('GET', frontend_settings_url)
            frontend_settings_response = session.send_and_read(frontend_settings_message, None)
            frontend_settings_response_data = json.loads(
                frontend_settings_response.get_data()
            ) if frontend_settings_response else {}

            data = {
                'validation-success': validation_response_data['info']['title'] == 'LibreTranslate',
                'api-key-supported': frontend_settings_response_data.get('apiKeys', False),
                'api-key-required': frontend_settings_response_data.get('keyRequired', False),
            }

            validation_error = validation_response_data.get('error', None)
            if validation_error:
                # FIXME: Does this ever happen?
                logging.error(f'validation_error: {validation_error}')

            frontend_settings_error = frontend_settings_response_data.get('error', None)
            if frontend_settings_error:
                # FIXME: Does this ever happen?
                logging.error(f'frontend_settings_error: {frontend_settings_error}')

            return data
        except Exception as exc:
            logging.warning(type(exc))
            return {
                'validation-success': False,
                'api-key-supported': False,
                'api-key-required': False,
            }

    @staticmethod
    def validate_api_key(api_key, url='translate.api.skitzen.com'):
        if url.startswith('localhost:'):
            translate_url = 'http://' + url + '/translate'
        else:
            translate_url = 'https://' + url + '/translate'

        session = Soup.Session()
        try:
            _data = {
                'q': 'hello',
                'source': 'en',
                'target': 'es',
                'api_key': api_key,
            }

            translate_message = Soup.Message.new('POST', translate_url)
            translate_data_bytes = json.dumps(_data).encode('utf-8')
            translate_data_glib_bytes = GLib.Bytes.new(translate_data_bytes)
            translate_message.set_request_body_from_bytes('application/json', translate_data_glib_bytes)
            translate_response = session.send_and_read(translate_message, None)
            translate_response_data = json.loads(
                translate_response.get_data()
            ) if translate_response else {}

            error = translate_response_data.get('error', None)
            if error:
                logging.error(error)
                return False

            return True
        except Exception as exc:
            logging.warning(type(exc))
            return False

    def detect(self, src_text):
        """Detect the language using the same mechanisms that LibreTranslate uses but locally."""
        try:
            data = {
                'q': src_text,
            }
            if self.api_key:
                data['api_key'] = self.api_key
            detect_response_data = self._post(self.detect_url, data)
            error = detect_response_data.get('error', None)
            if error:
                logging.error(error)
                # We don't raise here because we don't know if there will ever be a case where an error
                # is reported but a language and confidence is still given.
                # Can be changed if we ever get confirmation.
            return Detected(detect_response_data[0]['language'], detect_response_data[0]['confidence'])
        except Exception as exc:
            raise TranslationError(exc) from exc

    def suggest(self, suggestion):
        try:
            data = self._data
            data['s'] = suggestion
            if self.api_key:
                data['api_key'] = self.api_key
            suggest_response_data = self._post(self.suggest_url, data)
            error = suggest_response_data.get('error', None)
            if error:
                logging.error(error)
            return suggest_response_data.get('success', False)
        except Exception as exc:
            raise TranslationError(exc) from exc

    def translate(self, src_text, src, dest):
        try:
            self._data = {
                'q': src_text,
                'source': src,
                'target': dest,
            }
            if self.api_key:
                self._data['api_key'] = self.api_key
            response_data = self._post(
                self.translate_url,
                self._data,
            )
            error = response_data.get('error', None)
            if error:
                logging.error(error)
                # We don't raise here because we don't know if there will ever be a case where an error
                # is reported but a translatedText is still given. Can be changed if we ever get confirmation.
            return Translation(
                response_data['translatedText'],
                {
                    'possible-mistakes': None,
                    'src-pronunciation': None,
                    'dest-pronunciation': None,
                },
            )
        except Exception as exc:
            raise TranslationError(exc) from exc

    def _get(self, url):
        message = Soup.Message.new('GET', url)
        response = self.session.send_and_read(message, None)
        response_data = json.loads(
            response.get_data()
        ) if response else {}
        return response_data

    def _post(self, url, data):
        message = Soup.Message.new('POST', url)
        data_bytes = json.dumps(data).encode('utf-8')
        data_glib_bytes = GLib.Bytes.new(data_bytes)
        message.set_request_body_from_bytes('application/json', data_glib_bytes)
        response = self.session.send_and_read(message, None)
        response_data = json.loads(
            response.get_data()
        ) if response else {}
        return response_data
