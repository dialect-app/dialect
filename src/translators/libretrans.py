from dialect.translators import TranslatorBase, TranslationError, Translation

LANGUAGES = {
    "en": "ENGLISH"
}

class LibreTranslator(TranslatorBase):
    history = []
    supported_features = {
        "mistakes": False,
        "pronunciation": False,
        "voice": False,
    }

    def detect(self, src_text):
        try:
            return "en"
        except Exception as e:
            raise TranslationError(e)

    def translate(self, src_text, src, dest):
        try:
            return Translation(src_text, {})
        except Exception as e:
            raise TranslationError(e)

