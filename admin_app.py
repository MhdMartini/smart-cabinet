from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivy.uix.screenmanager import SlideTransition
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivy.config import Config
from admin import *
from gui import KV

Window.size = (500, 900)
Config.set('graphics', 'resizable', 0)
Config.write()

class DemoApp(MDApp):
    user = None
    id = None
    identifier = None
    kind = None
    dialog = None
    Enter = False  # Indicate whether Pressing Enter will save the added RFID

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

    def connect(self):
        self.user = Admin()
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

        def dismiss(instance):
            self.dialog.dismiss()
            self.Enter = False

        self.dialog = MDDialog(title='Name Check',
                               text=f"Are you sure you want to save {identifier.text}?"
                               , size_hint=(0.8, 1),
                               buttons=[MDFlatButton(text='Retry',
                                                     on_release=dismiss),
                                        MDRaisedButton(text='Confirm',
                                                       on_release=lambda x: self.send_identifier())],
                               )
        self.dialog.open()

    def send_identifier(self):
        self.Enter = False
        self.dialog.dismiss()
        self.user.send_msg(self.identifier.text.encode())
        self.root.ids.id_label.text = "SAVED!"
        self.identifier.hint_text = ""
        self.identifier.disabled = True
        self.root.ids.get_id.disabled = False
        return True


DemoApp().run()
