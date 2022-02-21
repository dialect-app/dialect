# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

class TranslatorBase:
    name = ''
    prettyname = ''
    history = []
    languages = ['en']
    supported_features = {
        'mistakes': False,
        'pronunciation': False,
        'change-instance': False,
        'suggestions': False,
        'api-key-supported': False,
        'api-key-required': False,
    }
    instance_url = ''
    api_key = ''
    src_langs = ['en', 'fr', 'es', 'de']
    dest_langs = ['fr', 'es', 'de', 'en']

    validation_path = ''
    api_test_path = ''

    @staticmethod
    def format_instance_url(url, path, http=False):
        protocol = 'https://'
        if url.startswith('localhost:') or http:
            protocol = 'http://'

        return protocol + url + path

    @staticmethod
    def validate_instance(data):
        pass

    def format_detection(self, text):
        pass

    def get_detect(self, data):
        return None

    def format_suggestion(self, text, src, dest, suggestion):
        pass

    def get_suggestion(self, data):
        pass

    def format_translation(self, text, src, dest):
        pass

    def get_translation(self, data):
        pass


class TranslationError(Exception):
    """Exception raised when translation fails."""

    def __init__(self, cause, message='Translation has failed'):
        self.cause = cause
        self.message = message
        super().__init__(self.message)


class Translation:
    text = None
    extra_data = {
        'possible-mistakes': None,
        'src-pronunciation': None,
        'dest-pronunciation': None,
    }

    def __init__(self, text, extra_data):
        self.text = text
        self.extra_data = extra_data


class Detected:
    lang = ''
    confidence = 0.0

    def __init__(self, lang, confidence):
        self.lang = lang
        self.confidence = confidence
