# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# Copyright 2023 Libretto
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import re
from typing import Literal, TypedDict

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gst, Gtk, Spelling

from dialect.asyncio import background_task
from dialect.define import APP_ID, PROFILE, RES_PATH, TRANS_NUMBER
from dialect.languages import LanguagesListModel
from dialect.providers import (
    TRANSLATORS,
    TTS,
    APIKeyInvalid,
    APIKeyRequired,
    BaseProvider,
    ProviderError,
    RequestError,
    Translation,
    TranslationRequest,
)
from dialect.settings import Settings
from dialect.shortcuts import DialectShortcutsWindow
from dialect.utils import find_item_match, first_exclude
from dialect.widgets import LangSelector, SpeechButton, TextView, ThemeSwitcher


class _OngoingSpeech(TypedDict):
    text: str
    lang: str
    called_from: Literal["src", "dest"]


class _NotificationAction(TypedDict):
    label: str
    name: str


@Gtk.Template(resource_path=f"{RES_PATH}/window.ui")
class DialectWindow(Adw.ApplicationWindow):
    __gtype_name__ = "DialectWindow"

    # Properties
    translator_loading: bool = GObject.Property(type=bool, default=True)  # type: ignore
    selection_translation_queued: bool = GObject.Property(type=bool, default=False)  # type: ignore

    # Child widgets
    menu_btn: Gtk.MenuButton = Gtk.Template.Child()  # type: ignore
    main_stack: Gtk.Stack = Gtk.Template.Child()  # type: ignore
    error_page: Adw.StatusPage = Gtk.Template.Child()  # type: ignore
    translator_box: Gtk.Box = Gtk.Template.Child()  # type: ignore
    key_page: Adw.StatusPage = Gtk.Template.Child()  # type: ignore
    rmv_key_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore

    langs_button_box: Gtk.Box = Gtk.Template.Child()  # type: ignore
    switch_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    src_lang_selector: LangSelector = Gtk.Template.Child()  # type: ignore
    dest_lang_selector: LangSelector = Gtk.Template.Child()  # type: ignore

    return_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    forward_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore

    src_pron_revealer: Gtk.Revealer = Gtk.Template.Child()  # type: ignore
    src_pron_label: Gtk.Label = Gtk.Template.Child()  # type: ignore
    mistakes: Gtk.Revealer = Gtk.Template.Child()  # type: ignore
    mistakes_label: Gtk.Label = Gtk.Template.Child()  # type: ignore
    char_counter: Gtk.Label = Gtk.Template.Child()  # type: ignore
    src_text: TextView = Gtk.Template.Child()  # type: ignore
    clear_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    paste_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    src_speech_btn: SpeechButton = Gtk.Template.Child()  # type: ignore
    translate_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore

    dest_box: Gtk.Box = Gtk.Template.Child()  # type: ignore
    dest_pron_revealer: Gtk.Revealer = Gtk.Template.Child()  # type: ignore
    dest_pron_label: Gtk.Label = Gtk.Template.Child()  # type: ignore
    dest_text: TextView = Gtk.Template.Child()  # type: ignore
    dest_toolbar_stack: Gtk.Stack = Gtk.Template.Child()  # type: ignore
    trans_spinner: Adw.Spinner = Gtk.Template.Child()  # type: ignore
    trans_warning: Gtk.Image = Gtk.Template.Child()  # type: ignore
    edit_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    copy_btn: Gtk.Button = Gtk.Template.Child()  # type: ignore
    dest_speech_btn: SpeechButton = Gtk.Template.Child()  # type: ignore

    toast: Adw.Toast | None = None  # for notification management
    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()  # type: ignore

    win_key_ctrlr: Gtk.EventControllerKey = Gtk.Template.Child()  # type: ignore

    # Providers objects
    provider: dict[str, BaseProvider | None] = {"trans": None, "tts": None}

    # Text to speech
    speech_provider_failed = False  # tts provider loading failed
    current_speech: _OngoingSpeech | None = None
    speech_loading = False  # tts loading status

    # Preset language values
    src_langs: list[str] = []
    dest_langs: list[str] = []

    current_history = 0  # for history management

    # Translation-related variables
    selection_translation_langs: tuple[str | None, str | None] = (None, None)
    next_translation: TranslationRequest | None = None  # for ongoing translation
    translation_loading = False  # for ongoing translation

    # Suggestions
    before_suggest: str | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Application object
        self.app: Adw.Application = kwargs["application"]

        # GStreamer playbin object and related setup
        self.player = Gst.ElementFactory.make("playbin", "player")
        if self.player:
            if bus := self.player.get_bus():
                bus.add_signal_watch()
                bus.connect("message", self._on_gst_message)

        # Setup window
        self.setup_actions()
        self.setup()

    def setup_actions(self):
        back = Gio.SimpleAction(name="back")
        back.props.enabled = False
        back.connect("activate", self._on_back_action)
        self.add_action(back)

        forward_action = Gio.SimpleAction(name="forward")
        forward_action.props.enabled = False
        forward_action.connect("activate", self._on_forward_action)
        self.add_action(forward_action)

        switch_action = Gio.SimpleAction(name="switch")
        switch_action.connect("activate", self._on_switch_action)
        self.add_action(switch_action)

        from_action = Gio.SimpleAction(name="from")
        from_action.connect("activate", self._on_from_action)
        self.add_action(from_action)

        to_action = Gio.SimpleAction(name="to")
        to_action.connect("activate", self._on_to_action)
        self.add_action(to_action)

        clear_action = Gio.SimpleAction(name="clear")
        clear_action.props.enabled = False
        clear_action.connect("activate", self._on_clear_action)
        self.add_action(clear_action)

        font_size_inc_action = Gio.SimpleAction(name="font-size-inc")
        font_size_inc_action.connect("activate", self._on_font_size_inc_action)
        self.add_action(font_size_inc_action)

        font_size_dec_action = Gio.SimpleAction(name="font-size-dec")
        font_size_dec_action.connect("activate", self._on_font_size_dec_action)
        self.add_action(font_size_dec_action)

        paste_action = Gio.SimpleAction(name="paste")
        paste_action.connect("activate", self._on_paste_action)
        self.add_action(paste_action)

        copy_action = Gio.SimpleAction(name="copy")
        copy_action.props.enabled = False
        copy_action.connect("activate", self._on_copy_action)
        self.add_action(copy_action)

        listen_dest_action = Gio.SimpleAction(name="listen-dest")
        listen_dest_action.connect("activate", self._on_dest_listen_action)
        listen_dest_action.props.enabled = False
        self.add_action(listen_dest_action)

        suggest_action = Gio.SimpleAction(name="suggest")
        suggest_action.props.enabled = False
        suggest_action.connect("activate", self._on_suggest_action)
        self.add_action(suggest_action)

        suggest_ok_action = Gio.SimpleAction(name="suggest-ok")
        suggest_ok_action.connect("activate", self._on_suggest_ok_action)
        self.add_action(suggest_ok_action)

        suggest_cancel_action = Gio.SimpleAction(name="suggest-cancel")
        suggest_cancel_action.connect("activate", self._on_suggest_cancel_action)
        self.add_action(suggest_cancel_action)

        listen_src_action = Gio.SimpleAction(name="listen-src")
        listen_src_action.connect("activate", self._on_src_listen_action)
        listen_src_action.props.enabled = False
        self.add_action(listen_src_action)

        translation_action = Gio.SimpleAction(name="translation")
        translation_action.props.enabled = False
        translation_action.connect("activate", self._on_translation)
        self.add_action(translation_action)

    def setup(self):
        self.set_default_icon_name(APP_ID)

        # Set devel style
        if PROFILE == "Devel":
            self.add_css_class("devel")

        # Theme Switcher
        theme_switcher = ThemeSwitcher()
        menu: Gtk.PopoverMenu = self.menu_btn.props.popover  # type: ignore
        menu.add_child(theme_switcher, "theme")

        # Save settings on close
        self.connect("unrealize", self.save_settings)

        self.setup_selectors()
        self.setup_translation()
        self.setup_spell_checking()
        self.set_help_overlay(DialectShortcutsWindow())

        # Load translator
        self.load_translator()
        # Load text to speech
        self.load_tts()

        # Listen to active providers changes
        Settings.get().connect("provider-changed", self._on_active_provider_changed)

        # Bind text views font size
        self.src_text.bind_property("font-size", self.dest_text, "font-size", GObject.BindingFlags.BIDIRECTIONAL)

        # Set initial saved text view font size
        if Settings.get().custom_default_font_size:
            font_size = Settings.get().default_font_size
            self.set_font_size(font_size)

        # Set src textview mod key requirement
        self.src_text.activate_mod = not bool(Settings.get().translate_accel_value)
        Settings.get().connect(
            "changed::translate-accel",
            lambda s, _k: self.src_text.set_property("activate_mod", not bool(s.translate_accel_value)),
        )

    def setup_spell_checking(self):
        # Enable spell-checking
        self.spell_checker: Spelling.Checker = Spelling.Checker.get_default()
        spell_checker_adapter = Spelling.TextBufferAdapter.new(self.src_buffer, self.spell_checker)
        spell_checker_menu = spell_checker_adapter.get_menu_model()
        self.src_text.set_extra_menu(spell_checker_menu)
        self.src_text.insert_action_group("spelling", spell_checker_adapter)
        spell_checker_adapter.set_enabled(True)

        # Collect the spell checking provider's supported languages.
        self.spell_checker_supported_languages = {}
        for lang_object in self.spell_checker.get_provider().list_languages():
            lang_code = lang_object.get_code()
            lang_base_code = re.split("_|-", lang_code)[0]
            if lang_base_code not in self.spell_checker_supported_languages:
                self.spell_checker_supported_languages[lang_base_code] = []
            self.spell_checker_supported_languages[lang_base_code].append(lang_code)

    def setup_selectors(self):
        def lang_names_func(code: str):
            return self.provider["trans"].get_lang_name(code)  # type: ignore

        # Languages models
        self.src_lang_model = LanguagesListModel(lang_names_func)
        self.src_recent_lang_model = LanguagesListModel(lang_names_func)
        self.dest_lang_model = LanguagesListModel(lang_names_func)
        self.dest_recent_lang_model = LanguagesListModel(lang_names_func)

        # Src lang selector
        self.src_lang_selector.bind_models(self.src_lang_model, self.src_recent_lang_model)
        # Dest lang selector
        self.dest_lang_selector.bind_models(self.dest_lang_model, self.dest_recent_lang_model)

    def setup_translation(self):
        # Src buffer
        self.src_buffer = self.src_text.props.buffer
        self.src_buffer.connect("changed", self._on_src_text_changed)
        self.src_buffer.connect("end-user-action", self._on_user_action_ended)

        # Dest buffer
        self.dest_buffer = self.dest_text.props.buffer
        self.dest_buffer.props.text = ""
        self.dest_buffer.connect("changed", self._on_dest_text_changed)

        # Translation progress
        self.trans_spinner.hide()
        self.trans_warning.hide()

    def reload_provider(self, kind: str):
        match kind:
            case "translator":
                self.load_translator()
            case "tts":
                self.load_tts()

    @background_task
    async def load_translator(self):
        self.translator_loading = True

        provider = Settings.get().active_translator

        # Show loading view
        self.main_stack.props.visible_child_name = "loading"

        # Translator object
        self.provider["trans"] = TRANSLATORS[provider]()
        # Get saved languages
        self.src_langs = self.provider["trans"].recent_src_langs
        self.dest_langs = self.provider["trans"].recent_dest_langs
        # Connect to provider settings changes
        self.provider["trans"].settings.connect(
            "changed::instance-url", self._on_provider_changed, self.provider["trans"].name
        )
        self.provider["trans"].settings.connect(
            "changed::api-key", self._on_provider_changed, self.provider["trans"].name
        )

        try:
            # Do provider init
            await self.provider["trans"].init_trans()

            # Update navigation UI
            self._check_navigation_enabled()
            # Check mistakes support
            self._check_mistakes()
            # Check pronunciation support
            self._check_pronunciation()
            # Check suggestions support and update UI
            self._on_suggest_cancel_action()
            self.edit_btn.props.visible = self.provider["trans"].supports_suggestions

            # Update langs
            self.src_lang_model.set_langs(self.provider["trans"].src_languages)
            self.dest_lang_model.set_langs(self.provider["trans"].dest_languages)

            # Update selected langs
            set_auto = Settings.get().src_auto and self.provider["trans"].supports_detection
            src_lang = self.provider["trans"].src_languages[0]
            if self.src_langs and self.src_langs[0] in self.provider["trans"].src_languages:
                src_lang = self.src_langs[0]
            self.src_lang_selector.selected = "auto" if set_auto else src_lang

            dest_lang = self.provider["trans"].dest_languages[1]
            if self.dest_langs and self.dest_langs[0] in self.provider["trans"].dest_languages:
                dest_lang = self.dest_langs[0]
            self.dest_lang_selector.selected = dest_lang

            # Update chars limit
            if self.provider["trans"].chars_limit == -1:  # -1 means unlimited
                self.char_counter.props.label = ""
            else:
                count = f"{str(self.src_buffer.get_char_count())}/{self.provider['trans'].chars_limit}"
                self.char_counter.props.label = count

            # Check API key
            if self.provider["trans"].supports_api_key:
                if self.provider["trans"].api_key:
                    try:
                        if await self.provider["trans"].validate_api_key(self.provider["trans"].api_key):
                            self.main_stack.props.visible_child_name = "translate"
                        else:
                            self.show_translator_api_key_view()
                    except ProviderError or RequestError as exc:
                        logging.error(exc, exc_info=exc)
                        self.show_translator_error_view(detail=str(exc))
                elif not self.provider["trans"].api_key and self.provider["trans"].api_key_required:
                    self.show_translator_api_key_view(required=True)
                else:
                    self.main_stack.props.visible_child_name = "translate"
            else:
                self.main_stack.props.visible_child_name = "translate"

        # Loading failed
        except (RequestError, ProviderError) as exc:
            logging.error(exc)

            # API key error
            if isinstance(exc, APIKeyRequired):
                self.show_translator_api_key_view(required=True)
            elif isinstance(exc, APIKeyInvalid):
                self.show_translator_api_key_view()

            # Other errors
            else:
                service = self.provider["trans"].prettyname
                url = self.provider["trans"].instance_url
                detail = str(exc)

                if isinstance(exc, RequestError):
                    title = _("Couldn’t connect to the translation service")
                    description = _("We can’t connect to the server. Please check for network issues.")
                    if self.provider["trans"].supports_instances:
                        description = _(
                            (
                                "We can’t connect to the {service} instance “{url}“.\n"
                                "Please check for network issues or if the address is correct."
                            )
                        ).format(service=service, url=url)
                    self.show_translator_error_view(title, description, detail)
                elif self.provider["trans"].supports_instances:
                    description = _(
                        (
                            "Failed loading “{url}“, check if the instance address is correct or report in the Dialect bug tracker"
                            " if the issue persists."
                        )
                    ).format(url=url)
                    self.show_translator_error_view(description=description, detail=detail)
                else:
                    self.show_translator_error_view(detail=detail)

        finally:
            self.translator_loading = False

    def show_translator_error_view(
        self,
        title: str = _("Failed loading the translation service"),
        description: str = _("Please report this in the Dialect bug tracker if the issue persists."),
        detail: str | None = None,
    ):
        if detail:  # Add detail bellow description
            if description:
                description += "\n\n"
            description += "<small><tt>" + detail + "</tt></small>"

        self.error_page.props.title = title
        self.error_page.props.description = description

        self.main_stack.props.visible_child_name = "error"

    def show_translator_api_key_view(self, required=False):
        if not self.provider["trans"]:
            return

        if required:
            self.key_page.props.title = _("API key is required to use the service")
            self.key_page.props.description = _("Please set an API key in the preferences.")

        else:
            self.key_page.props.title = _("The provided API key is invalid")
            if self.provider["trans"].api_key_required:
                self.key_page.props.description = _("Please set a valid API key in the preferences.")
            else:
                self.key_page.props.description = _(
                    "Please set a valid API key or unset the API key in the preferences."
                )
                self.rmv_key_btn.props.visible = True

        self.main_stack.props.visible_child_name = "api-key"

    @background_task
    async def load_tts(self):
        self.src_speech_btn.loading()
        self.dest_speech_btn.loading()

        # TTS name
        provider = Settings.get().active_tts

        # Check if TTS is disabled
        if provider != "":
            self.src_speech_btn.props.visible = True
            self.dest_speech_btn.props.visible = True

            # TTS Object
            self.provider["tts"] = TTS[provider]()
            # Connect to provider settings changes
            self.provider["tts"].settings.connect(
                "changed::instance-url", self._on_provider_changed, self.provider["tts"].name
            )
            self.provider["tts"].settings.connect(
                "changed::api-key", self._on_provider_changed, self.provider["tts"].name
            )

            try:
                # Do TTS init
                await self.provider["tts"].init_tts()

                self.speech_provider_failed = False
                self.src_speech_btn.ready()
                self.dest_speech_btn.ready()
                self._check_speech_enabled()

            # Loading failed
            except (RequestError, ProviderError) as exc:
                logging.error(exc)

                button_text = _("Failed loading the text-to-speech service. Retry?")
                toast_text = _("Failed loading the text-to-speech service")
                if isinstance(exc, RequestError):
                    toast_text = _("Failed loading the text-to-speech service, check for network issues")

                self.speech_provider_failed = True
                self.src_speech_btn.error(button_text)
                self.dest_speech_btn.error(button_text)
                self.send_notification(toast_text)
                self._check_speech_enabled()

        else:
            self.provider["tts"] = None
            self.src_speech_btn.props.visible = False
            self.dest_speech_btn.props.visible = False

    def translate(self, text: str, src_lang: str | None, dest_lang: str | None):
        """
        Translates the given text from auto detected language to last used
        language
        """
        if not self.provider["trans"]:
            return

        # Set src lang to Auto
        if src_lang is None:
            self.src_lang_selector.selected = "auto"
        else:
            self.src_lang_selector.selected = src_lang
        if dest_lang is not None and dest_lang in self.provider["trans"].dest_languages:
            self.dest_lang_selector.selected = dest_lang
            self.dest_lang_selector.emit("user-selection-changed")
        # Set text to src buffer
        self.src_buffer.props.text = text
        # Run translation
        self._on_translation()

    @background_task
    async def translate_selection(self, src_lang: str | None, dest_lang: str | None):
        """Runs `translate` with the selection clipboard text"""
        if display := Gdk.Display.get_default():
            clipboard = display.get_primary_clipboard()
            try:
                if text := await clipboard.read_text_async():  # type: ignore
                    self.translate(text, src_lang, dest_lang)
            except GLib.Error as exc:
                logging.error(exc)
                self.send_notification(_("Couldn’t read selection clip board!"))

    def queue_selection_translation(self, src_lang: str | None, dest_lang: str | None):
        """Call `translate_selection` or queue it until the window is focused"""
        if self.props.is_active:
            self.translate_selection(src_lang, dest_lang)
        else:
            self.selection_translation_queued = True
            self.selection_translation_langs = (src_lang, dest_lang)

    def save_settings(self, *args, **kwargs):
        if not self.is_maximized():
            size = self.get_default_size()
            Settings.get().window_size = (size.width, size.height)  # type: ignore
        if self.provider["trans"] is not None:
            self.provider["trans"].recent_src_langs = self.src_langs
            self.provider["trans"].recent_dest_langs = self.dest_langs

    def send_notification(
        self,
        text: str,
        queue: bool | None = False,
        action: _NotificationAction | None = None,
        timeout=5,
        priority=Adw.ToastPriority.NORMAL,
    ):
        """
        Display an in-app notification.

        Args:
            text: The text or message of the notification.
            queue: If True, the notification will be queued.
            action: A dict containing the action to be called.
            timeout: Toast timeout.
            timeout: Toast priority.
        """

        def toast_dismissed(_toast: Adw.Toast):
            self.toast = None

        if not queue and self.toast is not None:
            self.toast.dismiss()
        self.toast = Adw.Toast(title=text)
        self.toast.connect("dismissed", toast_dismissed)
        if action is not None:
            self.toast.props.button_label = action["label"]
            self.toast.props.action_name = action["name"]
        self.toast.props.timeout = timeout
        self.toast.props.priority = priority
        self.toast_overlay.add_toast(self.toast)

    def set_font_size(self, size: int):
        self.src_text.font_size = size

    def add_history_entry(self, translation: Translation):
        """Add a history entry to the history list."""
        if not self.provider["trans"]:
            return

        if self.current_history > 0:
            del self.provider["trans"].history[: self.current_history]
            self.current_history = 0
        if len(self.provider["trans"].history) == TRANS_NUMBER:
            self.provider["trans"].history.pop()
        self.provider["trans"].history.insert(0, translation)
        self._check_navigation_enabled()

    @property
    def current_translation(self) -> Translation | None:
        """Get the current active translation, respecting the history navigation"""
        if not self.provider["trans"]:
            return None

        try:
            return self.provider["trans"].history[self.current_history]
        except IndexError:
            return None

    def _check_navigation_enabled(self):
        self.lookup_action("back").props.enabled = self.current_history < len(self.provider["trans"].history) - 1  # type: ignore
        self.lookup_action("forward").props.enabled = self.current_history > 0  # type: ignore

    def _check_mistakes(self):
        if not self.provider["trans"]:
            return

        translation = self.current_translation
        if self.provider["trans"].supports_mistakes and translation and translation.mistakes:
            self.mistakes_label.set_markup(_("Did you mean: ") + f'<a href="#">{translation.mistakes.markup}</a>')
            self.mistakes.props.reveal_child = True
        elif self.mistakes.props.reveal_child:
            self.mistakes.props.reveal_child = False

    def _check_pronunciation(self):
        if not self.provider["trans"]:
            return

        if not self.provider["trans"].supports_pronunciation:
            self.src_pron_revealer.props.reveal_child = False
            self.dest_pron_revealer.props.reveal_child = False
            self.app.lookup_action("pronunciation").props.enabled = False  # type: ignore
        else:
            self.app.lookup_action("pronunciation").props.enabled = True  # type: ignore
            reveal = Settings.get().show_pronunciation
            translation = self.current_translation

            if translation and translation.pronunciation.src and not translation.mistakes:
                self.src_pron_label.props.label = translation.pronunciation.src
                self.src_pron_revealer.props.reveal_child = reveal
            elif self.src_pron_revealer.props.reveal_child:
                self.src_pron_revealer.props.reveal_child = False

            if translation and translation.pronunciation.dest:
                self.dest_pron_label.props.label = translation.pronunciation.dest
                self.dest_pron_revealer.props.reveal_child = reveal
            elif self.dest_pron_revealer.props.reveal_child:
                self.dest_pron_revealer.props.reveal_child = False

    def _check_speech_enabled(self):
        if not self.provider["tts"]:
            return

        src_playing = dest_playing = False
        if self.current_speech:
            src_playing = self.current_speech["called_from"] == "src"
            dest_playing = self.current_speech["called_from"] == "dest"

        # Check src listen button
        self.lookup_action("listen-src").set_enabled(  # type: ignore
            self.speech_provider_failed
            or self.src_lang_selector.selected in self.provider["tts"].tts_languages
            and self.src_buffer.get_char_count() != 0
            and not self.speech_loading
            and not dest_playing
        )

        # Check dest listen button
        self.lookup_action("listen-dest").set_enabled(  # type: ignore
            self.speech_provider_failed
            or self.dest_lang_selector.selected in self.provider["tts"].tts_languages
            and self.dest_buffer.get_char_count() != 0
            and not self.speech_loading
            and not src_playing
        )

    def _check_switch_enabled(self):
        if not self.provider["trans"]:
            return

        # Disable or enable switch function.
        self.lookup_action("switch").props.enabled = (  # type: ignore
            self.src_lang_selector.selected in self.provider["trans"].dest_languages
            and self.dest_lang_selector.selected in self.provider["trans"].src_languages
        )

    def _pick_spell_checking_language(self, lang_code: str):
        # Try and set the correct language if available.
        lang_base_code = lang_code.split("-")[0]
        default_user_lang_code = self.spell_checker.get_provider().get_default_code()

        spell_checker_lang_code = default_user_lang_code  # Default to the user's preference

        if lang_base_code in self.spell_checker_supported_languages:
            if lang_code in self.spell_checker_supported_languages[lang_base_code]:
                # The language is matched exactly.
                spell_checker_lang_code = lang_code
            elif (code := lang_code.replace("-", "_")) in self.spell_checker_supported_languages[lang_base_code]:
                # The language code needs underscores within the provider.
                spell_checker_lang_code = code
            elif default_user_lang_code.startswith(lang_base_code):
                # Default to user preference if at least the base language code matches.
                # Probably the most common scenario: en -> en_US.
                spell_checker_lang_code = default_user_lang_code
            else:
                # Try to set the language even if the country code doesn't match, to the first available one.
                spell_checker_lang_code = self.spell_checker_supported_languages[lang_base_code][0]

        self.spell_checker.set_language(spell_checker_lang_code)

    """
    User interface functions
    """

    def _on_back_action(self, *_args):
        """Go back one step in history."""
        if self.current_history != TRANS_NUMBER:
            self.current_history += 1
            self._history_update()

    def _on_forward_action(self, *_args):
        """Go forward one step in history."""
        if self.current_history != 0:
            self.current_history -= 1
            self._history_update()

    def _history_update(self):
        if not self.provider["trans"]:
            return

        if translation := self.current_translation:
            self.src_lang_selector.selected = translation.original.src
            self.dest_lang_selector.selected = translation.original.dest
            self.src_buffer.props.text = translation.original.text
            self.dest_buffer.props.text = translation.text

            self._check_navigation_enabled()
            self._check_mistakes()
            self._check_pronunciation()

    def _on_switch_action(self, *_args):
        # Get variables
        self.langs_button_box.props.sensitive = False
        self.lookup_action("translation").props.enabled = False  # type: ignore
        src_language = self.src_lang_selector.selected
        dest_language = self.dest_lang_selector.selected
        src_text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)
        dest_text = self.dest_buffer.get_text(self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True)
        if src_language == "auto":
            return

        # Switch all
        self.src_lang_selector.selected = dest_language
        self.dest_lang_selector.selected = src_language
        self.src_buffer.props.text = dest_text
        self.dest_buffer.props.text = src_text
        self.add_history_entry(Translation(src_text, TranslationRequest(dest_text, src_language, dest_language)))

        # Re-enable widgets
        self.langs_button_box.props.sensitive = True
        self.lookup_action("translation").props.enabled = self.src_buffer.get_char_count() != 0  # type: ignore

    def _on_from_action(self, *_args):
        self.src_lang_selector.button.popup()

    def _on_to_action(self, *_args):
        self.dest_lang_selector.button.popup()

    def _on_clear_action(self, *_args):
        self.src_buffer.props.text = ""
        self.src_buffer.emit("end-user-action")

    def _on_font_size_inc_action(self, *_args):
        self.src_text.font_size_inc()

    def _on_font_size_dec_action(self, *_args):
        self.src_text.font_size_dec()

    def _on_copy_action(self, *_args):
        dest_text = self.dest_buffer.get_text(self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True)
        if display := Gdk.Display.get_default():
            display.get_clipboard().set(dest_text)
            self.send_notification(_("Copied to clipboard"), timeout=1)

    @background_task
    async def _on_paste_action(self, *_args):
        if display := Gdk.Display.get_default():
            clipboard = display.get_clipboard()
            if text := await clipboard.read_text_async():  # type: ignore
                end_iter = self.src_buffer.get_end_iter()
                self.src_buffer.insert(end_iter, text)
                self.src_buffer.emit("end-user-action")

    def _on_suggest_action(self, *_args):
        self.dest_toolbar_stack.props.visible_child_name = "edit"
        self.before_suggest = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True
        )
        self.dest_text.props.editable = True

    @background_task
    async def _on_suggest_ok_action(self, *_args):
        if not self.provider["trans"]:
            return

        try:
            dest_text = self.dest_buffer.get_text(
                self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True
            )
            if translation := self.current_translation:
                if await self.provider["trans"].suggest(
                    translation.original.text, translation.original.src, translation.original.dest, dest_text
                ):
                    self.send_notification(_("New translation has been suggested!"))
                else:
                    self.send_notification(_("Suggestion failed."))

        except (RequestError, ProviderError) as exc:
            logging.error(exc)
            self.send_notification(_("Suggestion failed."))

        finally:
            self.dest_toolbar_stack.props.visible_child_name = "default"
            self.dest_text.props.editable = False
            self.before_suggest = None

    def _on_suggest_cancel_action(self, *_args):
        self.dest_toolbar_stack.props.visible_child_name = "default"
        if self.before_suggest is not None:
            self.dest_buffer.props.text = self.before_suggest
            self.before_suggest = None
        self.dest_text.props.editable = False

    def _on_src_listen_action(self, *_args):
        if self.current_speech:
            self._speech_reset()
            return

        src_text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)
        src_language = self.src_lang_selector.selected
        self._on_speech(src_text, src_language, "src")

    def _on_dest_listen_action(self, *_args):
        if self.current_speech:
            self._speech_reset()
            return

        dest_text = self.dest_buffer.get_text(self.dest_buffer.get_start_iter(), self.dest_buffer.get_end_iter(), True)
        dest_language = self.dest_lang_selector.selected
        self._on_speech(dest_text, dest_language, "dest")

    @background_task
    async def _on_speech(self, text: str, lang: str, called_from: Literal["src", "dest"]):
        # Retry loading TTS provider
        if self.speech_provider_failed:
            self.load_tts()
            return

        if not text or not self.provider["tts"] or not self.player:
            return

        # Set loading state and current speech to update UI
        self.speech_loading = True
        self.current_speech = {"text": text, "lang": lang, "called_from": called_from}
        self._check_speech_enabled()

        if called_from == "src":  # Show spinner on button
            self.src_speech_btn.loading()
        else:
            self.dest_speech_btn.loading()

        # Download speech
        try:
            file_ = await self.provider["tts"].speech(self.current_speech["text"], self.current_speech["lang"])
            uri = "file://" + file_.name
            self.player.set_property("uri", uri)
            self.player.set_state(Gst.State.PLAYING)
            self.add_tick_callback(self._gst_progress_timeout)
            file_.close()

        except (RequestError, ProviderError) as exc:
            logging.error(exc)

            text = _("Text-to-Speech failed")
            action: _NotificationAction | None = None

            if isinstance(exc, RequestError):
                text = _("Text-to-Speech failed, check for network issues")

            if self.current_speech:
                called_from = self.current_speech["called_from"]
                action = {
                    "label": _("Retry"),
                    "name": "win.listen-src" if called_from == "src" else "win.listen-dest",
                }

                button_text = _("Text-to-Speech failed. Retry?")
                if called_from == "src":
                    self.src_speech_btn.error(button_text)
                else:
                    self.dest_speech_btn.error(button_text)

            self.send_notification(text, action=action)
            self._speech_reset(False)

    def _speech_reset(self, set_ready: bool = True):
        if not self.player:
            return

        self.player.set_state(Gst.State.NULL)
        self.current_speech = None
        self.speech_loading = False
        self._check_speech_enabled()

        if set_ready:
            self.src_speech_btn.ready()
            self.dest_speech_btn.ready()

    def _on_gst_message(self, _bus, message: Gst.Message):
        if message.type == Gst.MessageType.EOS or message.type == Gst.MessageType.ERROR:
            if message.type == Gst.MessageType.ERROR:
                logging.error("Some error occurred while trying to play.")
            self._speech_reset()

    def _gst_progress_timeout(self, _widget, _clock):
        if not self.player:
            return False

        if self.current_speech and self.player.get_state(Gst.CLOCK_TIME_NONE) != Gst.State.NULL:
            have_pos, pos = self.player.query_position(Gst.Format.TIME)
            have_dur, dur = self.player.query_duration(Gst.Format.TIME)

            if have_pos and have_dur:
                if self.current_speech["called_from"] == "src":
                    self.src_speech_btn.progress(pos / dur)
                else:
                    self.dest_speech_btn.progress(pos / dur)

                if self.speech_loading:
                    self.speech_loading = False
                    self._check_speech_enabled()

            return True

        return False

    def _on_src_text_changed(self, buffer: Gtk.TextBuffer):
        if not self.provider["trans"]:
            return

        char_count = buffer.get_char_count()

        # If the text is over the highest number of characters allowed, it is truncated.
        # This is done for avoiding exceeding the limit imposed by translation services.
        if self.provider["trans"].chars_limit == -1:  # -1 means unlimited
            self.char_counter.props.label = ""
        else:
            self.char_counter.props.label = f"{str(char_count)}/{self.provider['trans'].chars_limit}"

            if char_count >= self.provider["trans"].chars_limit:
                self.send_notification(_("{} characters limit reached!").format(self.provider["trans"].chars_limit))
                buffer.delete(buffer.get_iter_at_offset(self.provider["trans"].chars_limit), buffer.get_end_iter())

        sensitive = char_count != 0
        self.lookup_action("translation").props.enabled = sensitive  # type: ignore
        self.lookup_action("clear").props.enabled = sensitive  # type: ignore
        self._check_speech_enabled()

    def _on_dest_text_changed(self, buffer: Gtk.TextBuffer):
        if not self.provider["trans"]:
            return

        sensitive = buffer.get_char_count() != 0
        self.lookup_action("copy").props.enabled = sensitive  # type: ignore
        self.lookup_action("suggest").set_enabled(  # type: ignore
            self.provider["trans"].supports_suggestions and sensitive
        )
        self._check_speech_enabled()

    def _on_user_action_ended(self, _buffer):
        if Settings.get().live_translation:
            self._on_translation()

    @Gtk.Template.Callback()
    def _on_is_active_changed(self, *_args):
        if self.selection_translation_queued and self.props.is_active:
            src, dest = self.selection_translation_langs
            self.selection_translation_queued = False
            self.selection_translation_langs = (None, None)
            self.translate_selection(src, dest)

    @Gtk.Template.Callback()
    def _on_retry_load_translator_clicked(self, *_args):
        self.reload_provider("translator")

    @Gtk.Template.Callback()
    def _on_remove_key_and_reload_clicked(self, *_args):
        if self.provider["trans"]:
            self.provider["trans"].reset_api_key()
        self.reload_provider("translator")

    @Gtk.Template.Callback()
    def _on_src_lang_changed(self, *_args):
        """Called on self.src_lang_selector::notify::selected signal"""
        if not self.provider["trans"]:
            return

        code = self.src_lang_selector.selected
        dest_code = self.dest_lang_selector.selected

        if self.provider["trans"].cmp_langs(code, dest_code):
            # Get first lang from saved src langs that is not current dest
            if valid := first_exclude(self.src_langs, dest_code):
                # Check if it's a valid dest lang
                valid = find_item_match([valid], self.provider["trans"].dest_languages)
            if not valid:  # If not, just get the first lang from the list that is not selected
                valid = first_exclude(self.provider["trans"].dest_languages, dest_code)

            self.dest_lang_selector.selected = valid or ""

        if code in self.provider["trans"].src_languages:
            # Update saved src langs list
            if code in self.src_langs:
                # Bring lang to the top
                self.src_langs.remove(code)
            elif code.lower() in self.src_langs:
                # Bring lang to the top
                self.src_langs.remove(code.lower())
            elif len(self.src_langs) == 4:
                self.src_langs.pop()
            self.src_langs.insert(0, code)

        # Try to set the language in the spell checker.
        self._pick_spell_checking_language(code)

        # Rewrite recent langs
        self.src_recent_lang_model.set_langs(self.src_langs, auto=True)

        self._check_switch_enabled()
        self._check_speech_enabled()

    @Gtk.Template.Callback()
    def _on_dest_lang_changed(self, *_args):
        """Called on self.dest_lang_selector::notify::selected signal"""
        if not self.provider["trans"]:
            return

        code = self.dest_lang_selector.selected
        src_code = self.src_lang_selector.selected

        if self.provider["trans"].cmp_langs(code, src_code):
            # Get first lang from saved dest langs that is not current src
            if valid := first_exclude(self.dest_langs, src_code):
                # Check if it's a valid src lang
                valid = find_item_match([valid], self.provider["trans"].src_languages)
            if not valid:  # If not, just get the first lang from the list that is not selected
                valid = first_exclude(self.provider["trans"].src_languages, src_code)

            self.src_lang_selector.selected = valid or ""

        # Update saved dest langs list
        if code in self.dest_langs:
            # Bring lang to the top
            self.dest_langs.remove(code)
        elif code.lower() in self.dest_langs:
            # Bring lang to the top
            self.dest_langs.remove(code.lower())
        elif len(self.src_langs) == 4:
            self.dest_langs.pop()
        self.dest_langs.insert(0, code)

        # Rewrite recent langs
        self.dest_recent_lang_model.set_langs(self.dest_langs)

        self._check_switch_enabled()
        self._check_speech_enabled()

    @Gtk.Template.Callback()
    def _on_key_event(self, _ctrl, keyval: int, _keycode: int, state: Gdk.ModifierType):
        """Called on self.win_key_ctrlr::key-pressed signal"""
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        unicode_key_val = Gdk.keyval_to_unicode(keyval)
        if (
            GLib.unichar_isgraph(chr(unicode_key_val))
            and modifiers in (shift_mask, 0)
            and not self.dest_text.props.editable
            and not self.src_text.is_focus()
        ):
            self.src_text.grab_focus()
            end_iter = self.src_buffer.get_end_iter()
            self.src_buffer.insert(end_iter, chr(unicode_key_val))
            return Gdk.EVENT_STOP
        return Gdk.EVENT_PROPAGATE

    @Gtk.Template.Callback()
    def _on_src_activated(self, _texview):
        """Called on self.src_text::active signal"""
        if not Settings.get().live_translation:
            self._on_translation()

    @Gtk.Template.Callback()
    def _on_mistakes_clicked(self, *_args):
        """Called on self.mistakes_label::activate-link signal"""
        self.mistakes.props.reveal_child = False

        translation = self.current_translation
        if translation and translation.mistakes:
            self.src_buffer.props.text = translation.mistakes.text
            # Ensure we're in the same languages
            self.src_lang_selector.selected = translation.original.src
            self.dest_lang_selector.selected = translation.original.dest

        # Run translation again
        self._on_translation()

        return Gdk.EVENT_STOP

    @Gtk.Template.Callback()
    @background_task
    async def _on_translation(self, *_args):
        if not self.provider["trans"] or self._appeared_before():
            # If it's like the last translation then it's useless to continue
            return

        # Run translation
        if self.next_translation:
            request = self.next_translation
            self.next_translation = None
        else:
            text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)
            request = TranslationRequest(text, self.src_lang_selector.selected, self.dest_lang_selector.selected)

            if self.translation_loading:
                self.next_translation = request
                return

        # Show feedback for start of translation.
        self.trans_spinner.show()
        self.dest_box.props.sensitive = False
        self.langs_button_box.props.sensitive = False

        # If the two languages are the same, nothing is done
        if request.src != request.dest and request.text != "":
            self.translation_loading = True

            try:
                translation = await self.provider["trans"].translate(request)

                if translation.detected and self.src_lang_selector.selected == "auto":
                    if Settings.get().src_auto:
                        self.src_lang_selector.set_insight(
                            self.provider["trans"].normalize_lang_code(translation.detected)
                        )
                    else:
                        self.src_lang_selector.selected = translation.detected

                self.dest_buffer.props.text = translation.text

                # Finally, translation is saved in history
                self.add_history_entry(translation)

                self._check_mistakes()
                self._check_pronunciation()

            # Translation failed
            except (RequestError, ProviderError) as exc:
                self.trans_warning.props.visible = True
                self.lookup_action("copy").props.enabled = False  # type: ignore
                self.lookup_action("listen-src").props.enabled = False  # type: ignore
                self.lookup_action("listen-dest").props.enabled = False  # type: ignore

                if isinstance(exc, RequestError):
                    self.send_notification(
                        _("Translation failed, check for network issues"),
                        action={
                            "label": _("Retry"),
                            "name": "win.translation",
                        },
                    )
                elif isinstance(exc, APIKeyInvalid):
                    self.send_notification(
                        _("The provided API key is invalid"),
                        action={
                            "label": _("Retry"),
                            "name": "win.translation",
                        },
                    )
                elif isinstance(exc, APIKeyRequired):
                    self.send_notification(
                        _("API key is required to use the service"),
                        action={
                            "label": _("Preferences"),
                            "name": "app.preferences",
                        },
                    )
                else:
                    self.send_notification(
                        _("Translation failed"),
                        action={
                            "label": _("Retry"),
                            "name": "win.translation",
                        },
                    )

            else:
                self.trans_warning.props.visible = False

            finally:
                self.translation_loading = False

                if self.next_translation:
                    self._on_translation()
                else:
                    self._translation_finish()
        else:
            self.trans_mistakes = None
            self.dest_buffer.props.text = ""

            if not self.translation_loading:
                self._translation_finish()

    def _appeared_before(self):
        if not self.provider["trans"]:
            return

        src_language = self.src_lang_selector.selected
        dest_language = self.dest_lang_selector.selected
        src_text = self.src_buffer.get_text(self.src_buffer.get_start_iter(), self.src_buffer.get_end_iter(), True)
        translation = self.current_translation
        if (
            len(self.provider["trans"].history) >= self.current_history + 1
            and translation
            and (translation.original.src == src_language or "auto")
            and translation.original.dest == dest_language
            and translation.original.text == src_text
        ):
            return True
        return False

    def _translation_finish(self):
        self.trans_spinner.hide()
        self.dest_box.props.sensitive = True
        self.langs_button_box.props.sensitive = True

    """
    Provider changes functions
    """

    def _on_active_provider_changed(self, _settings: Settings, kind: str, _name: str):
        self.save_settings()
        self.reload_provider(kind)

    def _on_provider_changed(self, _settings: Gio.Settings, _key: str, name: str):
        if not self.translator_loading:
            if self.provider["trans"] and name == self.provider["trans"].name:
                self.reload_provider("translator")

            if self.provider["tts"] and name == self.provider["tts"].name:
                self.reload_provider("tts")
