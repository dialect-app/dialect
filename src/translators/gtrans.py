# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from googletrans import LANGUAGES, Translator

from dialect.translators.basetrans import TranslatorBase, TranslationError


class GTranslator(TranslatorBase):
    name = 'google'
    prettyname = 'Google Translate'
    history = []
    languages = LANGUAGES
    supported_features = {
        'mistakes': True,
        'pronunciation': True,
        'voice': True,
        'change-instance': False,
    }

    def __init__(self, **kwargs):
        self._translator = Translator()

    def detect(self, src_text):
        try:
            if callable(getattr(self._translator, 'detect_legacy', None)):
                return self._translator.detect_legacy(src_text)
            return self._translator.detect(src_text)
        except Exception as exc:
            raise TranslationError(exc) from exc

    def translate(self, src_text, src, dest):
        try:
            if callable(getattr(self._translator, 'translate_legacy', None)):
                return self._translator.translate_legacy(src_text)
            return self._translator.translate(src_text, src=src, dest=dest)
        except Exception as exc:
            raise TranslationError(exc) from exc
