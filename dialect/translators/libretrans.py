# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import httpx

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
        self.client = httpx.Client()

        r = self.client.get(self.lang_url)

        for lang in r.json():
            self.languages.append(lang['code'])

        r_frontend_settings = self.client.get(self._frontend_settings_url)

        self.supported_features['suggestions'] = r_frontend_settings.json().get('suggestions', False)
        self.supported_features['api-key-supported'] = r_frontend_settings.json().get('apiKeys', False)
        self.supported_features['api-key-required'] = r_frontend_settings.json().get('keyRequired', False)

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

        client = httpx.Client()
        try:
            r_validation = client.get(spec_url)
            r_frontend_settings = client.get(frontend_settings_url)

            data = {
                'validation-success': r_validation.json()['info']['title'] == 'LibreTranslate',
                'api-key-supported': r_frontend_settings.json().get('apiKeys', False),
                'api-key-required': r_frontend_settings.json().get('keyRequired', False),
            }

            validation_error = r_validation.json().get('error', None)
            if validation_error:
                # FIXME: Does this ever happen?
                logging.error(f'validation_error: {validation_error}')

            frontend_settings_error = r_frontend_settings.json().get('error', None)
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

        client = httpx.Client()
        try:
            _data = {
                'q': 'hello',
                'source': 'en',
                'target': 'es',
                'api_key': api_key,
            }
            r = client.post(
                translate_url,
                data=_data,
            )
            error = r.json().get('error', None)
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
            r = self.client.post(
                self.detect_url,
                data=data,
            )
            error = r.json().get('error', None)
            if error:
                logging.error(error)
                # We don't raise here because we don't know if there will ever be a case where an error
                # is reported but a language and confidence is still given.
                # Can be changed if we ever get confirmation.
            return Detected(r.json()[0]['language'], r.json()[0]['confidence'])
        except Exception as exc:
            raise TranslationError(exc) from exc

    def suggest(self, suggestion):
        try:
            data = self._data
            data['s'] = suggestion
            if self.api_key:
                data['api_key'] = self.api_key
            r = self.client.post(
                self.suggest_url,
                data=data,
            )
            return r.json().get('success', False)
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
            r = self.client.post(
                self.translate_url,
                data=self._data,
            )
            error = r.json().get('error', None)
            if error:
                logging.error(error)
                # We don't raise here because we don't know if there will ever be a case where an error
                # is reported but a translatedText is still given. Can be changed if we ever get confirmation.
            return Translation(
                r.json()['translatedText'],
                {
                    'possible-mistakes': None,
                    'src-pronunciation': None,
                    'dest-pronunciation': None,
                },
            )
        except Exception as exc:
            raise TranslationError(exc) from exc
