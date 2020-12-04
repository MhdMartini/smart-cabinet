from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivy.uix.screenmanager import SlideTransition
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivy.config import Config
from admin import Admin
from gui import KV
import pandas as pd
from auto_complete import AutoComplete

Window.size = (500, 900)
Config.set('graphics', 'resizable', 0)
Config.write()


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

    def build(self):
        self.theme_cls.primary_palette = "Gray"
        self.title = "Smart Cabinet Admin Application"

        screen = Builder.load_string(KV)
        return screen

    def on_start(self):
        return

    def on_stop(self):
        try:
            self.user.close()
        except AttributeError:
            pass

    def on_text(self, textfield):
        if not self.roster or len(textfield.text) == 0:
            return
        print(textfield.text)
        self.suggestions = self.auto_complete.auto(textfield.text, max_sugg=5)
        print(self.suggestions)
        # TODO: Show suggestions somehow

    def connect(self):
        self.user = Admin(gui=True)
        self.root.transition = SlideTransition(direction='left')
        self.root.current = "access_screen"

    def admin_routine(self, kind):
        # Go to admin_routine screen and save the kind of RFID to be added
        self.root.transition = SlideTransition(direction='left')
        self.root.current = "admin_routine"
        self.kind = kind

    def get_id(self):
        # Get the Scanned ID, and allow user to input name (identifier)
        self.user.send_msg(self.kind.encode())
        self.id = self.user.get_msg().decode()
        self.root.ids.id_label.text = self.id

    def validate_identifier(self, identifier):
        self.identifier = identifier
        self.create_dialog()

    def dismiss(self):
        self.dialog.dismiss()

    def create_dialog(self):
        self.dialog = MDDialog(title='Name Check',
                               text=f"Are you sure you want to save {self.identifier.text}?"
                               , size_hint=(0.8, 1),
                               buttons=[MDFlatButton(text='Retry',
                                                     on_release=self.dismiss),
                                        MDRaisedButton(text='Confirm',
                                                       on_release=lambda x: self.send_identifier())],
                               )
        self.dialog.open()

    def send_identifier(self):
        self.Enter = False
        self.dismiss()
        self.user.send_msg(self.identifier.text.encode())
        self.root.ids.id_label.text = "SAVED!"
        self.identifier.hint_text = ""
        self.identifier.disabled = True
        self.root.ids.get_id.disabled = False
        return True


DemoApp().run()
