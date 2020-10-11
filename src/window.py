# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import threading
from tempfile import NamedTemporaryFile

from gi.repository import Gdk, Gio, GLib, Gtk, Gst, Handy

from googletrans import LANGUAGES, Translator
from gtts import gTTS, lang

from dialect.define import APP_ID, RES_PATH, MAX_LENGTH, TRANS_NUMBER, \
    LANG_NUMBER, BUTTON_LENGTH, BUTTON_NUM_LANGUAGES
from dialect.lang_selector import DialectLangSelector


@Gtk.Template(resource_path=f'{RES_PATH}/window.ui')
class DialectWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'DialectWindow'

    # Get widgets
    main_stack = Gtk.Template.Child()
    translator_box = Gtk.Template.Child()

    title_stack = Gtk.Template.Child()
    langs_button_box = Gtk.Template.Child()
    switch_btn = Gtk.Template.Child()
    left_lang_btn = Gtk.Template.Child()
    left_lang_label = Gtk.Template.Child()
    right_lang_btn = Gtk.Template.Child()
    right_lang_label = Gtk.Template.Child()

    return_btn = Gtk.Template.Child()
    forward_btn = Gtk.Template.Child()

    menu_btn = Gtk.Template.Child()

    left_text = Gtk.Template.Child()
    clear_btn = Gtk.Template.Child()
    paste_btn = Gtk.Template.Child()
    translate_btn = Gtk.Template.Child()

    right_box = Gtk.Template.Child()
    right_text = Gtk.Template.Child()
    trans_spinner = Gtk.Template.Child()
    trans_warning = Gtk.Template.Child()
    copy_btn = Gtk.Template.Child()
    voice_btn = Gtk.Template.Child()

    actionbar = Gtk.Template.Child()
    left_lang_btn2 = Gtk.Template.Child()
    switch_btn2 = Gtk.Template.Child()
    right_lang_btn2 = Gtk.Template.Child()

    notification_revealer = Gtk.Template.Child()
    notification_label = Gtk.Template.Child()

    # Language values
    lang_codes = list(LANGUAGES.keys())
    lang_names = list(LANGUAGES.values())
    lang_speech = None
    # Current input Text
    current_input_text = ''
    current_history = 0
    history = []
    type_time = 0
    trans_queue = []
    trans_failed = False
    active_thread = None
    # These are for being able to go backspace
    first_key = 0
    second_key = 0
    mobile_mode = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # GSettings object
        self.settings = Gio.Settings.new(APP_ID)
        # Get saved languages
        self.left_langs = list(self.settings.get_value('left-langs'))
        self.right_langs = list(self.settings.get_value('right-langs'))

        # Google Translate object
        self.translator = Translator()

        # GStreamer playbin object and related setup
        self.player = Gst.ElementFactory.make('playbin', 'player')
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_gst_message)
        self.player_event = threading.Event()  # An event for letting us know when Gst is done playing

        # Clipboard
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)  # This is only for the Clipboard button

        # Setup window
        self.setup()

    def setup(self):
        self.set_default_icon_name(APP_ID)

        # Load saved dark mode
        gtk_settings = Gtk.Settings.get_default()
        dark_mode = self.settings.get_boolean('dark-mode')
        gtk_settings.set_property('gtk-application-prefer-dark-theme',
                                  dark_mode)

        # Connect responsive design function
        self.connect('check-resize', self.responsive_listener)
        self.connect('destroy', self.on_destroy)

        self.setup_headerbar()
        self.setup_actionbar()
        self.setup_translation()
        self.toggle_mobile_mode()

        # Get languages available for speech
        threading.Thread(target=self.load_lang_speech).start()

    def load_lang_speech(self):
        try:
            self.lang_speech = list(lang.tts_langs(tld='com').keys())
            GLib.idle_add(self.toggle_voice_spinner, False)

        except RuntimeError as exc:
            def on_fail():
                self.voice_btn.set_image(self.voice_warning)
                self.voice_btn.set_sensitive(False)
                self.voice_spinner.stop()
                self.voice_btn.set_tooltip_text('No network connection detected.')
                self.notify('No network connection detected.')

            GLib.idle_add(on_fail)
            print('Error: ' + str(exc))

    def setup_headerbar(self):
        # Connect history buttons
        self.return_btn.connect('clicked', self.ui_return)
        self.forward_btn.connect('clicked', self.ui_forward)

        # Left lang selector
        self.left_lang_selector = DialectLangSelector()
        self.left_lang_selector.connect('notify::selected',
                                        self.on_left_lang_changed)
        # Load saved left lang
        self.left_lang_selector.set_property('selected', self.left_langs[0])
        # Set popover selector to button
        self.left_lang_btn.set_popover(self.left_lang_selector)
        self.left_lang_selector.set_relative_to(self.left_lang_btn)

        # Right lang selector
        self.right_lang_selector = DialectLangSelector()
        self.right_lang_selector.connect('notify::selected',
                                         self.on_right_lang_changed)
        # Load saved right lang
        self.right_lang_selector.set_property('selected', self.right_langs[0])
        # Set popover selector to button
        self.right_lang_btn.set_popover(self.right_lang_selector)
        self.right_lang_selector.set_relative_to(self.right_lang_btn)

        # Add languages to both list
        for code, name in LANGUAGES.items():
            self.left_lang_selector.insert(code, name.capitalize())
            self.right_lang_selector.insert(code, name.capitalize())

        self.langs_button_box.set_homogeneous(False)

        # Switch button
        self.switch_btn.connect('clicked', self.ui_switch)

        # Add menu to menu button
        builder = Gtk.Builder.new_from_resource(f'{RES_PATH}/menu.ui')
        menu = builder.get_object('app-menu')
        menu_popover = Gtk.Popover.new_from_model(self.menu_btn, menu)
        self.menu_btn.set_popover(menu_popover)

    def setup_actionbar(self):
        # Set popovers to lang buttons
        self.left_lang_btn2.set_popover(self.left_lang_selector)
        self.right_lang_btn2.set_popover(self.right_lang_selector)

        # Switch button
        self.switch_btn2.connect('clicked', self.ui_switch)

    def setup_translation(self):
        # Left buffer
        self.left_buffer = self.left_text.get_buffer()
        self.left_buffer.set_text('')
        self.left_buffer.connect('changed', self.text_changed)
        self.left_buffer.connect('end-user-action', self.user_action_ended)
        self.connect('key-press-event', self.update_trans_button)
        # Clear button
        self.clear_btn.connect('clicked', self.ui_clear)
        # Paste button
        self.paste_btn.connect('clicked', self.ui_paste)
        # Translate button
        self.translate_btn.connect('clicked', self.translation)

        # Right buffer
        self.right_buffer = self.right_text.get_buffer()
        self.right_buffer.set_text('')
        # Clipboard button
        self.copy_btn.connect('clicked', self.ui_copy)
        # Translation progress spinner
        self.trans_spinner.hide()
        self.trans_warning.hide()
        # Voice button prep-work
        self.voice_warning = Gtk.Image.new_from_icon_name(
            'dialog-warning-symbolic', Gtk.IconSize.BUTTON)
        self.voice_btn.connect('clicked', self.ui_voice)
        self.voice_image = Gtk.Image.new_from_icon_name(
            'audio-speakers-symbolic', Gtk.IconSize.BUTTON)
        self.voice_spinner = Gtk.Spinner()  # For use while audio is running or still loading.
        self.toggle_voice_spinner(True)

    def responsive_listener(self, window):
        size = self.get_size()

        if size.width < 600:
            if self.mobile_mode is False:
                self.mobile_mode = True
                self.toggle_mobile_mode()
        else:
            if self.mobile_mode is True:
                self.mobile_mode = False
                self.toggle_mobile_mode()

    def toggle_mobile_mode(self):
        if self.mobile_mode:
            # Show actionbar
            self.actionbar.set_reveal_child(True)
            # Change headerbar title
            self.title_stack.set_visible_child_name('label')
            # Change translation box orientation
            self.translator_box.set_orientation(Gtk.Orientation.VERTICAL)
            # Change lang selectors position
            self.left_lang_selector.set_relative_to(self.left_lang_btn2)
            self.right_lang_selector.set_relative_to(self.right_lang_btn2)
        else:
            # Hide actionbar
            self.actionbar.set_reveal_child(False)
            # Reset headerbar title
            self.title_stack.set_visible_child_name('selector')
            # Reset translation box orientation
            self.translator_box.set_orientation(Gtk.Orientation.HORIZONTAL)
            # Reset lang selectors position
            self.left_lang_selector.set_relative_to(self.left_lang_btn)
            self.right_lang_selector.set_relative_to(self.right_lang_btn)

    def on_destroy(self, _window):
        self.settings.set_value('left-langs',
                                GLib.Variant('as', self.left_langs))
        self.settings.set_value('right-langs',
                                GLib.Variant('as', self.right_langs))

    def notify(self, text, timeout=5):
        """
        Display an in-app notification.

        Args:
            text (str): The text or message of the notification.
            timeout (int, optional): The time before the notification disappears. Defaults to 5.
        """
        self.notification_label.set_text(text)
        self.notification_revealer.set_reveal_child(True)

        timer = threading.Timer(
            timeout,
            GLib.idle_add,
            args=[self.notification_revealer.set_reveal_child, False]
        )
        timer.start()

    def toggle_voice_spinner(self, active=True, loading=False):
        if active:
            self.voice_btn.set_sensitive(False)
            self.voice_btn.set_image(self.voice_spinner)
            self.voice_spinner.start()
        else:
            second_text = self.right_buffer.get_text(
                self.right_buffer.get_start_iter(),
                self.right_buffer.get_end_iter(),
                True
            )
            self.voice_btn.set_sensitive(self.right_lang_selector.get_property('selected') in self.lang_speech \
                                         and second_text != '')
            self.voice_btn.set_image(self.voice_image)
            self.voice_spinner.stop()

    def on_left_lang_changed(self, _obj, _param):
        code = self.left_lang_selector.get_property('selected')

        if code in LANGUAGES:
            self.left_lang_label.set_label(LANGUAGES[code].capitalize())
            # Updated saved left langs list
            if code in self.left_langs:
                # Bring lang to the top
                index = self.left_langs.index(code)
                self.left_langs.insert(0, self.left_langs.pop(index))
            else:
                self.left_langs.pop()
                self.left_langs.insert(0, code)
        else:
            self.left_lang_label.set_label('Auto')

        # Rewrite recent langs
        self.left_lang_selector.clear_recent()
        self.left_lang_selector.insert_recent('auto', 'Auto')
        for code in self.left_langs:
            name = LANGUAGES[code].capitalize()
            self.left_lang_selector.insert_recent(code, name)

        # Refresh list
        self.left_lang_selector.refresh_selected()

    def on_right_lang_changed(self, _obj, _param):
        code = self.right_lang_selector.get_property('selected')

        # Disable or enable listen function.
        if self.lang_speech:
            self.voice_btn.set_sensitive(code in self.lang_speech)

        name = LANGUAGES[code].capitalize()
        self.right_lang_label.set_label(name)
        # Updated saved right langs list
        if code in self.right_langs:
            # Bring lang to the top
            index = self.right_langs.index(code)
            self.right_langs.insert(0, self.right_langs.pop(index))
        else:
            self.right_langs.pop()
            self.right_langs.insert(0, code)

        # Rewrite recent langs
        self.right_lang_selector.clear_recent()
        for code in self.right_langs:
            name = LANGUAGES[code].capitalize()
            self.right_lang_selector.insert_recent(code, name)

        # Refresh list
        self.right_lang_selector.refresh_selected()

    """
    User interface functions
    """
    def ui_return(self, _button):
        if self.current_history != TRANS_NUMBER:
            self.current_history += 1
            self.history_update()

    def ui_forward(self, _button):
        if self.current_history != 0:
            self.current_history -= 1
            self.history_update()

    def add_history_entry(self, first_language, second_language, first_text, second_text):
        new_history_trans = {
            'Languages': [first_language, second_language],
            'Text': [first_text, second_text]
        }
        if self.current_history > 0:
            del self.history[:self.current_history]
            self.current_history = 0
        if len(self.history) > 0:
            self.return_btn.set_sensitive(True)
        if len(self.history) == TRANS_NUMBER:
            self.history.pop()
        self.history.insert(0, new_history_trans)
        GLib.idle_add(self.reset_return_forward_btns)

    def switch_all(self, first_language, second_language, first_text, second_text):
        self.left_lang_selector.set_property('selected', second_language)
        self.right_lang_selector.set_property('selected', first_language)
        self.left_buffer.set_text(second_text)
        self.right_buffer.set_text(first_text)
        self.add_history_entry(first_language, second_language, first_text, second_text)

        # Re-enable widgets
        self.langs_button_box.set_sensitive(True)
        self.translate_btn.set_sensitive(self.left_buffer.get_char_count() != 0)

    def switch_auto_lang(self, second_language, first_text, second_text):
        first_language = str(self.translator.detect(first_text).lang)

        # Switch all
        GLib.idle_add(self.switch_all, first_language, second_language, first_text, second_text)

    def ui_switch(self, _button):
        # Get variables
        self.langs_button_box.set_sensitive(False)
        self.translate_btn.set_sensitive(False)
        first_buffer = self.left_buffer
        second_buffer = self.right_buffer
        first_language = self.left_lang_selector.get_property('selected')
        second_language = self.right_lang_selector.get_property('selected')
        first_text = self.left_buffer.get_text(
            self.left_buffer.get_start_iter(),
            self.left_buffer.get_end_iter(),
            True
        )
        second_text = self.right_buffer.get_text(
            self.right_buffer.get_start_iter(),
            self.right_buffer.get_end_iter(),
            True
        )
        if first_language == 'auto':
            if first_text == '':
                first_language = self.left_langs[0]
            else:
                threading.Thread(
                    target=self.switch_auto_lang,
                    args=(second_language, first_text, second_text)
                ).start()
                return

        # Switch all
        self.switch_all(first_language, second_language, first_text, second_text)

    def ui_clear(self, _button):
        self.left_buffer.set_text('')

    def ui_copy(self, _button):
        second_buffer = self.right_buffer
        second_text = second_buffer.get_text(second_buffer.get_start_iter(), second_buffer.get_end_iter(), True)
        self.clipboard.set_text(second_text, -1)
        self.clipboard.store()

    def ui_paste(self, _button):
        text = self.clipboard.wait_for_text()
        if text is not None:
            end_iter = self.left_buffer.get_end_iter()
            self.left_buffer.insert(end_iter, text)

    def ui_voice(self, _button):
        second_buffer = self.right_buffer
        second_text = second_buffer.get_text(second_buffer.get_start_iter(),
                                             second_buffer.get_end_iter(), True)
        second_language_voice = self.right_lang_selector.get_property('selected')
        # Add here code that changes voice button behavior
        if second_text != '':
            self.toggle_voice_spinner(True)
            threading.Thread(
                target=self.voice_download,
                args=(second_text, second_language_voice)
            ).start()

    def on_gst_message(self, _bus, message):
        if message.type == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
            self.player_event.set()
        elif message.type == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            self.player_event.set()
            print('Some error occured while trying to play.')

    def voice_download(self, text, language):
        try:
            tts = gTTS(text, lang=language, lang_check=False)
        except Exception as exc:
            print(exc)
            print('Audio download failed.')
            pass
        else:
            with NamedTemporaryFile() as file_to_play:
                tts.write_to_fp(file_to_play)
                file_to_play.seek(0)
                self.player.set_property('uri', 'file://' + file_to_play.name)
                self.player.set_state(Gst.State.PLAYING)
                self.player_event.wait()
        finally:
            # The code to execute no matter what
            GLib.idle_add(self.toggle_voice_spinner, False)

    # This starts the translation if Ctrl+Enter button is pressed
    def update_trans_button(self, button, keyboard):
        modifiers = keyboard.get_state() & Gtk.accelerator_get_default_mod_mask()

        control_mask = Gdk.ModifierType.CONTROL_MASK
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        unicode_key_val = Gdk.keyval_to_unicode(keyboard.keyval)
        if (GLib.unichar_isgraph(chr(unicode_key_val)) and
                modifiers in (shift_mask, 0) and not self.left_text.is_focus()):
            self.left_text.grab_focus()

        if not self.settings.get_boolean('live-translation'):
            if control_mask == modifiers:
                if keyboard.keyval == Gdk.KEY_Return:
                    if not self.settings.get_value('translate-accel'):
                        self.translation(button)
                        return Gdk.EVENT_STOP
                    return Gdk.EVENT_PROPAGATE
            elif keyboard.keyval == Gdk.KEY_Return:
                if self.settings.get_value('translate-accel'):
                    self.translation(button)
                    return Gdk.EVENT_STOP
                return Gdk.EVENT_PROPAGATE

        return Gdk.EVENT_PROPAGATE

    def text_changed(self, buffer):
        sensitive = buffer.get_char_count() != 0
        self.translate_btn.set_sensitive(sensitive)
        self.clear_btn.set_sensitive(sensitive)

    def user_action_ended(self, buffer):
        if self.settings.get_boolean('live-translation'):
            self.translation(None)

    # The history part
    def reset_return_forward_btns(self):
        self.return_btn.set_sensitive(self.current_history < len(self.history) - 1)
        self.forward_btn.set_sensitive(self.current_history > 0)

    # Retrieve translation history
    def history_update(self):
        self.reset_return_forward_btns()
        lang_hist = self.history[self.current_history]
        self.left_lang_selector.set_property('selected',
                                             lang_hist['Languages'][0])
        self.right_lang_selector.set_property('selected',
                                              lang_hist['Languages'][1])
        self.left_buffer.set_text(lang_hist['Text'][0])
        self.right_buffer.set_text(lang_hist['Text'][1])

    # THE TRANSLATION AND SAVING TO HISTORY PART
    def appeared_before(self):
        first_language = self.left_lang_selector.get_property('selected')
        second_language = self.right_lang_selector.get_property('selected')
        first_text = self.left_buffer.get_text(self.left_buffer.get_start_iter(), self.left_buffer.get_end_iter(), True)
        if (self.history[self.current_history]['Languages'][0] == first_language and
                self.history[self.current_history]['Languages'][1] == second_language and
                self.history[self.current_history]['Text'][0] == first_text and
                not self.trans_failed):
            return True
        return False

    def translation(self, _button):
        # If it's like the last translation then it's useless to continue
        if len(self.history) == 0 or not self.appeared_before():
            first_buffer = self.left_buffer
            second_buffer = self.right_buffer
            first_text = first_buffer.get_text(first_buffer.get_start_iter(), first_buffer.get_end_iter(), True)
            # If the first text is empty, then everything is simply resetted and nothing is saved in history
            if first_text == '':
                second_buffer.set_text('')
            else:
                first_language = self.left_lang_selector.get_property('selected')
                second_language = self.right_lang_selector.get_property('selected')

                if self.trans_queue:
                    self.trans_queue.pop(0)
                self.trans_queue.append({
                    'first_text': first_text,
                    'first_language': first_language,
                    'second_language': second_language
                })

                # Check if there are any active threads.
                if self.active_thread is None:
                    self.trans_spinner.show()
                    self.trans_spinner.start()
                    self.right_box.set_sensitive(False)
                    self.langs_button_box.set_sensitive(False)
                    # If there are not any active threads, create one and start it.
                    self.active_thread = threading.Thread(target=self.run_translation, daemon=True)
                    self.active_thread.start()

    def run_translation(self):
        while self.trans_queue:
            # If the first language is revealed automatically, let's set it
            trans_dict = self.trans_queue.pop(0)
            first_text = trans_dict['first_text']
            first_language = trans_dict['first_language']
            second_language = trans_dict['second_language']
            if first_language == 'auto' and first_text != '':
                first_language = str(self.translator.detect(first_text).lang)
                GLib.idle_add(self.left_lang_selector.set_property,
                              'selected', first_language)
                self.left_langs[0] = first_language
            # If the two languages are the same, nothing is done
            if first_language != second_language:
                second_text = ''
                # If the text is over the highest number of characters allowed, it is truncated.
                # This is done for avoiding exceeding the limit imposed by Google.
                if len(first_text) > 100:
                    first_text = first_text[:MAX_LENGTH]
                # THIS IS WHERE THE TRANSLATION HAPPENS. The try is necessary to circumvent a bug of the used API
                try:
                    second_text = self.translator.translate(
                        first_text,
                        src=first_language,
                        dest=second_language
                    ).text
                    self.trans_failed = False
                except Exception:
                    self.trans_failed = True
                    pass
                GLib.idle_add(self.right_buffer.set_text, second_text)

                # Finally, everything is saved in history
                self.add_history_entry(first_language, second_language, first_text, second_text)
        if self.trans_failed:
            GLib.idle_add(self.trans_warning.show)
            GLib.idle_add(self.notify, 'Translation failed.\n Please check for network issues.')
            GLib.idle_add(self.copy_btn.set_sensitive, False)
            GLib.idle_add(self.voice_btn.set_sensitive, False)
        else:
            GLib.idle_add(self.trans_warning.hide)
            GLib.idle_add(self.copy_btn.set_sensitive, True)
            GLib.idle_add(self.voice_btn.set_sensitive, True)
        GLib.idle_add(self.trans_spinner.stop)
        GLib.idle_add(self.trans_spinner.hide)
        GLib.idle_add(self.right_box.set_sensitive, True)
        GLib.idle_add(self.langs_button_box.set_sensitive, True)
        self.active_thread = None
