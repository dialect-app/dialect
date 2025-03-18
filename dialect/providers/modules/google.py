# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import html
import json
import random
import re
from tempfile import NamedTemporaryFile

from gtts import gTTS, lang

from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    Translation,
    TranslationMistake,
    TranslationPronunciation,
)
from dialect.providers.errors import UnexpectedError
from dialect.providers.local import LocalProvider
from dialect.providers.soup import SoupProvider

RPC_ID = "MkEWBc"

# Predefined URLs used to make google translate requests.
TRANSLATE_RPC = "{host}/_/TranslateWebserverUi/data/batchexecute"

TRANSLATE_TLDS = (
    ".ac",
    ".ad",
    ".ae",
    ".al",
    ".am",
    ".as",
    ".at",
    ".az",
    ".ba",
    ".be",
    ".bf",
    ".bg",
    ".bi",
    ".bj",
    ".bs",
    ".bt",
    ".by",
    ".ca",
    ".cat",
    ".cc",
    ".cd",
    ".cf",
    ".cg",
    ".ch",
    ".ci",
    ".cl",
    ".cm",
    ".cn",
    ".co.ao",
    ".co.bw",
    ".co.ck",
    ".co.cr",
    ".co.id",
    ".co.il",
    ".co.in",
    ".co.jp",
    ".co.ke",
    ".co.kr",
    ".co.ls",
    ".co.ma",
    ".co.mz",
    ".co.nz",
    ".co.th",
    ".co.tz",
    ".co.ug",
    ".co.uk",
    ".co.uz",
    ".co.ve",
    ".co.vi",
    ".co.za",
    ".co.zm",
    ".co.zw",
    ".com.af",
    ".com.ag",
    ".com.ai",
    ".com.ar",
    ".com.au",
    ".com.bd",
    ".com.bh",
    ".com.bn",
    ".com.bo",
    ".com.br",
    ".com.bz",
    ".com.co",
    ".com.cu",
    ".com.cy",
    ".com.do",
    ".com.ec",
    ".com.eg",
    ".com.et",
    ".com.fj",
    ".com.gh",
    ".com.gi",
    ".com.gt",
    ".com.hk",
    ".com.jm",
    ".com.kh",
    ".com.kw",
    ".com.lb",
    ".com.ly",
    ".com.mm",
    ".com.mt",
    ".com.mx",
    ".com.my",
    ".com.na",
    ".com.ng",
    ".com.ni",
    ".com.np",
    ".com.om",
    ".com.pa",
    ".com.pe",
    ".com.pg",
    ".com.ph",
    ".com.pk",
    ".com.pr",
    ".com.py",
    ".com.qa",
    ".com.sa",
    ".com.sb",
    ".com.sg",
    ".com.sl",
    ".com.sv",
    ".com.tj",
    ".com.tr",
    ".com.tw",
    ".com.ua",
    ".com.uy",
    ".com.vc",
    ".com.vn",
    ".com",
    ".cv",
    ".cz",
    ".de",
    ".dj",
    ".dk",
    ".dm",
    ".dz",
    ".ee",
    ".es",
    ".fi",
    ".fm",
    ".fr",
    ".ga",
    ".ge",
    ".gg",
    ".gl",
    ".gm",
    ".gp",
    ".gr",
    ".gy",
    ".hn",
    ".hr",
    ".ht",
    ".hu",
    ".ie",
    ".im",
    ".iq",
    ".is",
    ".it",
    ".je",
    ".jo",
    ".kg",
    ".ki",
    ".kz",
    ".la",
    ".li",
    ".lk",
    ".lt",
    ".lu",
    ".lv",
    ".md",
    ".me",
    ".mg",
    ".mk",
    ".ml",
    ".mn",
    ".ms",
    ".mu",
    ".mv",
    ".mw",
    ".ne",
    ".nl",
    ".no",
    ".nr",
    ".nu",
    ".pl",
    ".pn",
    ".ps",
    ".pt",
    ".ro",
    ".rs",
    ".ru",
    ".rw",
    ".sc",
    ".se",
    ".sh",
    ".si",
    ".sk",
    ".sm",
    ".sn",
    ".so",
    ".sr",
    ".st",
    ".td",
    ".tg",
    ".tk",
    ".tl",
    ".tm",
    ".tn",
    ".to",
    ".tt",
    ".us",
    ".vg",
    ".vu",
    ".ws",
)


