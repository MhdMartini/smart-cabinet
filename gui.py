KV = """
#: import SlideTransition kivy.uix.screenmanager.SlideTransition

ScreenManager:
    id: screen_manager
    Screen:
        name: "connect_screen"
        MDFloatLayout:
            orientation: "vertical"

            Image:
                source: "icon.png"
                pos_hint: {"center_y": 0.7, "center_x": 0.5}
                size_hint: (0.4, 0.4)

            MDLabel:
                text: "SMART CABINET"
                theme_text_color: "Hint"
                halign: "center"
                pos_hint: {"center_y": 0.3}
            MDLabel:
                text: "ADMIN APPLICATION"
                theme_text_color: "Custom"
                text_color: 0, 0.4, 0.7, 1
                halign: "center"
                pos_hint: {"center_y": 0.27}
            MDLabel:
                text: "mohamed_martini@student.uml.edu"
                theme_text_color: "Hint"
                halign: "center"
                pos_hint: {"center_y": 0.05}


            MDFloatingActionButton:
                icon: "lan-connect"
                elevation_normal: 10
                md_bg_color: app.theme_cls.primary_color
                pos_hint: {"center_y": 0.4, "center_x": 0.5}
                on_release: app.connect()


    Screen:
        name: "access_screen"
        MDFloatLayout:
            MDFloatingActionButton:
                elevation_normal: 12
                icon: "account-plus"
                md_bg_color: 0, 0.4, 0.7, 1
                pos_hint: {"center_y": 0.8, "center_x": 0.5}
                size_hint: (None, None)
                size: (dp(120),dp(120))
                on_release: app.admin_routine("admin")
            MDFloatingActionButton:
                elevation_normal: 12
                icon: "account-multiple-plus"
                md_bg_color: 0, 0.4, 0.7, 0.6
                pos_hint: {"center_y": 0.55, "center_x": 0.5}
                size_hint: (None, None)
                size: (dp(120),dp(120))
                on_release: app.admin_routine("student")
            MDFloatingActionButton:
                elevation_normal: 12
                icon: "barcode-scan"
                md_bg_color: 0, 0.4, 0.7, 0.4
                pos_hint: {"center_y": 0.3, "center_x": 0.5}
                size_hint: (None, None)
                size: (dp(120),dp(120))
                on_release: app.admin_routine("shoebox")  

            MDLabel:
                text: "ADMIN"
                theme_text_color: "Hint"
                halign: "center"
                pos_hint: {"center_y": 0.7, "center_x": 0.5}
            MDLabel:
                text: "STUDENT"
                theme_text_color: "Hint"
                halign: "center"
                pos_hint: {"center_y": 0.45, "center_x": 0.5}
            MDLabel:
                text: "INVENTORY"
                theme_text_color: "Hint"
                halign: "center"
                pos_hint: {"center_y": 0.2, "center_x": 0.5}


    Screen:
        name: "admin_routine"
        MDFloatLayout:
            MDLabel:
                id: id_label
                text: ""
                font_style: "H4"
                theme_text_color: "Custom"
                text_color: 0.12, 0.76, 0.12, 1
                halign: "center"
                pos_hint: {"center_y": 0.8, "center_x": 0.5}
            MDTextField:
                id: identifier
                hint_text: ""
                helper_text: "Press Enter to Save"
                helper_text_mode: "on_focus"
                icon_right: "account-arrow-right"
                icon_right_color: app.theme_cls.primary_color
                pos_hint:{'center_x': 0.5, 'center_y': 0.5}
                size_hint_x:None
                width:300
                disabled: True
                on_text_validate: app.validate_identifier(self)

            MDRaisedButton:
                id: get_id
                text: "Get ID"
                font_size: "32sp"
                text_color: 1, 1, 1, 1
                size_hint: (0.4, 0.1)
                pos_hint: {"center_x": 0.5, "center_y": 0.3}
                md_bg_color: app.theme_cls.primary_dark
                on_release: 
                    app.get_id()
                    identifier.text = ""
                    identifier.hint_text = "Enter Name"
                    identifier.disabled = False
                    self.disabled = True


            MDIconButton:
                icon: "keyboard-backspace"
                pos_hint: {"center_y": .95, "center_x": .1}
                on_release:
                    screen_manager.transition = SlideTransition(direction='right')
                    screen_manager.current = "access_screen"
                    identifier.text = ""
                    id_label.text = ""

"""
