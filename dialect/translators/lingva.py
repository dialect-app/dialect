# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from gi.repository import Soup

from dialect.translators.basetrans import (
    InvalidLangCode, TranslatorBase, Translation, TranslatorError
)
from dialect.session import Session, ResponseEmpty


class Translator(TranslatorBase):
    name = 'lingva'
    prettyname = 'Lingva Translate'
    history = []
    languages = []
    chars_limit = 5000
    supported_features = {
        'detection': True,
        'mistakes': False,
        'pronunciation': False,
        'change-instance': True,
        'suggestions': False,
        'api-key-supported': False,
        'api-key-required': False,
    }
    instance_url = 'lingva.ml'

    validation_path = '/api/v1/en/es/hello'

    def __init__(self, callback, base_url=None, _api_key='', **kwargs):
        def on_langs_response(session, result):
            success = False
            network_error = False
            error = ''
            try:
                data = Session.get_response(session, result)
                self._check_errors(data)
                if 'languages' in data:
                    for lang in data['languages']:
                        if lang['code'] != 'auto':
                            self.languages.append(lang['code'])
                    success = True
            except (TranslatorError, ResponseEmpty) as exc:
                logging.warning(exc)
                error = str(exc)
            except Exception as exc:
                logging.warning(exc)
                error = str(exc)
                network_error = True

            callback(success, error, network_error)

        if base_url is not None:
            self.instance_url = base_url

        lang_message = Soup.Message.new('GET', self.lang_url)
        Session.get().send_and_read_async(lang_message, 0, None, on_langs_response)

    @property
    def lang_url(self):
        return self.format_url(self.instance_url, '/api/v1/languages/')

    @property
    def translate_url(self):
        return self.format_url(self.instance_url, '/api/v1/{src}/{dest}/{text}')

    @staticmethod
    def validate_instance(data):
        valid = False

        if data and 'translation' in data:
            valid = True

        return valid

    def format_translation(self, _text, _src, _dest):
        return ('GET', {}, {}, False)

    def get_translation(self, data):
        self._check_errors(data)
        translation = Translation(
            data['translation'],
            {
                'possible-mistakes': None,
                'src-pronunciation': None,
                'dest-pronunciation': None,
            },
        )

        return (translation, None)

    def _check_errors(self, data):
        """Raises a proper Exception if an error is found in the data."""
        if 'error' in data:
            error = data['error']

            if error == 'Invalid target language' or error == 'Invalid source language':
                raise InvalidLangCode(error)
            else:
                raise TranslatorError(error)
