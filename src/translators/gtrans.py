# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from googletrans import LANGUAGES, Translator

from dialect.translators.basetrans import TranslatorBase, TranslationError


class GTranslator(TranslatorBase):
    name = 'google'
    history = []
    languages = LANGUAGES
    supported_features = {
        'mistakes': True,
        'pronunciation': True,
        'voice': True,
    }

    def __init__(self):
        self._translator = Translator()

    def detect(self, src_text):
        try:
            return self._translator.detect(src_text)
        except Exception as e:
            raise TranslationError(e)

    def translate(self, src_text, src, dest):
        try:
            return self._translator.translate(src_text, src=src, dest=dest)
        except Exception as e:
            raise TranslationError(e)
