# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

class TextToSpeechBase:
    name = ''
    prettyname = ''
    languages = ['en']

    def download_voice(self, text, language, file):
        pass


class TextToSpeechError(Exception):
    """Exception raised when tts fails."""

    def __init__(self, cause, message='Text to Speech has failed'):
        self.cause = cause
        self.message = message
        super().__init__(self.message)
