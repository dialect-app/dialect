import httpx
from langdetect import detect_langs, DetectorFactory

from dialect.translators import Detected, TranslatorBase, TranslationError, Translation

DetectorFactory.seed = 0


class LibreTranslator(TranslatorBase):
    client = None
    history = []
    languages = {}
    supported_features = {
        'mistakes': False,
        'pronunciation': False,
        'voice': False,
    }
    url = 'https://libretranslate.com/translate'
    lang_url = 'https://libretranslate.com/languages'

    def __init__(self) -> None:
        super().__init__()
        if self.client is None:
            self.client = httpx.Client()
            r = self.client.get(self.lang_url)
            for lang in r.json():
                self.languages[lang['code']] = lang['name']

    def detect(self, src_text):
        """Detect the language using the same mechanisms that LibreTranslate uses but locally."""
        try:
            candidate_langs = list(
                filter(lambda l: l.lang in self.languages, detect_langs(src_text))
            )

            if len(candidate_langs) > 0:
                candidate_langs.sort(key=lambda l: l.prob, reverse=True)

                source_lang = next(
                    iter(
                        [
                            l
                            for l in self.languages.keys()
                            if l == candidate_langs[0].lang
                        ]
                    ),
                    None,
                )
                if not source_lang:
                    source_lang = 'en'
            else:
                source_lang = 'en'

            detected_object = Detected(source_lang, 1.0)
            return detected_object
        except Exception as e:
            raise TranslationError(e)

    def translate(self, src_text, src, dest):
        try:
            r = self.client.post(
                self.url,
                data={
                    'q': src_text,
                    'source': src,
                    'target': dest,
                },
            )
            return Translation(
                r.json()['translatedText'],
                {
                    'possible-mistakes': None,
                    'translation': [],
                },
            )
        except Exception as e:
            raise TranslationError(e)
