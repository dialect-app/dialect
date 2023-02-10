# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import urllib

from dialect.providers.base import (
    InvalidLangCode, SoupProvider, ProviderError, TextToSpeechError, Translation
)


class Provider(SoupProvider):
    __provider_type__ = 'soup'

    name = 'lingva'
    prettyname = 'Lingva Translate'
    translation = True
    tts = True
    definitions = False
    change_instance = True
    api_key_supported = False
    defaults = {
        'instance_url': 'lingva.ml',
        'api_key': '',
        'src_langs': ['en', 'fr', 'es', 'de'],
        'dest_langs': ['fr', 'es', 'de', 'en']
    }

    trans_init_requests = [
        'languages'
    ]
    tts_init_requests = [
        'languages'
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = 5000
        self.detection = True
        self.mistakes = True
        self.pronunciation = True

    @staticmethod
    def format_validate_instance(url):
        url = Provider.format_url(url, '/api/v1/en/es/hello')
        return Provider.create_request('GET', url)

    @staticmethod
    def validate_instance(data):
        data = Provider.read_data(data)
        valid = False

        if data and 'translation' in data:
            valid = True

        return valid

    @property
    def lang_url(self):
        return self.format_url(self.instance_url, '/api/v1/languages/')

    @property
    def translate_url(self):
        return self.format_url(self.instance_url, '/api/v1/{src}/{dest}/{text}')

    @property
    def speech_url(self):
        return self.format_url(self.instance_url, '/api/v1/audio/{lang}/{text}')

    def format_languages_init(self):
        return self.create_request('GET', self.lang_url)

    def languages_init(self, data):
        try:
            data = self.read_data(data)
            self._check_errors(data)
            if 'languages' in data:
                for lang in data['languages']:
                    if lang['code'] != 'auto':
                        self.languages.append(lang['code'])
                        self.tts_languages.append(lang['code'])
            else:
                self.error = 'No langs found on server.'
        except Exception as exc:
            logging.warning(exc)
            self.error = str(exc)

    def format_translation(self, text, src, dest):
        text = urllib.parse.quote(text, safe='')
        url = self.translate_url.format(text=text, src=src, dest=dest)
        return self.create_request('GET', url)

    def get_translation(self, data):
        data = self.read_data(data)
        self._check_errors(data)

        detected = data['info'].get('detectedSource', None)
        mistakes = data['info'].get('typo', None)
        src_pronunciation = data['info']['pronunciation'].get('query', None)
        dest_pronunciation = data['info']['pronunciation'].get('translation', None)

        translation = Translation(
            data['translation'],
            {
                'possible-mistakes': [mistakes, mistakes],
                'src-pronunciation': src_pronunciation,
                'dest-pronunciation': dest_pronunciation,
            },
        )

        return (translation, detected)

    def format_speech(self, text, language):
        url = self.speech_url.format(text=text, lang=language)
        return self.create_request('GET', url)

    def get_speech(self, data, file):
        data = self.read_data(data)
        self._check_errors(data)

        if 'audio' in data:
            audio = bytearray(data['audio'])
            file.write(audio)
            file.seek(0)
        else:
            raise TextToSpeechError('No audio was found')

    def _check_errors(self, data):
        """Raises a proper Exception if an error is found in the data."""
        if not data:
            raise ProviderError('Request empty')
        if 'error' in data:
            error = data['error']

            if error == 'Invalid target language' or error == 'Invalid source language':
                raise InvalidLangCode(error)
            else:
                raise ProviderError(error)
