class TranslatorBase:
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
