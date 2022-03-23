# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

class TranslatorBase:
    name = ''
    prettyname = ''
    history = []
    languages = ['en']
    chars_limit = 0
    supported_features = {
        'detection': False,
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
    def format_url(url, path, http=False):
        protocol = 'https://'
        if url.startswith('localhost:') or http:
            protocol = 'http://'

        return protocol + url + path

    @staticmethod
    def validate_instance(data):
        pass

    def format_suggestion(self, text, src, dest, suggestion):
        pass

    def get_suggestion(self, data):
        pass

    def format_translation(self, text, src, dest):
        pass

    def get_translation(self, data):
        pass


class TranslatorError(Exception):
    """Base Exception for Translator related errors."""

    def __init__(self, cause, message='Translator Error'):
        self.cause = cause
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}: {self.cause}'


class ApiKeyRequired(TranslatorError):
    """Exception raised when API key is required."""

    def __init__(self, cause, message='API Key Required'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class InvalidApiKey(TranslatorError):
    """Exception raised when an invalid API key is found."""

    def __init__(self, cause, message='Invalid API Key'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class InvalidLangCode(TranslatorError):
    """Exception raised when an invalid lang code is sent."""

    def __init__(self, cause, message='Invalid Lang Code'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class BatchSizeExceeded(TranslatorError):
    """Exception raised when the batch size limit has been exceeded."""

    def __init__(self, cause, message='Batch Size Exceeded'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class CharactersLimitExceeded(TranslatorError):
    """Exception raised when the char limit has been exceeded."""

    def __init__(self, cause, message='Characters Limit Exceeded'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class ServiceLimitReached(TranslatorError):
    """Exception raised when the service limit has been reached."""

    def __init__(self, cause, message='Service Limit Reached'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


class TranslationError(TranslatorError):
    """Exception raised when translation fails."""

    def __init__(self, cause, message='Translation has failed'):
        self.cause = cause
        self.message = message
        super().__init__(self.cause, self.message)


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
