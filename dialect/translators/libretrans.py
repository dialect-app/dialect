# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import json

from gi.repository import GLib, Soup

from dialect.translators.basetrans import Detected, TranslatorBase, TranslationError, Translation
from dialect.session import Session


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

    validation_path = '/spec'
    settings_path = '/frontend/settings'
    api_test_path = '/translate'

    _data = {
        'q': None,
        'source': None,
        'target': None,
        'api_key': api_key,
    }

    def __init__(self, callback, base_url=None, api_key='', **kwargs):
        def on_loaded():
            callback(self.langs_success and self.settings_success, self.error)

        def on_langs_response(session, result):
            try:
                data = Session.get_response(session, result)
                for lang in data:
                    self.languages.append(lang['code'])
                self.langs_success = True
            except Exception as exc:
                logging.error(exc)
                self.error = exc.cause

        def on_settings_response(session, result):
            try:
                data = Session.get_response(session, result)
                self.supported_features['suggestions'] = data.get('suggestions', False)
                self.supported_features['api-key-supported'] = data.get('apiKeys', False)
                self.supported_features['api-key-required'] = data.get('keyRequired', False)
                self.settings_success = True
            except Exception as exc:
                logging.error(exc)
                self.error = exc.cause

        self.langs_success = False
        self.settings_success = False
        self.error = ''

        if base_url is not None:
            self.instance_url = base_url
        self.api_key = api_key

        lang_message = Soup.Message.new('GET', self.lang_url)
        settings_message = Soup.Message.new('GET', self._frontend_settings_url)

        Session.get().multiple(
            [
                [lang_message, on_langs_response],
                [settings_message, on_settings_response]
            ],
            on_loaded
        )

    @property
    def _frontend_settings_url(self):
        return self.format_instance_url(self.instance_url, '/frontend/settings')

    @property
    def detect_url(self):
        return self.format_instance_url(self.instance_url, '/detect')

    @property
    def lang_url(self):
        return self.format_instance_url(self.instance_url, '/languages')

    @property
    def suggest_url(self):
        return self.format_instance_url(self.instance_url, '/suggest')

    @property
    def translate_url(self):
        return self.format_instance_url(self.instance_url, '/translate')

    @staticmethod
    def validate_instance(data):
        valid = False

        if data and data is not None:
            valid = data['info']['title'] == 'LibreTranslate'

        return valid

    @staticmethod
    def get_instance_settings(data):
        settings = {
            'api-key-supported': False,
            'api-key-required': False,
        }

        if data:
            settings = {
                'api-key-supported': data.get('apiKeys', False),
                'api-key-required': data.get('keyRequired', False),
            }

        return settings

    @staticmethod
    def format_api_key_test(api_key):
        data = {
            'q': 'hello',
            'source': 'en',
            'target': 'es',
            'api_key': api_key,
        }

        return (data, {})

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

    def format_detection(self, text):
        data = {
            'q': text,
        }
        if self.api_key:
            data['api_key'] = self.api_key

        return (data, {})

    def get_detect(self, data):
        return Detected(data[0]['language'], data[0]['confidence'])

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

    def format_translation(self, text, src, dest):
        data = {
            'q': text,
            'source': src,
            'target': dest,
        }
        if self.api_key:
            data['api_key'] = self.api_key

        return (data, {})

    def get_translation(self, data):
        return Translation(
            data['translatedText'],
            {
                'possible-mistakes': None,
                'src-pronunciation': None,
                'dest-pronunciation': None,
            },
        )

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
