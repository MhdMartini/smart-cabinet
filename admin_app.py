from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivy.uix.screenmanager import SlideTransition
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivy.config import Config
from admin import Admin
from gui import KV
import pandas as pd
import string
from auto_complete import AutoComplete
import concurrent.futures

Config.set('kivy', 'exit_on_escape', '0')

Window.size = (500, 900)
Config.set('graphics', 'resizable', 1)
Config.write()

SUGG_COLOR = (0.5, 0.78, 0.95, 1)
SUGG_MENU_COLOR = (.98, .98, .98, .95)
ALLOWED_CHARS = string.ascii_lowercase + " ,.'1234567890_-+*"


def find_roster():
    try:
        roster = pd.read_csv("roster.csv")
    except FileNotFoundError:
        return False, []

    names_col = []
    first_name, last_name = None, None
    for col in roster.columns:
        if "first" in col.lower() and "name" in col.lower():
            first_name = col
            if last_name:
                break
            continue
        if "last" in col.lower() and "name" in col.lower():
            last_name = col
            if first_name:
                break
            continue
        if "name" == col.lower():
            roster[col] = roster[col].apply(lambda x: x.lower())
            return True, list(roster[col])

    if not first_name or not last_name:
        # If somehow there was no column which contains "name" in its name
        # Could happen in case of header
        return False, []

    # Only get here when a first name and a last name columns were detected (2)
    roster_col = roster[first_name] + " " + roster[last_name]
    roster_col = roster_col.apply(lambda x: x.lower())

    return True, list(roster_col)