class Provider(LocalProvider, SoupProvider):
    name = "google"
    prettyname = "Google"

    capabilities = ProviderCapability.TRANSLATION | ProviderCapability.TTS
    features = ProviderFeature.DETECTION | ProviderFeature.MISTAKES | ProviderFeature.PRONUNCIATION

    defaults = {
        "instance_url": "",
        "api_key": "",
        "src_langs": ["en", "fr", "es", "de"],
        "dest_langs": ["fr", "es", "de", "en"],
    }

    _headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://translate.google.com",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = 2000

    async def init_trans(self):
        langs_url = self.format_url(
            self._get_translate_host(".com"), "/translate_a/l", {"client": "t", "alpha": "true"}
        )
        response = await self.get(langs_url, self._headers, False)

        try:
            for code, name in response["tl"].items():
                self.add_lang(code, name)
        except Exception as exc:
            raise UnexpectedError from exc

    async def init_tts(self):
        for code in lang.tts_langs().keys():
            self.add_lang(code, trans_src=False, trans_dest=False, tts=True)

    @staticmethod
    def _build_rpc_request(text: str, src: str, dest: str):
        return json.dumps(
            [
                [
                    [
                        RPC_ID,
                        json.dumps([[text, src, dest, True], [None]], separators=(",", ":")),
                        None,
                        "generic",
                    ],
                ]
            ],
            separators=(",", ":"),
        )

    def _get_translate_host(self, tld: str | None = None):
        if not tld:
            tld = random.choice(TRANSLATE_TLDS)
        return f"translate.google{tld}"

    @property
    def translate_url(self):
        url = TRANSLATE_RPC.format(host=self._get_translate_host()) + "?"
        params = {
            "rpcids": RPC_ID,
            "bl": "boq_translate-webserver_20201207.13_p0",
            "soc-app": "1",
            "soc-platform": "1",
            "soc-device": "1",
            "rt": "c",
        }

        return self.format_url(url, params=params)

    async def translate(self, request):
        src_lang, dest_lang = self.denormalize_lang(request.src, request.dest)

        # Form data
        data = {
            "f.req": self._build_rpc_request(request.text, src_lang, dest_lang),
        }

        # Do request
        response = await self.post(self.translate_url, data, self._headers, True, False, False)

        try:
            token_found = False
            square_bracket_counts = [0, 0]
            resp = ""
            data = response.decode("utf-8")

            for line in data.split("\n"):
                token_found = token_found or f'"{RPC_ID}"' in line[:30]
                if not token_found:
                    continue

                is_in_string = False
                for index, char in enumerate(line):
                    if char == '"' and line[max(0, index - 1)] != "\\":
                        is_in_string = not is_in_string
                    if not is_in_string:
                        if char == "[":
                            square_bracket_counts[0] += 1
                        elif char == "]":
                            square_bracket_counts[1] += 1

                resp += line
                if square_bracket_counts[0] == square_bracket_counts[1]:
                    break

            data = json.loads(resp)
            parsed = json.loads(data[0][2])
            translated_parts = None
            translated = None
            try:
                translated_parts = list(
                    map(
                        lambda part: TranslatedPart(
                            part[0] if len(part) > 0 else "", part[1] if len(part) >= 2 else []
                        ),
                        parsed[1][0][0][5],
                    )
                )
            except TypeError:
                translated_parts = [TranslatedPart(parsed[1][0][1][0], [parsed[1][0][0][0], parsed[1][0][1][0]])]

            first_iter = True
            translated = ""
            for part in translated_parts:
                if not part.text.isspace() and not first_iter:
                    translated += " "
                if first_iter:
                    first_iter = False
                translated += part.text

            src = None
            try:
                src = parsed[1][-1][1]
            except (IndexError, TypeError):
                pass

            if not src == src_lang:
                raise UnexpectedError("source language mismatch")

            if src == "auto":
                try:
                    if parsed[0][2] in self.src_languages:
                        src = parsed[0][2]
                except (IndexError, TypeError):
                    pass

            dest = None
            try:
                dest = parsed[1][-1][2]
            except (IndexError, TypeError):
                pass

            if not dest == dest_lang:
                raise UnexpectedError("destination language mismatch")

            origin_pronunciation = None
            try:
                origin_pronunciation = parsed[0][0]
            except (IndexError, TypeError):
                pass

            pronunciation = None
            try:
                pronunciation = parsed[1][0][0][1]
            except (IndexError, TypeError):
                pass

            mistake = None
            try:
                mistake = parsed[0][1][0][0][1]
                # Convert to pango markup
                mistake = mistake.replace("<em>", "<b>").replace("</em>", "</b>")
            except (IndexError, TypeError):
                pass

            return Translation(
                translated,
                request,
                src,
                TranslationMistake(mistake, self._strip_html_tags(mistake)) if mistake else None,
                TranslationPronunciation(origin_pronunciation, pronunciation),
            )

        except Exception as exc:
            raise UnexpectedError from exc

    def _strip_html_tags(self, text: str):
        """Strip html tags"""
        tags_re = re.compile(r"(<!--.*?-->|<[^>]*>)")
        tags_removed = tags_re.sub("", text)
        escaped = html.escape(tags_removed)
        return escaped

    async def speech(self, text, language):
        def get_speech():
            try:
                file = NamedTemporaryFile()
                (lang,) = self.denormalize_lang(language)
                tts = gTTS(text, lang=lang, lang_check=False)
                tts.write_to_fp(file)
                file.seek(0)

                return file
            except Exception:
                raise

        return await self.run_async(get_speech)


class TranslatedPart:
    def __init__(self, text: str, candidates: list[str]):
        self.text = text
        self.candidates = candidates

    def __str__(self):
        return self.text
