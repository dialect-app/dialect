# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import re

from bs4 import BeautifulSoup

from dialect.providers.base import (
    ProviderError, SoupProvider, Translation, TranslationError
)


class Provider(SoupProvider):
    __provider_type__ = 'soup'

    name = 'bing'
    prettyname = 'Bing'
    translation = True
    tts = False
    definitions = False
    change_instance = False
    api_key_supported = False
    defaults = {
        'instance_url': '',
        'api_key': '',
        'src_langs': ['en', 'fr', 'es', 'de'],
        'dest_langs': ['fr', 'es', 'de', 'en']
    }

    trans_init_requests = [
        'parse_html'
    ]

    _headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': '*/*'
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = 1000  # Web UI limit
        self.detection = True
        self.pronunciation = True

        self._key = ''
        self._token = ''
        self._ig = ''
        self._iid = ''
        self._count = 1

    @property
    def html_url(self):
        return self.format_url('www.bing.com', '/translator')

    @property
    def translate_url(self):
        params = {
            'isVertical': '1',
            '': '',
            'IG': self._ig,
            'IID': f'{self._iid}.{self._count}',
        }
        return self.format_url('www.bing.com', '/ttranslatev3', params)

    def format_parse_html_init(self):
        return self.create_request('GET', self.html_url, headers=self._headers)

    def parse_html_init(self, data):
        if data:
            try:
                soup = BeautifulSoup(data, 'html.parser')

                # Get Langs
                langs = soup.find('optgroup', {'id': 't_tgtAllLang'})
                for child in langs.findChildren():
                    if child.name == 'option':
                        self.languages.append(child['value'])

                # Get IID
                iid = soup.find('div', {'id': 'rich_tta'})
                self._iid = iid['data-iid']

                # Decode response bytes
                data = data.decode('utf-8')

                # Look for abuse prevention data
                params = re.findall("var params_AbusePreventionHelper = \[(.*?)\];", data)[0]
                abuse_params = params.replace('"', '').split(',')
                self._key = abuse_params[0]
                self._token = abuse_params[1]

                # Look for IG
                self._ig = re.findall("IG:\"(.*?)\",", data)[0]

            except Exception as exc:
                self.error = 'Failed parsing HTML from bing.com'
                logging.warning(self.error, str(exc))

        else:
            self.error = 'Could not get HTML from bing.com'
            logging.warning(self.error)

    def format_translation(self, text, src, dest):
        data = {
            'fromLang': 'auto-detect',
            'text': text,
            'to': dest,
            'token': self._token,
            'key': self._key
        }

        if src != 'auto':
            data['fromLang'] = src

        return self.create_request('POST', self.translate_url, data, self._headers, True)

    def get_translation(self, data):
        self._count += 1  # Increment requests count

        data = self.read_data(data)
        self._check_errors(data)

        try:
            data = data[0]
            detected = None
            pronunciation = None

            if 'translations' in data:

                if 'detectedLanguage' in data:
                    detected = data['detectedLanguage']['language']

                if 'transliteration' in data['translations'][0]:
                    pronunciation = data['translations'][0]['transliteration']['text']

                result = Translation(
                    data['translations'][0]['text'],
                    {
                        'possible-mistakes': None,
                        'src-pronunciation': None,
                        'dest-pronunciation': pronunciation,
                    }
                )
                return (result, detected)

        except Exception as exc:
            raise TranslationError(str(exc))

    def _check_errors(self, data):
        if not data:
            raise ProviderError('Request empty')

        if 'errorMessage' in data:
            error = data['errorMessage']
            code = data['statusCode']

            match code:
                case _:
                    raise ProviderError(error)
