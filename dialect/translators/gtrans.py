# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from googletrans import Translator as GoogleTranslator

from dialect.translators.basetrans import TranslatorBase, TranslationError, Translation


class Translator(TranslatorBase):
    name = 'google'
    prettyname = 'Google Translate'
    history = []
    languages = [
        'af', 'sq', 'am', 'ar', 'hy', 'az', 'eu', 'be', 'bn', 'bs', 'bg', 'ca',
        'ceb', 'ny', 'zh-CN', 'zh-TW', 'co', 'hr', 'cs', 'da', 'nl', 'en', 'eo',
        'et', 'tl', 'fi', 'fr', 'fy', 'gl', 'ka', 'de', 'el', 'gu', 'ht', 'ha',
        'haw', 'iw', 'he', 'hi', 'hmn', 'hu', 'is', 'ig', 'id', 'ga', 'it',
        'ja', 'jw', 'kn', 'kk', 'km', 'ko', 'ku', 'ky', 'lo', 'la', 'lv', 'lt',
        'lb', 'mk', 'mg', 'ms', 'ml', 'mt', 'mi', 'mr', 'mn', 'my', 'ne', 'no',
        'or', 'ps', 'fa', 'pl', 'pt', 'pa', 'ro', 'ru', 'sm', 'gd', 'sr', 'st',
        'sn', 'sd', 'si', 'sk', 'sl', 'so', 'es', 'su', 'sw', 'sv', 'tg', 'ta',
        'te', 'th', 'tr', 'uk', 'ur', 'ug', 'uz', 'vi', 'cy', 'xh', 'yi', 'yo',
        'zu'
    ]
    supported_features = {
        'mistakes': True,
        'pronunciation': True,
        'change-instance': False,
    }

    def __init__(self, **kwargs):
        self._translator = GoogleTranslator(raise_exception=True)

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
                translated = self._translator.translate_legacy(src_text, src=src, dest=dest)
            else:
                translated = self._translator.translate(src_text, src=src, dest=dest)
            result = Translation(
                translated.text,
                {
                    'possible-mistakes': translated.extra_data['possible-mistakes'],
                    'src-pronunciation': None,
                    'dest-pronunciation': None,
                },
            )
            try:
                result.extra_data['src-pronunciation'] = translated.extra_data['translation'][1][3]
            except IndexError:
                result.extra_data['src-pronunciation'] = None
            try:
                result.extra_data['dest-pronunciation'] = translated.extra_data['translation'][1][2]
            except IndexError:
                result.extra_data['dest-pronunciation'] = None
            return result
        except Exception as exc:
            raise TranslationError(exc) from exc