class ConfirmBtn(MDRaisedButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = 'Confirm'
        self.md_bg_color = (0, 0.4, 0.7, 0.8)

    def on_release(self):
        self.send_identifier()


class DemoApp(MDApp):
    user = None
    id = None
    identifier = None
    kind = None
    dialog = None
    Enter = False  # Indicate whether Pressing Enter will save the added RFID
    roster, names = find_roster()  # Look for Students Roster
    auto_complete = AutoComplete(names)  # Object which generates name suggestions
    suggestions = []  # Suggested names in case of roster
    current_count = 0  # Number of characters currently in the text field
    input_mode = False
    index = 0
    menu_items = []
    original_input = ""
    received = False  # TODO: Manage

    def build(self):
        self.theme_cls.primary_palette = "Gray"
        self.title = "Smart Cabinet Admin Application"

        Window.bind(on_key_down=self._on_keyboard_down)

        screen = Builder.load_string(KV)
        return screen

    def _on_keyboard_down(self, *args):
        if self.root.current != "admin_routine" or not self.received:
            # Ignore keys unless in admin_routine and there is no dialog and
            return

        if args[2] == 41:
            # Escape button
            if self.dialog:
                self.dismiss()

            self.shrink_suggestions()
            return

        elif args[3] and args[3] in ALLOWED_CHARS:
            # an allowed character
            self.root.ids.identifier.text += args[3]
            self.original_input += args[3]
            if self.root.ids.identifier.text[:-1] in self.suggestions:
                # If a name is highlighted and user inputs letter, add letter to the suggested name
                self.original_input = self.root.ids.identifier.text[:-1] + args[3]
                self.root.ids.identifier.text = self.original_input
                self.index = 0

        elif args[2] == 42 and self.root.ids.identifier.text:
            # backspace and there is a letter to delete
            self.original_input = self.root.ids.identifier.text
            self.root.ids.identifier.text = self.root.ids.identifier.text[:-1]
            self.original_input = self.original_input[:-1]
            self.index = 0
            if not self.root.ids.identifier.text:
                self.shrink_suggestions()
                return

        elif args[2] == 40:
            # If Enter key is pressed
            if self.dialog:
                # If dialog is open
                self.send_identifier()
                self.original_input = ""

            elif self.root.ids.identifier.text and self.received:
                # If dialog is closed, and Enter key is pressed:
                # If suggestions are shown, copy highlighted text and shrink suggestions
                # self.index = 0
                self.validate_identifier()
                self.shrink_suggestions()
            return

        # elif not self.roster or self.kind != "student":
        #     return

        elif args[2] == 81 and self.root.ids.identifier.text and not self.dialog:
            # down arrow
            self.index += 1
            self.index = min(self.index, len(self.suggestions) - 1)
        elif args[2] == 82 and self.root.ids.identifier.text and not self.dialog:
            # up arrow
            self.index -= 1
            self.index = max(self.index, 0)
        else:
            return

        # menu_items: [input text, 5 suggestions]
        if not self.roster or self.kind != "student":
            return
        if not self.menu_items:
            self.menu_items = [self.root.ids.identifier, self.root.ids.name0, self.root.ids.name1,
                               self.root.ids.name2, self.root.ids.name3, self.root.ids.name4]
        self.suggestions = [self.original_input] + self.auto_complete.auto(self.original_input, max_sugg=5)

        if len(self.suggestions) == 1:
            self.shrink_suggestions()
            return

        self.show_suggestions()
        self.highlight_suggestions()

        if self.index == 0:
            self.root.ids.identifier.text = self.original_input
        for idx in range(1, 6):
            # Populate the name suggestions as needed
            try:
                self.menu_items[idx].text = self.suggestions[idx]
            except IndexError:
                self.menu_items[idx].text = ""
                pass

    def show_suggestions(self):
        self.input_mode = True
        # Show suggestions
        self.root.ids.name_list.size_hint_y = (len(self.suggestions) - 1) * 0.06
        self.root.ids.name_list.pos_hint = {"center_y": 0.47 - (len(self.suggestions) - 1) / 2 * .06, "center_x": .5}

    def shrink_suggestions(self):
        self.input_mode = False
        self.root.ids.name_list.size_hint_y = 0
        self.root.ids.name_list.pos_hint = {"center_y": .47, "center_x": .5}

    def highlight_suggestions(self):
        for idx in range(1, 6):
            if idx == self.index:
                if not self.menu_items[self.index].text:
                    continue
                self.menu_items[self.index].bg_color = SUGG_COLOR
            else:
                self.menu_items[idx].bg_color = SUGG_MENU_COLOR

        self.root.ids.identifier.text = self.menu_items[self.index].text

    def on_start(self):
        return

    def on_stop(self):
        try:
            self.user.close()
        except AttributeError:
            pass

    def connect2(self):
        self.user = Admin(gui=True)
        self.root.transition = SlideTransition(direction='left')
        self.root.current = "access_screen"
        self.root.ids.spinner2.active = False

    def connect(self):
        self.root.ids.spinner2.active = True
        executor = concurrent.futures.ThreadPoolExecutor()
        f = executor.submit(self.connect2)

    def admin_routine(self, kind):
        # Go to admin_routine screen and save the kind of RFID to be added
        self.root.transition = SlideTransition(direction='left')
        self.root.current = "admin_routine"
        self.kind = kind

    def get_id(self):
        # Get the Scanned ID, and allow user to input name (identifier)
        self.root.ids.id_label.text = ""
        self.root.ids.spinner.active = True
        executor = concurrent.futures.ThreadPoolExecutor()
        f = executor.submit(self.receive)

    def receive(self):
        self.user.send_msg(self.kind.encode())
        self.id = self.user.get_msg().decode()
        self.root.ids.id_label.text = self.id
        self.root.ids.identifier.hint_text = "Enter Name"

        self.received = True
        self.root.ids.spinner.active = False

    def back_btn(self):
        if self.received:
            return
        self.root.transition = SlideTransition(direction='right')
        self.root.current = "access_screen"
        self.root.ids.identifier.text = ""
        self.root.ids.id_label.text = ""

    def validate_identifier(self):
        self.identifier = self.root.ids.identifier
        if not self.identifier.text:
            return

        self.dialog = MDDialog(title='Name Check',
                               text=f"Are you sure you want to save {self.identifier.text}?"
                               , size_hint=(0.8, 1),
                               buttons=[ConfirmBtn()],
                               )
        self.dialog.open()

    def dismiss(self):
        self.dialog.dismiss()
        self.dialog = None

    def send_identifier(self):
        print(self.identifier.text, "Sent!")
        self.dismiss()
        name = self.identifier.text.strip()
        self.user.send_msg(name.encode())
        self.root.ids.id_label.text = "SAVED"

        self.identifier.hint_text = ""
        self.identifier.disabled = True
        self.root.ids.get_id.disabled = False
        self.original_input = ""
        self.index = 0
        self.suggestions = []
        self.menu_items = []
        self.received = False


DemoApp().run()
