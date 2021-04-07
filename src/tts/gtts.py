# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gtts import gTTS, lang

from dialect.tts.basetts import TextToSpeechBase, TextToSpeechError


class TextToSpeech(TextToSpeechBase):
    name = 'google'
    prettyname = 'Google Text-to-Speech'
    languages = []

    def __init__(self, **kwargs):
        self.languages = list(lang.tts_langs().keys())

    def download_voice(self, text, language, file):
        try:
            tts = gTTS(text, lang=language, lang_check=False)
            tts.write_to_fp(file)
            file.seek(0)

        except Exception as exc:
            raise TextToSpeechError(exc) from exc
