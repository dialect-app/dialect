# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from uuid import uuid4

from dialect.providers.base import (ProviderError, SoupProvider, Translation,
                                    TranslationError)


class Provider(SoupProvider):
    __provider_type__ = 'soup'

    name = 'yandex'
    prettyname = 'Yandex'
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

    _headers = {
        'User-Agent': 'ru.yandex.translate/21.15.4.21402814 (Xiaomi Redmi K20 Pro; Android 11)',
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.languages = [
            'af', 'sq', 'am', 'ar', 'hy', 'az', 'ba', 'eu', 'be', 'bn', 'bs', 'bg', 'my',
            'ca', 'ceb', 'zh', 'cv', 'hr', 'cs', 'da', 'nl', 'sjn', 'emj', 'en', 'eo',
            'et', 'fi', 'fr', 'gl', 'ka', 'de', 'el', 'gu', 'ht', 'he', 'mrj', 'hi',
            'hu', 'is', 'id', 'ga', 'it', 'ja', 'jv', 'kn', 'kk', 'kazlat', 'km', 'ko',
            'ky', 'lo', 'la', 'lv', 'lt', 'lb', 'mk', 'mg', 'ms', 'ml', 'mt', 'mi', 'mr',
            'mhr', 'mn', 'ne', 'no', 'pap', 'fa', 'pl', 'pt', 'pa', 'ro', 'ru', 'gd', 'sr',
            'si', 'sk', 'sl', 'es', 'su', 'sw', 'sv', 'tl', 'tg', 'ta', 'tt', 'te', 'th', 'tr',
            'udm', 'uk', 'ur', 'uz', 'uzbcyr', 'vi', 'cy', 'xh', 'sah', 'yi', 'zu'
        ]
        self.chars_limit = 10000
        self.detection = True

        self._uuid = str(uuid4()).replace('-', '')

    @property
    def translate_url(self):
        path = f'/api/v1/tr.json/translate?id={self._uuid}-0-0&srv=android'
        return self.format_url('translate.yandex.net', path)

    def format_translation(self, text, src, dest):
        data = {
            'lang': dest,
            'text': text
        }
        if src != 'auto':
            data['lang'] = f'{src}-{dest}'

        return self.create_request('POST', self.translate_url, data, self._headers, True)

    def get_translation(self, data):
        data = self.read_data(data)
        detected = None

        if 'code' in data and data['code'] == 200:

            if 'lang' in data:
                detected = data['lang'].split('-')[0]

            if 'text' in data:
                result = Translation(
                    data['text'][0],
                    {
                        'possible-mistakes': None,
                        'src-pronunciation': None,
                        'dest-pronunciation': None,
                    }
                )
                return (result, detected)

            else:
                raise TranslationError('Translation failed')

        else:
            error = data['message'] if 'message' in data else ''
            raise ProviderError(error)
