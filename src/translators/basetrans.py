# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

class TranslatorBase:
    name = ''
    history = []
    languages = {
        'en': 'ENGLISH'
    }
    supported_features = {
        'mistakes': False,
        'pronunciation': False,
        'voice': False,
    }

    def detect(self, src_text):
        pass

    def translate(self, src_text, src, dest):
        pass


class TranslationError(Exception):
    """Exception raised when translation fails."""

    def __init__(self, cause, message='Translation has failed'):
        self.cause = cause
        self.message = message
        super().__init__(self.message)


class Translation:
    text = None
    extra_data = {}

    def __init__(self, text, extra_data):
        self.text = text
        self.extra_data = extra_data


class Detected:
    lang = ''
    confidence = 0.0

    def __init__(self, lang, confidence):
        self.lang = lang
        self.confidence = confidence
