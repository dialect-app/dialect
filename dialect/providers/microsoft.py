# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from uuid import uuid4

from dialect.providers.base import (
    ProviderError, ServiceLimitReached, SoupProvider, Translation,
    InvalidApiKey, InvalidLangCode
)


class Provider(SoupProvider):
    __provider_type__ = 'soup'

    name = 'microsoft'
    prettyname = 'Microsoft'
    translation = True
    tts = False
    definitions = False
    change_instance = False
    api_key_supported = True
    defaults = {
        'instance_url': '',
        'api_key': '',
        'src_langs': ['en', 'fr', 'es', 'de'],
        'dest_langs': ['fr', 'es', 'de', 'en']
    }

    trans_init_requests = [
        'languages',
    ]

    _microsoft_url = 'api.cognitive.microsofttranslator.com'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.detection = True
        self.api_key_required = True

    @property
    def lang_url(self):
        params = {
            'api-version': '3.0',
            'scope': 'translation'
        }
        return self.format_url(self._microsoft_url, '/languages', params)

    def translate_url(self, params):
        return self.format_url(self._microsoft_url, '/translate', params)

    def format_languages_init(self):
        return self.create_request('GET', self.lang_url)

    def languages_init(self, data):
        try:
            data = self.read_data(data)
            self._check_errors(data)
            for code in data['translation'].keys():
                self.languages.append(code)
        except Exception as exc:
            logging.warning(exc)
            self.error = str(exc)

    def format_validate_api_key(self, api_key):
        self.api_key = api_key
        return self.format_translation('a', 'auto', 'en')

    def validate_api_key(self, data):
        self.get_translation(data)

    def format_translation(self, text, src, dest):
        params = {
            'api-version': '3.0',
            'to': dest
        }
        if src != 'auto':
            params['from'] = src

        headers = {
            'Ocp-Apim-Subscription-Key': self.api_key,
            'Ocp-Apim-Subscription-Region': 'westus2',  # TODO: This value should be configurable
            'X-ClientTraceId': str(uuid4())
        }

        data = [{
            'text': text
        }]

        return self.create_request('POST', self.translate_url(params), data, headers)

    def get_translation(self, data):
        data = self.read_data(data)
        self._check_errors(data)

        data = data[0]
        detected = None

        if 'translations' in data:

            if 'detectedLanguage' in data:
                detected = data['detectedLanguage']['language']

            result = Translation(
                data['translations'][0]['text'],
                {
                    'possible-mistakes': None,
                    'src-pronunciation': None,
                    'dest-pronunciation': None,
                }
            )
            return (result, detected)

        else:
            error = data['message'] if 'message' in data else ''
            raise ProviderError(error)

    def _check_errors(self, data):
        if not data:
            raise ProviderError('Request empty')

        if 'error' in data:
            error = data['error']['message']
            code = data['error']['code']

            match code:
                case 400019 | 400023 | 400035 | 400036:
                    raise InvalidLangCode(error)
                case 401000:
                    raise InvalidApiKey(error)
                case 403001 | 429000 | 429001 | 429002:
                    raise ServiceLimitReached(error)
                case _:
                    raise ProviderError(error)
