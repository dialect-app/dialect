# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

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
    }
    instance_url = 'translate.astian.org'

    _data = {
        'q': None,
        'source': None,
        'target': None,
    }

    def __init__(self, base_url=None, **kwargs):
        if base_url is not None:
            self.instance_url = base_url

        self.client = httpx.Client()

        r = self.client.get(self.lang_url)

        for lang in r.json():
            self.languages.append(lang['code'])

        r_frontend_settings = self.client.get(self._frontend_settings_url)

        if r_frontend_settings.json()['suggestions']:
            self.supported_features['suggestions'] = True

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
            url = 'http://' + url + '/spec'
        else:
            url = 'https://' + url + '/spec'
        client = httpx.Client()
        try:
            r = client.get(url)
            data = r.json()

            if data['info']['title'] == 'LibreTranslate':
                return True

            return False
        except Exception:
            return False

    def detect(self, src_text):
        """Detect the language using the same mechanisms that LibreTranslate uses but locally."""
        try:
            r = self.client.post(
                self.detect_url,
                data={
                    'q': src_text,
                },
            )
            return Detected(r.json()[0]['language'], r.json()[0]['confidence'])
        except Exception as exc:
            raise TranslationError(exc) from exc

    def suggest(self, suggestion):
        try:
            data = self._data
            data['s'] = suggestion
            r = self.client.post(
                self.suggest_url,
                data=data,
            )
            if 'success' in r.json():
                return r.json()['success']
            else:
                return False
        except Exception as exc:
            raise TranslationError(exc) from exc

    def translate(self, src_text, src, dest):
        try:
            self._data = {
                'q': src_text,
                'source': src,
                'target': dest,
            }
            r = self.client.post(
                self.translate_url,
                data=self._data,
            )
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
