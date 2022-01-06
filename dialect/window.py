# Copyright 2020 gi-lom
# Copyright 2020-2021 Mufeed Ali
# Copyright 2020-2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
from gettext import gettext as _
from tempfile import NamedTemporaryFile

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gst, Gtk

from dialect.define import APP_ID, PROFILE, MAX_LENGTH, RES_PATH, TRANS_NUMBER
from dialect.lang_selector import DialectLangSelector
from dialect.settings import Settings
from dialect.shortcuts import DialectShortcutsWindow
from dialect.translators import TRANSLATORS, get_lang_name
from dialect.tts import TTS


@Gtk.Template(resource_path=f'{RES_PATH}/window.ui')
class DialectWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'DialectWindow'

    # Get widgets
    main_stack = Gtk.Template.Child()
    error_page = Gtk.Template.Child()
    translator_box = Gtk.Template.Child()
    retry_backend_btn = Gtk.Template.Child()

    title_stack = Gtk.Template.Child()
    langs_button_box = Gtk.Template.Child()
    switch_btn = Gtk.Template.Child()
    src_lang_btn = Gtk.Template.Child()
    src_lang_label = Gtk.Template.Child()
    dest_lang_btn = Gtk.Template.Child()
    dest_lang_label = Gtk.Template.Child()

    return_btn = Gtk.Template.Child()
    forward_btn = Gtk.Template.Child()

    src_pron_revealer = Gtk.Template.Child()
    src_pron_label = Gtk.Template.Child()
    mistakes = Gtk.Template.Child()
    mistakes_label = Gtk.Template.Child()
    char_counter = Gtk.Template.Child()
    src_scroller = Gtk.Template.Child()
    src_text = Gtk.Template.Child()
    clear_btn = Gtk.Template.Child()
    paste_btn = Gtk.Template.Child()
    src_voice_btn = Gtk.Template.Child()
    translate_btn = Gtk.Template.Child()

    dest_box = Gtk.Template.Child()
    dest_pron_revealer = Gtk.Template.Child()
    dest_pron_label = Gtk.Template.Child()
    dest_scroller = Gtk.Template.Child()
    dest_text = Gtk.Template.Child()
    dest_toolbar_stack = Gtk.Template.Child()
    trans_spinner = Gtk.Template.Child()
    trans_warning = Gtk.Template.Child()
    edit_btn = Gtk.Template.Child()
    copy_btn = Gtk.Template.Child()
    dest_voice_btn = Gtk.Template.Child()

    actionbar = Gtk.Template.Child()
    src_lang_btn2 = Gtk.Template.Child()
    switch_btn2 = Gtk.Template.Child()
    dest_lang_btn2 = Gtk.Template.Child()

    toast = None  # for notification management
    toast_overlay = Gtk.Template.Child()

    src_key_ctrlr = Gtk.Template.Child()
    win_key_ctrlr = Gtk.Template.Child()

    # Translator
    translator = None  # Translator object
    # Text to speech
    tts = None
    tts_langs = None
    voice_loading = False  # tts loading status

    # Preset language values
    src_langs = []
    dest_langs = []

    current_history = 0  # for history management

    # Translation-related variables
    no_retranslate = False  # used to prevent unnecessary re-translations
    trans_queue = []  # for pending translations
    active_thread = None  # for ongoing translation
    trans_failed = False  # for monitoring connectivity issues
    trans_mistakes = None  # "mistakes" suggestions
    # Pronunciations
    trans_src_pron = None
    trans_dest_pron = None
    # Suggestions
    before_suggest = None

    mobile_mode = False  # UI mode

    # Propeties
    backend_loading = GObject.Property(type=bool, default=False)

    def __init__(self, text, langs, **kwargs):
        super().__init__(**kwargs)

        # Options passed to command line
        self.launch_text = text
        self.launch_langs = langs

        # Application object
        self.app = kwargs['application']

        # GStreamer playbin object and related setup
        self.player = Gst.ElementFactory.make('playbin', 'player')
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_gst_message)
        self.player_event = threading.Event()  # An event for letting us know when Gst is done playing

        # Setup window
        self.setup_actions()
        self.setup()

    def setup(self):
        self.set_default_icon_name(APP_ID)

        # Set devel style
        if PROFILE == 'Devel':
            self.get_style_context().add_class('devel')

        # Connect responsive design function
        self.connect('notify::default-width', self.responsive_listener)
        self.connect('notify::maximized', self.responsive_listener)
        # Save settings on close
        self.connect('unrealize', self.save_settings)

        self.setup_headerbar()
        self.setup_translation()
        self.responsive_listener(launch=True)
        self.set_help_overlay(DialectShortcutsWindow())

        # Load translator
        self.retry_backend_btn.connect('clicked', self.retry_load_translator)
        threading.Thread(
            target=self.load_translator,
            args=[Settings.get().active_translator, True],
            daemon=True
        ).start()
        # Get languages available for speech
        if Settings.get().tts != '':
            threading.Thread(target=self.load_lang_speech, daemon=True).start()

    def setup_actions(self):
        back = Gio.SimpleAction.new('back', None)
        back.set_enabled(False)
        back.connect('activate', self.ui_return)
        self.add_action(back)

        forward_action = Gio.SimpleAction.new('forward', None)
        forward_action.set_enabled(False)
        forward_action.connect('activate', self.ui_forward)
        self.add_action(forward_action)

        switch_action = Gio.SimpleAction.new('switch', None)
        switch_action.connect('activate', self.ui_switch)
        self.add_action(switch_action)

        clear_action = Gio.SimpleAction.new('clear', None)
        clear_action.set_enabled(False)
        clear_action.connect('activate', self.ui_clear)
        self.add_action(clear_action)

        paste_action = Gio.SimpleAction.new('paste', None)
        paste_action.connect('activate', self.ui_paste)
        self.add_action(paste_action)

        copy_action = Gio.SimpleAction.new('copy', None)
        copy_action.set_enabled(False)
        copy_action.connect('activate', self.ui_copy)
        self.add_action(copy_action)

        listen_dest_action = Gio.SimpleAction.new('listen-dest', None)
        listen_dest_action.connect('activate', self.ui_dest_voice)
        self.add_action(listen_dest_action)

        suggest_action = Gio.SimpleAction.new('suggest', None)
        suggest_action.set_enabled(False)
        suggest_action.connect('activate', self.ui_suggest)
        self.add_action(suggest_action)

        suggest_ok_action = Gio.SimpleAction.new('suggest-ok', None)
        suggest_ok_action.connect('activate', self.ui_suggest_ok)
        self.add_action(suggest_ok_action)

        suggest_cancel_action = Gio.SimpleAction.new('suggest-cancel', None)
        suggest_cancel_action.connect('activate', self.ui_suggest_cancel)
        self.add_action(suggest_cancel_action)

        listen_src_action = Gio.SimpleAction.new('listen-src', None)
        listen_src_action.connect('activate', self.ui_src_voice)
        self.add_action(listen_src_action)

        translation_action = Gio.SimpleAction.new('translation', None)
        translation_action.set_enabled(False)
        translation_action.connect('activate', self.translation)
        self.add_action(translation_action)

    def load_translator(self, backend, launch=False):
        def update_ui():
            # Supported features
            if not self.translator.supported_features['mistakes']:
                self.mistakes.set_reveal_child(False)

            self.ui_suggest_cancel(None, None)
            if not self.translator.supported_features['suggestions']:
                self.edit_btn.set_visible(False)
            else:
                self.edit_btn.set_visible(True)

            if not self.translator.supported_features['pronunciation']:
                self.src_pron_revealer.set_reveal_child(False)
                self.dest_pron_revealer.set_reveal_child(False)
                self.app.lookup_action('pronunciation').set_enabled(False)
            else:
                self.app.lookup_action('pronunciation').set_enabled(True)

            self.no_retranslate = True
            # Update langs list
            self.src_lang_selector.set_languages(self.translator.languages)
            self.dest_lang_selector.set_languages(self.translator.languages)
            # Update selected langs
            self.src_lang_selector.set_property(
                'selected',
                'auto' if Settings.get().src_auto else self.src_langs[0]
            )
            self.dest_lang_selector.set_property(
                'selected',
                self.dest_langs[0]
            )

            self.no_retranslate = False

            self.main_stack.set_visible_child_name('translate')
            self.set_property('backend-loading', False)

        # Show loading view
        GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')

        try:
            # Translator object
            if TRANSLATORS[backend].supported_features['change-instance']:
                self.translator = TRANSLATORS[backend](
                    base_url=Settings.get().instance_url
                )
            else:
                self.translator = TRANSLATORS[backend]()

            # Get saved languages
            self.src_langs = Settings.get().src_langs
            self.dest_langs = Settings.get().dest_langs

            # Update UI
            GLib.idle_add(update_ui)

            if launch:
                self.no_retranslate = True
                if self.launch_langs['src'] is not None:
                    self.src_lang_selector.set_property('selected', self.launch_langs['src'])
                if self.launch_langs['dest'] is not None and self.launch_langs['dest'] in self.translator.languages:
                    self.dest_lang_selector.set_property('selected', self.launch_langs['dest'])
                self.no_retranslate = False

                if self.launch_text != '':
                    GLib.idle_add(self.translate, self.launch_text, self.launch_langs['src'], self.launch_langs['dest'])

        except Exception as exc:
            # Show error view
            GLib.idle_add(self.main_stack.set_visible_child_name, 'error')
            GLib.idle_add(self.set_property, 'backend-loading', False)

            self.error_page.set_description(str(exc))
            print('Error: ' + str(exc))

    def retry_load_translator(self, _button):
        threading.Thread(
            target=self.load_translator,
            args=[Settings.get().active_translator],
            daemon=True
        ).start()

    def on_listen_failed(self, called_from):
        self.src_voice_btn.set_child(self.src_voice_warning)
        self.src_voice_spinner.stop()

        self.dest_voice_btn.set_child(self.dest_voice_warning)
        self.dest_voice_spinner.stop()

        tooltip_text = _('A network issue has occured. Retry?')
        self.src_voice_btn.set_tooltip_text(tooltip_text)
        self.dest_voice_btn.set_tooltip_text(tooltip_text)

        if called_from is not None:
            action = {
                'label': _('Retry'),
                'name': 'win.listen-src' if called_from == 'src' else 'win.listen-dest',
            }
        else:
            action = None

        self.send_notification(
            _('A network issue has occured. Please try again.'),
            action=action
        )

        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )

        if self.tts_langs:
            self.lookup_action('listen-src').set_enabled(
                self.src_lang_selector.get_property('selected') in self.tts_langs
                and src_text != ''
            )
            self.lookup_action('listen-dest').set_enabled(
                self.dest_lang_selector.get_property('selected') in self.tts_langs
                and dest_text != ''
            )
        else:
            self.lookup_action('listen-src').set_enabled(src_text != '')
            self.lookup_action('listen-dest').set_enabled(dest_text != '')

    def load_lang_speech(self, listen=False, text=None, language=None, called_from=None):
        """
        Load the language list for TTS.

        text and language parameters are only needed with listen parameter.
        """
        try:
            self.voice_loading = True
            self.tts = TTS[Settings.get().tts]()
            self.tts_langs = self.tts.languages
            if not listen:
                GLib.idle_add(self.toggle_voice_spinner, False)
            elif language in self.tts_langs and text != '':
                self.voice_download(text, language)

        except RuntimeError as exc:
            GLib.idle_add(self.on_listen_failed, called_from)
            print('Error: ' + str(exc))
        finally:
            if not listen:
                self.voice_loading = False

    def setup_headerbar(self):
        # Left lang selector
        self.src_lang_selector = DialectLangSelector()
        self.src_lang_selector.connect('notify::selected',
                                       self.on_src_lang_changed)
        # Set popover selector to button
        self.src_lang_btn.set_popover(self.src_lang_selector)

        # Right lang selector
        self.dest_lang_selector = DialectLangSelector()
        self.dest_lang_selector.connect('notify::selected',
                                        self.on_dest_lang_changed)
        # Set popover selector to button
        self.dest_lang_btn.set_popover(self.dest_lang_selector)

        self.langs_button_box.set_homogeneous(False)

    def setup_translation(self):
        # Left buffer
        self.src_buffer = self.src_text.get_buffer()
        self.src_buffer.set_text(self.launch_text)
        self.src_buffer.connect('changed', self.on_src_text_changed)
        self.src_buffer.connect('end-user-action', self.user_action_ended)
        # Detect typing
        self.src_key_ctrlr.connect('key-pressed', self.update_trans_button)
        self.win_key_ctrlr.connect('key-pressed', self.on_key_event)
        # "Did you mean" links
        self.mistakes_label.connect('activate-link', self.on_mistakes_clicked)
        self.src_scroller.get_vadjustment().connect('value-changed', self.on_src_scrolled)
        self.src_scroller.get_vadjustment().connect('changed', self.on_src_scrolled)

        # Right buffer
        self.dest_buffer = self.dest_text.get_buffer()
        self.dest_buffer.set_text('')
        self.dest_buffer.connect('changed', self.on_dest_text_changed)
        self.dest_scroller.get_vadjustment().connect('value-changed', self.on_dest_scrolled)
        self.dest_scroller.get_vadjustment().connect('changed', self.on_dest_scrolled)
        # Translation progress spinner
        self.trans_spinner.hide()
        self.trans_warning.hide()

        # Voice buttons prep-work
        self.src_voice_warning = Gtk.Image.new_from_icon_name('dialog-warning-symbolic')
        self.src_voice_image = Gtk.Image.new_from_icon_name('audio-speakers-symbolic')
        self.src_voice_spinner = Gtk.Spinner()  # For use while audio is running or still loading.

        self.dest_voice_warning = Gtk.Image.new_from_icon_name('dialog-warning-symbolic')
        self.dest_voice_image = Gtk.Image.new_from_icon_name('audio-speakers-symbolic')
        self.dest_voice_spinner = Gtk.Spinner()

        self.toggle_voice_spinner(True)

        self.src_voice_btn.set_visible(Settings.get().tts != '')
        self.dest_voice_btn.set_visible(Settings.get().tts != '')

    def responsive_listener(self, _window=None, _param=None, launch=False):
        if launch:
            width, height = Settings.get().window_size
        else:
            size = self.get_default_size()
            width = size.width
            height = size.height

        if width < 680 and not self.is_maximized():
            if self.mobile_mode is False:
                self.mobile_mode = True
                self.toggle_mobile_mode()
        else:
            if self.mobile_mode is True:
                self.mobile_mode = False
                self.toggle_mobile_mode()

        if launch:
            self.set_default_size(width, height)

    def toggle_mobile_mode(self):
        if self.mobile_mode:
            # Show actionbar
            self.actionbar.set_reveal_child(True)
            # Change headerbar title
            self.title_stack.set_visible_child_name('label')
            # Change translation box orientation
            self.translator_box.set_orientation(Gtk.Orientation.VERTICAL)
            # Change lang selectors position
            self.src_lang_btn.set_popover(None)
            self.src_lang_btn2.set_popover(self.src_lang_selector)
            self.dest_lang_btn.set_popover(None)
            self.dest_lang_btn2.set_popover(self.dest_lang_selector)
        else:
            # Hide actionbar
            self.actionbar.set_reveal_child(False)
            # Reset headerbar title
            self.title_stack.set_visible_child_name('selector')
            # Reset translation box orientation
            self.translator_box.set_orientation(Gtk.Orientation.HORIZONTAL)
            # Reset lang selectors position
            self.src_lang_btn2.set_popover(None)
            self.src_lang_btn.set_popover(self.src_lang_selector)
            self.dest_lang_btn2.set_popover(None)
            self.dest_lang_btn.set_popover(self.dest_lang_selector)

    def translate(self, text, src_lang, dest_lang):
        """
        Translates the given text from auto detected language to last used
        language
        """
        # Set src lang to Auto
        if src_lang is None:
            self.src_lang_selector.set_property('selected', 'auto')
        else:
            self.src_lang_selector.set_property('selected', src_lang)
        if dest_lang is not None and dest_lang in self.translator.languages:
            self.dest_lang_selector.set_property('selected', dest_lang)
        # Set text to src buffer
        self.src_buffer.set_text(text)
        # Run translation
        self.translation()

    def save_settings(self, *args, **kwargs):
        if not self.is_maximized():
            size = self.get_default_size()
            Settings.get().window_size = (size.width, size.height)
        if self.translator is not None:
            Settings.get().src_langs = self.src_langs
            Settings.get().dest_langs = self.dest_langs
            Settings.get().save_translator_settings()

    def send_notification(self, text, queue=False, action=None, timeout=5, priority=Adw.ToastPriority.NORMAL):
        """
        Display an in-app notification.

        Args:
            text (str): The text or message of the notification.
            queue (bool, optional): If True, the notification will be queued.
            action (dict, optional): A dict containing the action to be called.
        """
        if not queue and self.toast is not None:
            self.toast.dismiss()
        self.toast = Adw.Toast.new(text)
        if action is not None:
            self.toast.set_button_label(action['label'])
            self.toast.set_action_name(action['name'])
        self.toast.set_timeout(timeout)
        self.toast.set_priority(priority)
        self.toast_overlay.add_toast(self.toast)

    def toggle_voice_spinner(self, active=True):
        if active:
            self.lookup_action('listen-src').set_enabled(False)
            self.src_voice_btn.set_child(self.src_voice_spinner)
            self.src_voice_spinner.start()

            self.lookup_action('listen-dest').set_enabled(False)
            self.dest_voice_btn.set_child(self.dest_voice_spinner)
            self.dest_voice_spinner.start()
        else:
            src_text = self.src_buffer.get_text(
                self.src_buffer.get_start_iter(),
                self.src_buffer.get_end_iter(),
                True
            )
            self.lookup_action('listen-src').set_enabled(
                self.src_lang_selector.get_property('selected') in self.tts_langs
                and src_text != ''
            )
            self.src_voice_btn.set_child(self.src_voice_image)
            self.src_voice_spinner.stop()

            dest_text = self.dest_buffer.get_text(
                self.dest_buffer.get_start_iter(),
                self.dest_buffer.get_end_iter(),
                True
            )
            self.lookup_action('listen-dest').set_enabled(
                self.dest_lang_selector.get_property('selected') in self.tts_langs
                and dest_text != ''
            )
            self.dest_voice_btn.set_child(self.dest_voice_image)
            self.dest_voice_spinner.stop()

    def on_src_scrolled(self, vadj):
        if (vadj.get_value() + vadj.get_page_size() != vadj.get_upper()
                or (self.src_pron_revealer.get_reveal_child() or self.mistakes.get_reveal_child())):
            self.src_scroller.get_style_context().add_class("scroller-border")
        else:
            self.src_scroller.get_style_context().remove_class("scroller-border")

    def on_dest_scrolled(self, vadj):
        if (vadj.get_value() + vadj.get_page_size() != vadj.get_upper()
                or self.dest_pron_revealer.get_reveal_child()):
            self.dest_scroller.get_style_context().add_class("scroller-border")
        else:
            self.dest_scroller.get_style_context().remove_class("scroller-border")

    def on_src_lang_changed(self, _obj, _param):
        code = self.src_lang_selector.get_property('selected')
        dest_code = self.dest_lang_selector.get_property('selected')
        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )

        if code == dest_code:
            code = self.dest_langs[1] if code == self.src_langs[0] else dest_code
            self.dest_lang_selector.set_property('selected', self.src_langs[0])

        # Disable or enable listen function.
        if self.tts_langs and Settings.get().tts != '':
            self.lookup_action('listen-src').set_enabled(
                code in self.tts_langs and src_text != ''
            )

        if code in self.translator.languages:
            self.src_lang_label.set_label(get_lang_name(code))
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
        else:
            self.src_lang_label.set_label(_('Auto'))

        # Rewrite recent langs
        self.src_lang_selector.clear_recent()
        self.src_lang_selector.insert_recent('auto', _('Auto'))
        for code in self.src_langs:
            self.src_lang_selector.insert_recent(code, get_lang_name(code))

        # Refresh list
        self.src_lang_selector.refresh_selected()

        # Translate again
        if not self.no_retranslate:
            self.translation()

    def on_dest_lang_changed(self, _obj, _param):
        code = self.dest_lang_selector.get_property('selected')
        src_code = self.src_lang_selector.get_property('selected')
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )

        if code == src_code:
            self.src_lang_selector.set_property('selected', self.dest_langs[0])

        # Disable or enable listen function.
        if self.tts_langs and Settings.get().tts != '':
            self.lookup_action('listen-dest').set_enabled(
                code in self.tts_langs and dest_text != ''
            )

        self.dest_lang_label.set_label(get_lang_name(code))
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
        self.dest_lang_selector.clear_recent()
        for code in self.dest_langs:
            self.dest_lang_selector.insert_recent(code, get_lang_name(code))

        # Refresh list
        self.dest_lang_selector.refresh_selected()

        # Translate again
        if not self.no_retranslate:
            self.translation()

    """
    User interface functions
    """
    def ui_return(self, _action, _param):
        """Go back one step in history."""
        if self.current_history != TRANS_NUMBER:
            self.current_history += 1
            self.history_update()

    def ui_forward(self, _action, _param):
        """Go forward one step in history."""
        if self.current_history != 0:
            self.current_history -= 1
            self.history_update()

    def add_history_entry(self, src_language, dest_language, src_text, dest_text):
        """Add a history entry to the history list."""
        new_history_trans = {
            'Languages': [src_language, dest_language],
            'Text': [src_text, dest_text]
        }
        if self.current_history > 0:
            del self.translator.history[: self.current_history]
            self.current_history = 0
        if len(self.translator.history) == TRANS_NUMBER:
            self.translator.history.pop()
        self.translator.history.insert(0, new_history_trans)
        GLib.idle_add(self.reset_return_forward_btns)

    def switch_all(self, src_language, dest_language, src_text, dest_text):
        self.src_lang_selector.set_property('selected', dest_language)
        self.dest_lang_selector.set_property('selected', src_language)
        self.src_buffer.set_text(dest_text)
        self.dest_buffer.set_text(src_text)
        self.add_history_entry(src_language, dest_language, src_text, dest_text)

        # Re-enable widgets
        self.langs_button_box.set_sensitive(True)
        self.lookup_action('translation').set_enabled(self.src_buffer.get_char_count() != 0)

    def switch_auto_lang(self, dest_language, src_text, dest_text):
        src_language = self.translator.detect(src_text).lang
        if isinstance(src_language, list):
            src_language = src_language[0]

        # Switch all
        GLib.idle_add(self.switch_all, src_language, dest_language, src_text, dest_text)

    def ui_switch(self, _action, _param):
        # Get variables
        self.langs_button_box.set_sensitive(False)
        self.lookup_action('translation').set_enabled(False)
        src_language = self.src_lang_selector.get_property('selected')
        dest_language = self.dest_lang_selector.get_property('selected')
        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        if src_language == 'auto':
            if src_text == '':
                src_language = self.src_langs[0]
            else:
                threading.Thread(
                    target=self.switch_auto_lang,
                    args=(dest_language, src_text, dest_text),
                    daemon=True
                ).start()
                return

        # Switch all
        self.switch_all(src_language, dest_language, src_text, dest_text)

    def ui_clear(self, _action, _param):
        self.src_buffer.set_text('')
        self.src_buffer.emit('end-user-action')

    def ui_copy(self, _action, _param):
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(dest_text)

    def ui_paste(self, _action, _param):
        clipboard = Gdk.Display.get_default().get_clipboard()

        def on_paste(_clipboard, result):
            text = clipboard.read_text_finish(result)
            if text is not None:
                end_iter = self.src_buffer.get_end_iter()
                self.src_buffer.insert(end_iter, text)

        cancellable = Gio.Cancellable()
        clipboard.read_text_async(cancellable, on_paste)

    def ui_suggest(self, _action, _param):
        self.dest_toolbar_stack.set_visible_child_name('edit')
        self.before_suggest = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        self.dest_text.set_editable(True)

    def ui_suggest_ok(self, _action, _param):
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        threading.Thread(
            target=self._suggest,
            args=(dest_text,),
            daemon=True
        ).start()
        self.before_suggest = None

    def ui_suggest_cancel(self, _action, _param):
        self.dest_toolbar_stack.set_visible_child_name('default')
        if self.before_suggest is not None:
            self.dest_buffer.set_text(self.before_suggest)
            self.before_suggest = None
        self.dest_text.set_editable(False)

    def _suggest(self, text):
        success = self.translator.suggest(text)
        GLib.idle_add(
            self.dest_toolbar_stack.set_visible_child_name,
            'default'
        )
        if success:
            GLib.idle_add(
                self.send_notification,
                _("New translation has been suggested!")
            )
        else:
            GLib.idle_add(
                self.send_notification,
                _("Suggestion failed.")
            )
        GLib.idle_add(
            self.dest_text.set_editable,
            False
        )

    def ui_src_voice(self, _action, _param):
        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )
        src_language = self.src_lang_selector.get_property('selected')
        self._voice(src_text, src_language, 'src')

    def ui_dest_voice(self, _action, _param):
        dest_text = self.dest_buffer.get_text(
            self.dest_buffer.get_start_iter(),
            self.dest_buffer.get_end_iter(),
            True
        )
        dest_language = self.dest_lang_selector.get_property('selected')
        self._voice(dest_text, dest_language, 'dest')

    def _voice(self, text, lang, called_from):
        if text != '':
            self.toggle_voice_spinner(True)
            if self.tts_langs:
                threading.Thread(
                    target=self.voice_download,
                    args=(text, lang, called_from),
                    daemon=True
                ).start()
            else:
                threading.Thread(
                    target=self.load_lang_speech,
                    args=(True, text, lang, called_from),
                    daemon=True
                ).start()

    def on_gst_message(self, _bus, message):
        if message.type == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
            self.player_event.set()
        elif message.type == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            self.player_event.set()
            print('Some error occured while trying to play.')

    def voice_download(self, text, language, called_from):
        try:
            self.voice_loading = True

            with NamedTemporaryFile() as file_to_play:
                self.tts.download_voice(text, language, file_to_play)
                self.player.set_property('uri', 'file://' + file_to_play.name)
                self.player.set_state(Gst.State.PLAYING)
                self.player_event.wait()
        except Exception as exc:
            print(exc)
            print('Audio download failed.')
            GLib.idle_add(self.on_listen_failed, called_from)
        else:
            GLib.idle_add(self.toggle_voice_spinner, False)
        finally:
            self.voice_loading = False

    def on_key_event(self, _button, keyval, _keycode, state):
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        unicode_key_val = Gdk.keyval_to_unicode(keyval)
        if (GLib.unichar_isgraph(chr(unicode_key_val))
                and modifiers in (shift_mask, 0)
                and not self.dest_text.get_editable()
                and not self.src_text.is_focus()):
            self.src_text.grab_focus()
            end_iter = self.src_buffer.get_end_iter()
            self.src_buffer.insert(end_iter, chr(unicode_key_val))
            return Gdk.EVENT_STOP
        return Gdk.EVENT_PROPAGATE

    # This starts the translation if Ctrl+Enter button is pressed
    def update_trans_button(self, _button, keyval, _keycode, state):
        modifiers = state & Gtk.accelerator_get_default_mod_mask()

        control_mask = Gdk.ModifierType.CONTROL_MASK
        enter_keys = (Gdk.KEY_Return, Gdk.KEY_KP_Enter)

        if not Settings.get().live_translation:
            if control_mask == modifiers:
                if keyval in enter_keys:
                    if not Settings.get().translate_accel_value:
                        self.translation()
                        return Gdk.EVENT_STOP
                    return Gdk.EVENT_PROPAGATE
            elif keyval in enter_keys:
                if Settings.get().translate_accel_value:
                    self.translation()
                    return Gdk.EVENT_STOP
                return Gdk.EVENT_PROPAGATE

        return Gdk.EVENT_PROPAGATE

    def on_mistakes_clicked(self, _button, _data):
        self.mistakes.set_reveal_child(False)
        self.src_buffer.set_text(self.trans_mistakes[1])
        # Run translation again
        self.translation()

        return Gdk.EVENT_STOP

    def on_src_text_changed(self, buffer):
        sensitive = buffer.get_char_count() != 0
        self.lookup_action('translation').set_enabled(sensitive)
        self.lookup_action('clear').set_enabled(sensitive)
        if not self.voice_loading and self.tts_langs:
            self.lookup_action('listen-src').set_enabled(
                self.src_lang_selector.get_property('selected') in self.tts_langs
                and sensitive
            )
        elif not self.voice_loading and not self.tts_langs:
            self.lookup_action('listen-src').set_enabled(sensitive)

    def on_dest_text_changed(self, buffer):
        sensitive = buffer.get_char_count() != 0
        self.lookup_action('copy').set_enabled(sensitive)
        self.lookup_action('suggest').set_enabled(
            self.translator.supported_features['suggestions']
            and sensitive
        )
        if not self.voice_loading and self.tts_langs:
            self.lookup_action('listen-dest').set_enabled(
                self.dest_lang_selector.get_property('selected') in self.tts_langs
                and sensitive
            )
        elif not self.voice_loading and not self.tts_langs:
            self.lookup_action('listen-dest').set_enabled(sensitive)

    def user_action_ended(self, buffer):
        # If the text is over the highest number of characters allowed, it is truncated.
        # This is done for avoiding exceeding the limit imposed by translation services.
        if buffer.get_char_count() >= MAX_LENGTH:
            self.send_notification(_('5000 characters limit reached!'))
            buffer.delete(
                buffer.get_iter_at_offset(MAX_LENGTH),
                buffer.get_end_iter()
            )
        self.char_counter.set_text(f'{str(buffer.get_char_count())}/{MAX_LENGTH}')
        if Settings.get().live_translation:
            self.translation()

    # The history part
    def reset_return_forward_btns(self):
        self.lookup_action('back').set_enabled(self.current_history < len(self.translator.history) - 1)
        self.lookup_action('forward').set_enabled(self.current_history > 0)

    # Retrieve translation history
    def history_update(self):
        self.reset_return_forward_btns()
        lang_hist = self.translator.history[self.current_history]
        self.no_retranslate = True
        self.src_lang_selector.set_property('selected',
                                            lang_hist['Languages'][0])
        self.dest_lang_selector.set_property('selected',
                                             lang_hist['Languages'][1])
        self.no_retranslate = False
        self.src_buffer.set_text(lang_hist['Text'][0])
        self.dest_buffer.set_text(lang_hist['Text'][1])

    def set_no_retranslate(self, state):
        self.no_retranslate = state

    # THE TRANSLATION AND SAVING TO HISTORY PART
    def appeared_before(self):
        src_language = self.src_lang_selector.get_property('selected')
        dest_language = self.dest_lang_selector.get_property('selected')
        src_text = self.src_buffer.get_text(
            self.src_buffer.get_start_iter(),
            self.src_buffer.get_end_iter(),
            True
        )
        if (
            len(self.translator.history) >= self.current_history + 1
            and (self.translator.history[self.current_history]['Languages'][0] == src_language or 'auto')
            and self.translator.history[self.current_history]['Languages'][1] == dest_language
            and self.translator.history[self.current_history]['Text'][0] == src_text
            and not self.trans_failed
        ) or (
            len(self.trans_queue) == 1
            and (self.trans_queue[0].get('src_language') == src_language or 'auto')
            and self.trans_queue[0].get('dest_language') == dest_language
            and self.trans_queue[0].get('src_text') == src_text
        ):
            return True
        return False

    def translation(self, _action=None, _param=None):
        # If it's like the last translation then it's useless to continue
        if not self.appeared_before():
            src_text = self.src_buffer.get_text(
                self.src_buffer.get_start_iter(),
                self.src_buffer.get_end_iter(),
                True
            )
            src_language = self.src_lang_selector.get_property('selected')
            dest_language = self.dest_lang_selector.get_property('selected')

            if self.trans_queue:
                self.trans_queue.pop(0)
            self.trans_queue.append({
                'src_text': src_text,
                'src_language': src_language,
                'dest_language': dest_language
            })

            # Check if there are any active threads.
            if self.active_thread is None:
                # Show feedback for start of translation.
                self.trans_spinner.show()
                self.trans_spinner.start()
                self.dest_box.set_sensitive(False)
                self.langs_button_box.set_sensitive(False)
                # If there is no active thread, create one and start it.
                self.active_thread = threading.Thread(target=self.run_translation, daemon=True)
                self.active_thread.start()

    def change_backends(self, backend):
        self.set_property('backend-loading', True)

        # Save previous backend settings
        self.save_settings()

        # Load translator
        threading.Thread(
            target=self.load_translator,
            args=[backend],
            daemon=True
        ).start()

    def run_translation(self):
        def on_trans_failed():
            self.trans_warning.show()
            self.lookup_action('copy').set_enabled(False)
            self.lookup_action('listen-src').set_enabled(False)
            self.lookup_action('listen-dest').set_enabled(False)
            self.send_notification(
                _('Translation failed. Please check for network issues.'),
                action={
                    'label': _('Retry'),
                    'name': 'win.translation',
                }
            )

        def on_trans_success():
            self.trans_warning.hide()

        def on_trans_done():
            self.trans_spinner.stop()
            self.trans_spinner.hide()
            self.dest_box.set_sensitive(True)
            self.langs_button_box.set_sensitive(True)

        def on_mistakes():
            if self.trans_mistakes is not None and self.translator.supported_features['mistakes']:
                mistake_text = self.trans_mistakes[0].replace("<em>", "<b>").replace("</em>", "</b>")
                self.mistakes_label.set_markup(_('Did you mean: ') + f'<a href="#">{mistake_text}</a>')
                self.mistakes.set_reveal_child(True)
            elif self.mistakes.get_reveal_child():
                self.mistakes.set_reveal_child(False)

        def on_pronunciation():
            reveal = Settings.get().show_pronunciation
            if self.translator.supported_features['pronunciation']:
                if self.trans_src_pron is not None:
                    self.src_pron_label.set_text(self.trans_src_pron)
                    self.src_pron_revealer.set_reveal_child(reveal)
                elif self.src_pron_revealer.get_reveal_child():
                    self.src_pron_revealer.set_reveal_child(False)

                if self.trans_dest_pron is not None:
                    self.dest_pron_label.set_text(self.trans_dest_pron)
                    self.dest_pron_revealer.set_reveal_child(reveal)
                elif self.dest_pron_revealer.get_reveal_child():
                    self.dest_pron_revealer.set_reveal_child(False)

        while self.trans_queue:
            # If the first language is revealed automatically, let's set it
            trans_dict = self.trans_queue.pop(0)
            src_text = trans_dict['src_text']
            src_language = trans_dict['src_language']
            dest_language = trans_dict['dest_language']
            if src_language == 'auto' and src_text != '':
                try:
                    src_language = self.translator.detect(src_text).lang
                    if isinstance(src_language, list):
                        src_language = src_language[0]
                    if src_language in self.translator.languages:
                        GLib.idle_add(self.set_no_retranslate, True)
                        GLib.idle_add(self.src_lang_selector.set_property,
                                      'selected', src_language)
                        GLib.idle_add(self.set_no_retranslate, False)
                        if src_language not in self.src_langs:
                            self.src_langs[0] = src_language
                    else:
                        src_language = 'auto'
                except Exception:
                    self.trans_failed = True
            # If the two languages are the same, nothing is done
            if src_language != dest_language:
                dest_text = ''
                # THIS IS WHERE THE TRANSLATION HAPPENS. The try is necessary to circumvent a bug of the used API
                if src_text != '':
                    try:
                        translation = self.translator.translate(
                            src_text,
                            src=src_language,
                            dest=dest_language
                        )
                        dest_text = translation.text
                        self.trans_mistakes = translation.extra_data['possible-mistakes']
                        self.trans_src_pron = translation.extra_data['src-pronunciation']
                        self.trans_dest_pron = translation.extra_data['dest-pronunciation']
                        self.trans_failed = False
                    except Exception as exc:
                        print(exc)
                        self.trans_mistakes = None
                        self.trans_pronunciation = None
                        self.trans_failed = True

                    # Finally, everything is saved in history
                    self.add_history_entry(
                        src_language,
                        dest_language,
                        src_text,
                        dest_text
                    )
                else:
                    self.trans_failed = False
                    self.trans_mistakes = None
                    self.trans_src_pron = None
                    self.trans_dest_pron = None
                GLib.idle_add(self.dest_buffer.set_text, dest_text)
                GLib.idle_add(on_mistakes)
                GLib.idle_add(on_pronunciation)

        if self.trans_failed:
            GLib.idle_add(on_trans_failed)
        else:
            GLib.idle_add(on_trans_success)
        GLib.idle_add(on_trans_done)
        self.active_thread = None
