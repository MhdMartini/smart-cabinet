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
                elevation_normal: 5
                user_font_size: "30sp"
                size_hint: (None, None)
                size: dp(70), dp(70)
                md_bg_color: app.theme_cls.primary_color
                pos_hint: {"center_x": 0.5, "center_y": 0.4}
                on_release:
                    self.disabled = True
                    app.connect()


        MDSpinner:
            id: spinner2
            color: (0, 0.4, 0.7, 1) if self.active else (.98, .98, .98, 1)
            size_hint: None, None
            size: dp(80), dp(80)
            pos_hint: {'center_x': .5, 'center_y': .4}
            active: False

    Screen:
        name: "access_screen"
        MDFloatLayout:
            MDFloatingActionButton:
                elevation_normal: 12
                icon: "account-plus"
                md_bg_color: 0, 0.4, 0.7, 1
                pos_hint: {"center_y": 0.8, "center_x": 0.5}
                size_hint: (0.24, 0.133)
                user_font_size: "60sp"
                on_release: app.admin_routine("admin")
            MDFloatingActionButton:
                elevation_normal: 12
                icon: "account-multiple-plus"
                md_bg_color: 0, 0.4, 0.7, 0.6
                pos_hint: {"center_y": 0.55, "center_x": 0.5}
                size_hint: (0.24, 0.133)
                user_font_size: "60sp"
                on_release: app.admin_routine("student")
            MDFloatingActionButton:
                elevation_normal: 12
                icon: "barcode-scan"
                md_bg_color: 0, 0.4, 0.7, 0.4
                pos_hint: {"center_y": 0.3, "center_x": 0.5}
                size_hint: (0.24, 0.133)
                user_font_size: "60sp"
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
        on_touch_down: app.shrink_suggestions()

        MDFloatLayout:
            MDLabel:
                id: id_label
                text: ""
                font_style: "H4"
                theme_text_color: "Custom"
                text_color: 0, 0.4, 0.7, 1
                halign: "center"
                pos_hint: {"center_y": 0.8, "center_x": 0.5}
            MDTextField:
                id: identifier
                hint_text: ""
                helper_text: "Press Enter to Save"
                helper_text_mode: "persistent"
                icon_right: "account-arrow-right"
                icon_right_color: app.theme_cls.primary_color
                pos_hint:{'center_x': 0.5, 'center_y': 0.5}
                size_hint_x:None
                width:300
                disabled: True
                required: True
                color_mode: 'custom'
                line_color_focus: 0, 0.4, 0.7, 1
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
                    #identifier.hint_text = "Enter Name"
                    self.disabled = True


            MDIconButton:
                icon: "keyboard-backspace"
                pos_hint: {"center_y": .95, "center_x": .1}
                on_release:
                    app.back_btn()

            ScrollView:
                id: name_list
                pos_hint: {"center_x": 0.5, "center_y": 0.47}
                size_hint_x : 0.8
                size_hint_y : 0
                size_hint_x:None
                width:300
                MDList:
                    id: container
                    OneLineListItem:
                        id: name0
                        bg_color: app.theme_cls.primary_light
                        on_release:
                            identifier.text = self.text
                            name_list.size_hint_y = 0
                    OneLineListItem:
                        id: name1
                        bg_color: app.theme_cls.primary_light
                        on_release:
                            identifier.text = self.text
                            name_list.size_hint_y = 0
                    OneLineListItem:
                        id: name2
                        bg_color: app.theme_cls.primary_light
                        on_release:
                            identifier.text = self.text
                            name_list.size_hint_y = 0
                    OneLineListItem:
                        id: name3
                        bg_color: app.theme_cls.primary_light
                        text_color: 1,1,1,1
                        on_release:
                            identifier.text = self.text
                            name_list.size_hint_y = 0
                    OneLineListItem:
                        id: name4
                        bg_color: app.theme_cls.primary_light
                        on_release:
                            identifier.text = self.text
                            name_list.size_hint_y = 0

            MDSpinner:
                id: spinner
                color: (0, 0.4, 0.7, 1) if self.active else app.theme_cls.primary_light
                size_hint: None, None
                size: dp(60), dp(60)
                pos_hint: {'center_x': .5, 'center_y': .8}
                active: False

"""
