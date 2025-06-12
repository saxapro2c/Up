from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivy.uix.image import AsyncImage
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.properties import StringProperty
from kivymd.uix.list import OneLineListItem
from kivymd.uix.button import MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton
from bs4 import BeautifulSoup
from datetime import datetime
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivymd.uix.label import MDLabel
import sqlite3
import os
import shutil
import threading
import requests


def get_vyatsu_news():
    try:
        url = "https://www.vyatsu.ru/internet-gazeta.html"
        response = requests.get(url, timeout=10)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        news = []
        all_a_items = soup.find_all("a", class_="item")
        for a_tag in all_a_items:
            title_tag = a_tag.find("h6")
            title = title_tag.get_text(strip=True) if title_tag else "Без названия"

            # --- Парсим картинку ---
            img_tag = a_tag.find("img")
            if img_tag and img_tag.get("src"):
                img_url = img_tag["src"]
                # Заменяем "/tiny/" на "/"
                img_url = img_url.replace("/tiny/", "/")
                if not img_url.startswith("http"):
                    img_url = "https://www.vyatsu.ru" + img_url
            else:
                img_url = None

            preview = a_tag.find("div", class_="preview")
            description = preview.get_text(strip=True) if preview else ""
            link = "https://www.vyatsu.ru" + a_tag.get("href", "")

            news.append({
                "title": title,
                "link": link,
                "description": description,
                "image": img_url,
            })
            if len(news) >= 6:
                break
        return news
    except Exception as e:
        print("Ошибка загрузки новостей:", e)
        return []


def sync_vyatsu_news_to_db(db_manager):
    news_list = get_vyatsu_news()
    for item in news_list:
        external_link = item.get("link", "")
        title = item["title"]
        content = item["description"]
        image_path = item.get("image", "")
        # Проверяем, нет ли уже новости по ссылке
        cursor = db_manager.connection.cursor()
        cursor.execute("SELECT id FROM News WHERE external_link=?", (external_link,))
        result = cursor.fetchone()
        if not result:
            db_manager.add_news(title, content, image_path, author_id=1, external_link=external_link)
        cursor.close()


KV = '''
<DrawerClickableItem@MDNavigationDrawerItem>:
    focus_color: "#e7e4c0"
    text_color: "#4a4939"
    icon_color: "#4a4939"
    ripple_color: "#c5bdd2"
    selected_color: "#0c6c4d"

<DrawerLabelItem@MDNavigationDrawerItem>:
    text_color: "#4a4939"
    icon_color: "#4a4939"
    focus_behavior: False
    selected_color: "#4a4939"
    _no_ripple_effect: True

<NewsCard>:
    orientation: "vertical"
    size_hint_y: None
    height: self.minimum_height
    padding: "10dp"
    spacing: "10dp"
    md_bg_color: app.theme_cls.bg_normal
    radius: [18, 18, 18, 18]
    elevation: 3

    BoxLayout:
        size_hint_y: None
        height: "36dp"
        spacing: "10dp"

    AsyncImage:
        id: image
        size_hint_y: None
        height: "160dp"
        radius: [12, 12, 12, 12]
        source: root.image if hasattr(root, "image") and root.image else ""
        allow_stretch: True
        keep_ratio: True

    MDLabel:
        id: title
        text: ""
        font_style: "Subtitle1"
        bold: True
        adaptive_height: True
        theme_text_color: "Primary"

    MDLabel:
        id: content
        text: ""
        font_style: "Body2"
        adaptive_height: True
        theme_text_color: "Secondary"

    BoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: "28dp"
        spacing: "10dp"

        MDIconButton:
            id: like_btn
            icon: "thumb-up-outline"
            on_release: root.like_news()
        MDLabel:
            id: like_count
            text: "0"
            font_style: "Caption"
            size_hint_x: None
            width: "32dp"
        MDIconButton:
            id: comment_btn
            icon: "comment-outline"
            on_release: root.show_comments_popup()
        MDLabel:
            id: comment_count
            text: "0"
            font_style: "Caption"
            size_hint_x: None
            width: "32dp"


<ImageChooserPopup>:
    title: "Выберите изображение для новости"
    size_hint: 0.9, 0.9
    BoxLayout:
        orientation: 'vertical'
        FileChooserListView:
            id: filechooser
            filters: ['*.png', '*.jpg', '*.jpeg']
        BoxLayout:
            size_hint_y: None
            height: "50dp"
            MDRaisedButton:
                text: "Выбрать"
                on_release: root.select_image(filechooser.selection)
            MDRaisedButton:
                text: "Отмена"
                on_release: root.dismiss()

<CreateNewsScreen>:
    name: "create_news"
    selected_image_path: ""

    ScrollView:
        BoxLayout:
            orientation: 'vertical'
            padding: "20dp"
            spacing: "20dp"
            size_hint_y: None
            height: self.minimum_height

            MDTextField:
                id: news_title
                hint_text: "Заголовок новости"
                size_hint_x: None
                width: "300dp"
                pos_hint: {"center_x": 0.5}

            BoxLayout:
                size_hint_y: None
                height: "50dp"
                pos_hint: {"center_x": 0.5}

                MDRaisedButton:
                    text: "Выбрать изображение"
                    size_hint_x: None
                    width: "200dp"
                    on_release: root.choose_image()

            AsyncImage:
                id: news_image
                size_hint_y: None
                height: "200dp"
                source: root.selected_image_path if root.selected_image_path else ""
                pos_hint: {"center_x": 0.5}

            MDTextField:
                id: news_content
                hint_text: "Текст новости"
                multiline: True
                size_hint_x: None
                width: "300dp"
                height: "200dp"
                pos_hint: {"center_x": 0.5}

            MDRaisedButton:
                text: "Опубликовать"
                size_hint_x: None
                width: "200dp"
                pos_hint: {"center_x": 0.5}
                on_release: root.publish_news()

            MDRaisedButton:
                text: "Назад"
                size_hint_x: None
                width: "200dp"
                pos_hint: {"center_x": 0.5}
                on_release: root.manager.current = "news"

<NewsScreen>:
    name: "news"
    MDNavigationLayout:
        ScreenManager:
            Screen:
                BoxLayout:
                    orientation: "vertical"
                    MDTopAppBar:
                        title: "Новости"
                        elevation: 4
                        left_action_items: [["menu", lambda x: nav_drawer.set_state("open")]]
                    ScrollView:
                        BoxLayout:
                            id: news_feed
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: "12dp"
                            padding: "10dp"
        MDNavigationDrawer:
            id: nav_drawer
            radius: [0, dp(16), dp(16), 0]
            MDNavigationDrawerMenu:
                MDNavigationDrawerHeader:
                    title: "Меню"
                    title_color: "#4a4939"
                    text: "Выберите действие"
                    spacing: "4dp"
                    padding: "12dp", 0, 0, "56dp"

                DrawerClickableItem:
                    icon: "account"
                    text: "Личный кабинет"
                    on_release: 
                        root.manager.current = "profile"
                        nav_drawer.set_state("close")

                DrawerClickableItem:
                    icon: "home"
                    text: "Главная"
                    on_release: 
                        root.manager.current = "news"
                        nav_drawer.set_state("close")

                DrawerClickableItem:
                    icon: "account-school"
                    text: "Для педагога"
                    on_release:
                        app.go_to_teacher_screen()
                        nav_drawer.set_state("close")

                DrawerClickableItem:
                    icon: "school"
                    text: "Об образовании"
                    on_release: 
                        root.manager.current = "education"
                        nav_drawer.set_state("close")

                MDBoxLayout:
                    orientation: "horizontal"
                    spacing: "8dp"
                    padding: "16dp", "4dp", "16dp", "4dp"
                    adaptive_height: True

                    MDLabel:
                        text: "Темная тема"
                        theme_text_color: "Primary"

                    MDSwitch:
                        id: theme_switch
                        pos_hint: {"center_y": 0.5}
                        on_active: app.toggle_theme(self.active)

                MDNavigationDrawerDivider:

<ProfileScreen>:
    name: "profile"
    MDNavigationLayout:
        MDScreenManager:
            MDScreen:
                BoxLayout:
                    orientation: "vertical"
                    MDTopAppBar:
                        title: "Личный кабинет"
                        elevation: 4
                        left_action_items: [["menu", lambda x: nav_drawer.set_state("toggle")]]
                    BoxLayout:
                        orientation: "vertical"
                        padding: "20dp"
                        spacing: "10dp"
                        Widget:
                        MDLabel:
                            id: profile_label
                            text: ""
                            halign: "center"
                            valign: "center"
                            markup: True
                        Widget:
                        MDRaisedButton:
                            text: "Выйти"
                            size_hint: None, None
                            size: "120dp", "40dp"
                            pos_hint: {"center_x": 0.5}
                            on_release: app.logout()
        MDNavigationDrawer:
            id: nav_drawer
            radius: [0, dp(16), dp(16), 0]
            MDNavigationDrawerMenu:
                MDNavigationDrawerHeader:
                    title: "Меню"
                    title_color: "#4a4939"
                    text: "Выберите действие"
                    spacing: "4dp"
                    padding: "12dp", 0, 0, "56dp"
                DrawerClickableItem:
                    icon: "account"
                    text: "Личный кабинет"
                    on_release:
                        root.manager.current = "profile"
                        nav_drawer.set_state("close")
                DrawerClickableItem:
                    icon: "home"
                    text: "Главная"
                    on_release:
                        root.manager.current = "news"
                        nav_drawer.set_state("close")
                DrawerClickableItem:
                    icon: "account-school"
                    text: "Для педагога"
                    on_release:
                        app.go_to_teacher_screen()
                        nav_drawer.set_state("close")
                DrawerClickableItem:
                    icon: "school"
                    text: "Об образовании"
                    on_release:
                        root.manager.current = "education"
                        nav_drawer.set_state("close")
                MDNavigationDrawerDivider:


<TeacherScreen>:
    name: "teacher"
    MDNavigationLayout:
        ScreenManager:
            Screen:
                BoxLayout:
                    orientation: "vertical"
                    MDTopAppBar:
                        title: "Для педагога"
                        elevation: 4
                        left_action_items: [["menu", lambda x: nav_drawer.set_state("open")]]
                    BoxLayout:
                        id: chat_box
                        orientation: "vertical"
                        padding: "10dp"
                        ScrollView:
                            MDBoxLayout:
                                id: chat_list
                                orientation: "vertical"
                                size_hint_y: None
                                height: self.minimum_height
                        BoxLayout:
                            size_hint_y: None
                            height: "56dp"
                            MDTextField:
                                id: chat_input
                                hint_text: "Введите сообщение"
                                mode: "rectangle"
                            MDRaisedButton:
                                text: "Отправить"
                                on_release: root.send_message()

        MDNavigationDrawer:
            id: nav_drawer
            radius: [0, dp(16), dp(16), 0]
            MDNavigationDrawerMenu:
                MDNavigationDrawerHeader:
                    title: "Меню"
                    title_color: "#4a4939"
                    text: "Выберите действие"
                    spacing: "4dp"
                    padding: "12dp", 0, 0, "56dp"

                DrawerClickableItem:
                    icon: "account"
                    text: "Личный кабинет"
                    on_release:
                        root.manager.current = "profile"
                        nav_drawer.set_state("close")
                DrawerClickableItem:
                    icon: "home"
                    text: "Главная"
                    on_release:
                        root.manager.current = "news"
                        nav_drawer.set_state("close")
                DrawerClickableItem:
                    icon: "account-school"
                    text: "Для педагога"
                    on_release:
                        app.go_to_teacher_screen()
                        nav_drawer.set_state("close")
                DrawerClickableItem:
                    icon: "school"
                    text: "Об образовании"
                    on_release:
                        root.manager.current = "education"
                        nav_drawer.set_state("close")
                MDNavigationDrawerDivider:


<EducationScreen>:
    name: "education"
    MDNavigationLayout:
        ScreenManager:
            Screen:
                BoxLayout:
                    orientation: "vertical"
                    MDTopAppBar:
                        title: "Об образовании"
                        elevation: 4
                        left_action_items: [["menu", lambda x: nav_drawer.set_state("open")]]
                    ScrollView:
                        MDBoxLayout:
                            id: specialty_list
                            orientation: "vertical"
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: "16dp"
                            padding: "10dp"

        MDNavigationDrawer:
            id: nav_drawer
            radius: [0, dp(16), dp(16), 0]
            MDNavigationDrawerMenu:
                MDNavigationDrawerHeader:
                    title: "Меню"
                    title_color: "#4a4939"
                    text: "Выберите действие"
                    spacing: "4dp"
                    padding: "12dp", 0, 0, "56dp"

                DrawerClickableItem:
                    icon: "account"
                    text: "Личный кабинет"
                    on_release:
                        root.manager.current = "profile"
                        nav_drawer.set_state("close")
                DrawerClickableItem:
                    icon: "home"
                    text: "Главная"
                    on_release:
                        root.manager.current = "news"
                        nav_drawer.set_state("close")
                DrawerClickableItem:
                    icon: "account-school"
                    text: "Для педагога"
                    on_release:
                        app.go_to_teacher_screen()
                        nav_drawer.set_state("close")
                DrawerClickableItem:
                    icon: "school"
                    text: "Об образовании"
                    on_release:
                        root.manager.current = "education"
                        nav_drawer.set_state("close")
                MDNavigationDrawerDivider:

<LoginScreen>:
    name: "login"
    BoxLayout:
        orientation: 'vertical'
        padding: "20dp"
        spacing: "20dp"
        pos_hint: {"center_x": 0.5, "center_y": 0.5}
        size_hint: None, None
        size: "300dp", "300dp"

        MDTextField:
            id: username
            hint_text: "Логин"
            helper_text_mode: "on_error"
            size_hint_x: None
            width: "240dp"
            pos_hint: {"center_x": 0.5}

        MDTextField:
            id: password
            hint_text: "Пароль"
            password: True
            helper_text_mode: "on_error"
            size_hint_x: None
            width: "240dp"
            pos_hint: {"center_x": 0.5}

        MDFillRoundFlatButton:
            id: login_btn
            text: "Войти"
            size_hint_x: None
            width: "200dp"
            pos_hint: {"center_x": 0.5}
            on_release: root.try_login()

        MDFlatButton:
            text: "Регистрация"
            pos_hint: {"center_x": 0.5}
            on_release: root.manager.current = "register"

<RegisterScreen>:
    name: "register"
    BoxLayout:
        orientation: "vertical"
        padding: "20dp"
        spacing: "20dp"
        size_hint: None, None
        size: "300dp", "340dp"
        pos_hint: {"center_x": 0.5, "center_y": 0.5}

        MDTextField:
            id: reg_username
            hint_text: "Логин"
            helper_text_mode: "on_error"
            size_hint_x: None
            width: "240dp"
            pos_hint: {"center_x": 0.5}

        MDTextField:
            id: reg_password
            hint_text: "Пароль"
            password: True
            helper_text_mode: "on_error"
            size_hint_x: None
            width: "240dp"
            pos_hint: {"center_x": 0.5}

        MDTextField:
            id: reg_confirm
            hint_text: "Повторите пароль"
            password: True
            helper_text_mode: "on_error"
            size_hint_x: None
            width: "240dp"
            pos_hint: {"center_x": 0.5}

        MDLabel:
            text: "Вы учитель?"
            halign: "center"

        MDSwitch:
            id: teacher_switch
            pos_hint: {"center_x": 0.5}

        MDRaisedButton:
            text: "Зарегистрироваться"
            size_hint_x: None
            width: "200dp"
            pos_hint: {"center_x": 0.5}
            on_release: root.register_user()

        MDFlatButton:
            text: "Назад"
            pos_hint: {"center_x": 0.5}
            on_release: root.manager.current = "login"

'''


class CommentItem(BoxLayout):
    def __init__(self, login, text, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=56, spacing=8, padding=(8, 4, 8, 4),
                         **kwargs)
        # Аватарка (ставь свою картинку или делай сгенерированный цвет)
        self.add_widget(Image(source='default_avatar.png', size_hint=(None, None), size=(40, 40)))
        vbox = BoxLayout(orientation='vertical', spacing=2)
        vbox.add_widget(MDLabel(text=f"[b]{login}[/b]", markup=True, font_style='Caption', size_hint_y=None, height=20))
        vbox.add_widget(MDLabel(text=text, font_style='Body2', size_hint_y=None, height=28))
        self.add_widget(vbox)


class ProfileScreen(MDScreen):
    def on_pre_enter(self):
        app = MDApp.get_running_app()
        username = app.current_user_login
        password = app.current_user_password
        self.ids.profile_label.text = f"Логин: [b]{username}[/b]\nПароль: [b]{password}[/b]"


class ImageChooserPopup(Popup):
    def select_image(self, selection):
        if selection:
            selected_path = selection[0]
            create_news_screen = MDApp.get_running_app().root.get_screen('create_news')
            create_news_screen.selected_image_path = selected_path
            create_news_screen.ids.news_image.source = selected_path
            self.dismiss()


class RegisterScreen(MDScreen):
    def register_user(self):
        username = self.ids.reg_username.text.strip()
        password = self.ids.reg_password.text.strip()
        confirm = self.ids.reg_confirm.text.strip()
        is_teacher = self.ids.teacher_switch.active
        role = "педагог" if is_teacher else "студент"

        self.ids.reg_username.error = False
        self.ids.reg_password.error = False
        self.ids.reg_confirm.error = False

        # Проверки на пустые поля
        if not username:
            self.ids.reg_username.error = True
            self.ids.reg_username.helper_text = "Введите логин"
            return
        if not password:
            self.ids.reg_password.error = True
            self.ids.reg_password.helper_text = "Введите пароль"
            return
        if not confirm:
            self.ids.reg_confirm.error = True
            self.ids.reg_confirm.helper_text = "Повторите пароль"
            return

        if password != confirm:
            self.ids.reg_confirm.error = True
            self.ids.reg_confirm.helper_text = "Пароли не совпадают"
            return

        app = MDApp.get_running_app()
        if app.db_manager.create_user(username, password, role):
            self.show_dialog("Успех", "Регистрация прошла успешно!")
            self.manager.current = "login"
        else:
            self.show_dialog("Ошибка", "Такой логин уже существует!")

    def show_dialog(self, title, text):
        dialog = MDDialog(
            title=title,
            text=text,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
        )
        dialog.open()


class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.create_tables()
            print("Успешное подключение к базе данных")
            return True
        except sqlite3.Error as e:
            print(f"Ошибка подключения к базе данных: {e}")
            return False

    def create_tables(self):
        """Создание таблиц, если они не существуют"""
        cursor = self.connection.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS News (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            author_id INTEGER,
            external_link TEXT UNIQUE,  -- <== добавили
            FOREIGN KEY (author_id) REFERENCES Account_Data(id)
        )
        ''')

        # Таблица для пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Account_Data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id INTEGER,
                user_login TEXT,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (news_id) REFERENCES News(id)
            )
        ''')

        # Добавляем таблицу лайков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id INTEGER,
                user_login TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (news_id) REFERENCES News(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS SpecialtyLikes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                specialty_id INTEGER,
                user_login TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(specialty_id, user_login)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Specialties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                descript TEXT,
                places INTEGER NOT NULL,
                pass_score INTEGER NOT NULL
            )
        ''')

        self.connection.commit()
        cursor.close()

    def check_user(self, username, password):
        """Проверка пользователя в базе данных"""
        if not self.connection:
            return False

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT * FROM Account_Data WHERE login = ? AND password = ?",
                (username, password)
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Ошибка при проверке пользователя: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def add_specialty_like(self, specialty_id, user_login):
        cursor = self.connection.cursor()
        try:
            print(f"DEBUG: добавляем лайк — {specialty_id=}, {user_login=}")
            cursor.execute("""
                INSERT OR IGNORE INTO SpecialtyLikes (specialty_id, user_login)
                VALUES (?, ?)
            """, (specialty_id, user_login))
            self.connection.commit()
        finally:
            cursor.close()

    def count_specialty_likes(self, specialty_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM SpecialtyLikes WHERE specialty_id = ?
        """, (specialty_id,))
        count = cursor.fetchone()[0]
        cursor.close()
        return count

    def add_news(self, title, content, image_path="", author_id=1, external_link=None):
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO News (title, content, image_path, author_id, external_link) VALUES (?, ?, ?, ?, ?)",
                (title, content, image_path, author_id, external_link)
            )
            self.connection.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Ошибка при добавлении новости: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_all_news(self):
        """Получение всех новостей"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM News ORDER BY created_at DESC")
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Ошибка при получении новостей: {e}")
            return []
        finally:
            if cursor:
                cursor.close()

    def get_all_specialties(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT code, name, descript, places, pass_score FROM Specialties")
        result = cursor.fetchall()
        cursor.close()
        return result

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            self.connection.close()

    def create_user(self, username, password, role="студент"):
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO Account_Data (login, password, role) VALUES (?, ?, ?)",
                (username, password, role)
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"Ошибка при регистрации пользователя: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def add_comment(self, news_id, user_login, text):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO Comments (news_id, user_login, text) VALUES (?, ?, ?)",
            (news_id, user_login, text)
        )
        self.connection.commit()
        cursor.close()

    def get_comments(self, news_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT user_login, text, created_at FROM Comments WHERE news_id=? ORDER BY created_at ASC",
                       (news_id,))
        comments = cursor.fetchall()
        cursor.close()
        return comments

    def count_comments(self, news_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM Comments WHERE news_id=?", (news_id,))
        count = cursor.fetchone()[0]
        cursor.close()
        return count

    def add_teacher_message(self, login, message):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO TeacherChat (login, message) VALUES (?, ?)", (login, message))
        self.connection.commit()
        cursor.close()

    def get_teacher_messages(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT login, message, timestamp FROM TeacherChat ORDER BY timestamp ASC")
        result = cursor.fetchall()
        cursor.close()
        return result

    def add_like(self, news_id, user_login):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM Likes WHERE news_id=? AND user_login=?", (news_id, user_login))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO Likes (news_id, user_login) VALUES (?, ?)", (news_id, user_login))
            self.connection.commit()
        cursor.close()

    def count_likes(self, news_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM Likes WHERE news_id=?", (news_id,))
        count = cursor.fetchone()[0]
        cursor.close()
        return count


class LoginScreen(MDScreen):
    def try_login(self):
        username = self.ids.username.text.strip()
        password = self.ids.password.text.strip()

        # Сброс предыдущих ошибок
        self.ids.username.error = False
        self.ids.password.error = False

        # Проверка заполнения полей
        if not username:
            self.ids.username.error = True
            self.ids.username.helper_text = "Введите логин"
            return

        if not password:
            self.ids.password.error = True
            self.ids.password.helper_text = "Введите пароль"
            return

        # Проверка в базе данных
        app = MDApp.get_running_app()
        if app.db_manager.check_user(username, password):
            app.current_user_login = username
            app.current_user_password = password
            self.manager.current = "news"
        else:
            self.ids.username.error = True
            self.ids.password.error = True
            self.ids.username.helper_text = "Неверный логин или пароль"

        cursor = app.db_manager.connection.cursor()
        cursor.execute("SELECT role FROM Account_Data WHERE login=? AND password=?", (username, password))
        result = cursor.fetchone()
        if result:
            app.current_user_role = result[0]


class CreateNewsScreen(MDScreen):
    selected_image_path = StringProperty("")

    def choose_image(self):
        popup = ImageChooserPopup()
        popup.open()

    def publish_news(self):
        title = self.ids.news_title.text.strip()
        content = self.ids.news_content.text.strip()

        if not title:
            self.show_dialog("Ошибка", "Введите заголовок новости")
            return

        if not content:
            self.show_dialog("Ошибка", "Введите текст новости")
            return

        # Сохраняем изображение в папку приложения
        image_path = ""
        if self.selected_image_path:
            images_dir = os.path.join(os.path.dirname(__file__), "images")
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)

            # Генерируем уникальное имя файла
            ext = os.path.splitext(self.selected_image_path)[1]
            filename = f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            image_path = os.path.join("images", filename)

            try:
                shutil.copy2(self.selected_image_path, os.path.join(os.path.dirname(__file__), image_path))
            except Exception as e:
                print(f"Ошибка копирования изображения: {e}")
                image_path = ""

        # Добавляем новость в базу данных
        app = MDApp.get_running_app()
        news_id = app.db_manager.add_news(title, content, image_path)

        if news_id:
            self.show_dialog("Успех", f"Новость #{news_id} успешно опубликована!")
            self.clear_fields()
            self.manager.current = "news"
        else:
            self.show_dialog("Ошибка", "Не удалось сохранить новость")

    def clear_fields(self):
        self.ids.news_title.text = ""
        self.ids.news_content.text = ""
        self.selected_image_path = ""
        self.ids.news_image.source = ""

    def show_dialog(self, title, text):
        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()


class NewsCard(MDCard):
    news_id = None

    def like_news(self):
        app = MDApp.get_running_app()
        user_login = app.current_user_login or "Гость"
        if self.news_id:
            app.db_manager.add_like(self.news_id, user_login)
            self.update_like_count()

    def update_like_count(self):
        app = MDApp.get_running_app()
        if self.news_id:
            count = app.db_manager.count_likes(self.news_id)
            self.ids.like_count.text = str(count)

    def show_comments_popup(self):
        popup = CommentsPopup(news_id=self.news_id)
        popup.open()

    def update_comment_count(self):
        app = MDApp.get_running_app()
        if self.news_id:
            count = app.db_manager.count_comments(self.news_id)
            self.ids.comment_count.text = str(count)


class NewsScreen(MDScreen):
    def on_enter(self):
        app = MDApp.get_running_app()
        sync_vyatsu_news_to_db(app.db_manager)
        self.load_news_from_db()

    def load_news_from_db(self):
        self.ids.news_feed.clear_widgets()
        app = MDApp.get_running_app()
        news_items = app.db_manager.get_all_news()
        for news in news_items:
            # Учитываем новое поле в выборке
            if len(news) == 7:
                news_id, title, content, image_path, created_at, author_id, external_link = news
            else:
                news_id, title, content, image_path, created_at, author_id = news
                external_link = None
            card = NewsCard()
            card.news_id = news_id
            card.ids.title.text = title
            card.ids.content.text = content
            card.ids.image.source = image_path if image_path else "https://via.placeholder.com/300x200"
            card.update_like_count()
            card.update_comment_count()
            self.ids.news_feed.add_widget(card)

    def load_online_news(self):
        self.ids.news_feed.clear_widgets()
        # Карточка-заглушка
        loading_card = NewsCard()
        loading_card.ids.title.text = "Загрузка новостей..."
        loading_card.ids.content.text = ""
        self.ids.news_feed.add_widget(loading_card)

        def fetch_and_show():
            news_list = get_vyatsu_news()

            def update_ui(*_):
                self.ids.news_feed.clear_widgets()
                if not news_list:
                    card = NewsCard()
                    card.ids.title.text = "Не удалось загрузить новости"
                    card.ids.content.text = "Проверьте интернет-соединение."
                    self.ids.news_feed.add_widget(card)
                else:
                    for item in news_list:
                        card = NewsCard()
                        card.ids.title.text = item["title"]
                        card.ids.content.text = item["description"]
                        card.ids.image.source = item["image"] if item[
                            "image"] else "https://via.placeholder.com/300x200"
                        # card.ids.image — УБРАНО!
                        self.ids.news_feed.add_widget(card)

            from kivy.clock import Clock
            Clock.schedule_once(update_ui)

        import threading
        threading.Thread(target=fetch_and_show, daemon=True).start()

    # def load_news(self):
    #     app = MDApp.get_running_app()
    #     news_items = app.db_manager.get_all_news()
    #
    #     news_feed = self.ids.news_feed
    #     news_feed.clear_widgets()
    #
    #     for news in news_items:
    #         news_id, title, content, image_path, created_at, author_id = news
    #         news_card = NewsCard()
    #
    #         # Устанавливаем данные
    #         news_card.ids.title.text = title
    #         news_card.ids.content.text = content
    #
    #         # Устанавливаем изображение
    #         if image_path:
    #             full_path = os.path.join(os.path.dirname(__file__), image_path)
    #             if os.path.exists(full_path):
    #                 news_card.ids.image.source = full_path
    #             else:
    #                 news_card.ids.image.source = "https://via.placeholder.com/300x200"
    #         else:
    #             news_card.ids.image.source = "https://via.placeholder.com/300x200"
    #
    #         news_feed.add_widget(news_card)


class TeacherScreen(MDScreen):
    def on_enter(self):
        app = MDApp.get_running_app()
        if app.get_user_role() != "педагог":
            self.ids.chat_list.clear_widgets()
            self.ids.chat_list.add_widget(MDLabel(text="Только для педагогов", halign="center"))
            return
        self.load_messages()

    def load_messages(self):
        self.ids.chat_list.clear_widgets()
        messages = MDApp.get_running_app().db_manager.get_teacher_messages()
        for login, msg, _ in messages:
            label = MDLabel(text=f"[b]{login}:[/b] {msg}", markup=True, size_hint_y=None, height="24dp")
            self.ids.chat_list.add_widget(label)

    def send_message(self):
        app = MDApp.get_running_app()
        msg = self.ids.chat_input.text.strip()
        if msg:
            app.db_manager.add_teacher_message(app.current_user_login, msg)
            self.ids.chat_input.text = ""
            self.load_messages()


class EducationScreen(MDScreen):

    def like_specialty(self, specialty_id):
        app = MDApp.get_running_app()
        app.db_manager.add_specialty_like(specialty_id, app.current_user_login)
        self.on_enter()

    def on_enter(self):
        self.ids.specialty_list.clear_widgets()
        app = MDApp.get_running_app()
        specialties = app.db_manager.get_all_specialties()
        # print("DEBUG specialties:", specialties)  # Чтобы дебажить

        if not specialties:
            lbl = MDLabel(text="Нет данных о специальностях.", halign="center")
            self.ids.specialty_list.add_widget(lbl)
            return

        for code, name, descript, places, pass_score in specialties:
            cursor = app.db_manager.connection.cursor()
            cursor.execute("SELECT id FROM Specialties WHERE code=? AND name=?", (code, name))
            row = cursor.fetchone()
            if not row:
                continue
            specialty_id = row[0]
            cursor.close()
            card = MDCard(
                orientation="vertical",
                size_hint_y=None, height=160,
                padding=[16, 10, 16, 10],
                spacing=6,
                radius=[14],
                elevation=2,
                md_bg_color=(1, 1, 1, 1)
            )

            # Заголовок
            card.add_widget(
                MDLabel(
                    text=f"[b]{code} {name}[/b]",
                    font_style="Subtitle1",
                    markup=True,
                    theme_text_color="Primary",
                    adaptive_height=True
                )
            )

            # Описание
            card.add_widget(
                MDLabel(
                    text=descript,
                    font_style="Body2",
                    theme_text_color="Secondary",
                    adaptive_height=True
                )
            )

            # Инфо-блок
            info_row = MDBoxLayout(orientation="horizontal", spacing=32)
            info_row.add_widget(
                MDLabel(
                    text=f"[b]Кол-во мест:[/b] {places}",
                    markup=True,
                    font_style="Body2",
                    theme_text_color="Secondary"
                )
            )
            info_row.add_widget(
                MDLabel(
                    text=f"[b]Проходной балл:[/b] {pass_score}",
                    markup=True,
                    font_style="Body2",
                    theme_text_color="Secondary"
                )
            )

            like_row = MDBoxLayout(orientation="horizontal", spacing=4, padding=(0, 8), size_hint_y=None, height="32dp")
            like_btn = MDIconButton(
                icon="thumb-up-outline",
                theme_text_color="Custom",
                text_color=(0, 0.5, 1, 1),
                on_release=lambda x, sid=specialty_id: self.like_specialty(sid)
            )
            like_label = MDLabel(
                text=str(app.db_manager.count_specialty_likes(specialty_id)),
                font_style="Caption",
                size_hint_x=None,
                width="32dp",
                halign="left"
            )
            like_row.add_widget(like_btn)
            like_row.add_widget(like_label)

            like_row = MDBoxLayout(orientation="horizontal", spacing=4, size_hint_y=None, height="32dp")
            like_btn = MDIconButton(
                icon="thumb-up-outline",
                on_release=lambda x, sid=specialty_id: self.like_specialty(sid)
            )
            like_count = MDLabel(
                text=str(app.db_manager.count_specialty_likes(specialty_id)),
                font_style="Caption",
                size_hint_x=None,
                width="30dp"
            )
            like_row.add_widget(like_btn)
            like_row.add_widget(like_count)
            card.add_widget(info_row)
            self.ids.specialty_list.add_widget(card)


class CommentsPopup(Popup):
    def __init__(self, news_id, **kwargs):
        super().__init__(**kwargs)
        self.news_id = news_id
        self.title = "Комментарии"
        self.size_hint = (0.95, 0.8)
        self.background = ''  # прозрачный фон
        self.background_color = (0.95, 0.95, 0.95, 1)

        box = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Список комментариев
        self.comments_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        self.comments_box.bind(minimum_height=self.comments_box.setter('height'))

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.comments_box)
        box.add_widget(scroll)

        # Нижний бар для ввода комментария
        input_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp', spacing=10)
        self.text_input = MDTextField(hint_text="Написать комментарий...", mode="rectangle", size_hint_x=0.8)
        send_btn = MDRaisedButton(text="Отправить", on_release=self.add_comment, size_hint_x=0.2)
        input_bar.add_widget(self.text_input)
        input_bar.add_widget(send_btn)

        box.add_widget(input_bar)
        self.add_widget(box)
        self.load_comments()

    def load_comments(self):
        self.comments_box.clear_widgets()
        app = MDApp.get_running_app()
        comments = app.db_manager.get_comments(self.news_id)
        for login, text, dt in comments:
            card = MDCard(
                orientation='vertical',
                size_hint_y=None,
                height='64dp',
                padding=[12, 6, 12, 6],
                md_bg_color=[1, 1, 1, 1],
                radius=[14, 14, 14, 14],
                elevation=2,
            )
            user_label = MDLabel(
                text=f"[b]{login}[/b]",
                markup=True,
                font_style="Subtitle2",
                theme_text_color="Primary",
                size_hint_y=None,
                height="18dp"
            )
            comment_label = MDLabel(
                text=text,
                font_style="Body2",
                theme_text_color="Secondary",
                size_hint_y=None,
                height="22dp"
            )
            card.add_widget(user_label)
            card.add_widget(comment_label)
            self.comments_box.add_widget(card)

    def add_comment(self, *args):
        app = MDApp.get_running_app()
        user_login = app.current_user_login or "Гость"
        text = self.text_input.text.strip()
        if text:
            app.db_manager.add_comment(self.news_id, user_login, text)
            self.text_input.text = ""
            self.load_comments()


class AuthApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

        # Инициализация базы данных
        db_path = os.path.join(os.path.dirname(__file__), "diplom2.db")
        self.db_manager = DatabaseManager(db_path)
        if not self.db_manager.connect():
            self.show_error("Ошибка базы данных", "Не удалось подключиться к базе данных")

        # Загрузка KV-разметки
        Builder.load_string(KV)

        # Создание экранов
        sm = MDScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(RegisterScreen(name="register"))
        sm.add_widget(NewsScreen(name="news"))
        sm.add_widget(CreateNewsScreen(name="create_news"))
        sm.add_widget(TeacherScreen(name="teacher"))
        sm.add_widget(EducationScreen(name="education"))
        sm.add_widget(ProfileScreen(name="profile"))

        return sm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user_login = None
        self.current_user_password = None
        self.current_user_role = None

    def get_user_role(self):
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT role FROM Account_Data WHERE login=?", (self.current_user_login,))
        row = cursor.fetchone()
        return row[0] if row else "студент"

    def go_to_teacher_screen(self):
        if self.current_user_role == "педагог":
            self.root.current = "teacher"
        else:
            self.dialog = MDDialog(
                title="Отказано в доступе",
                text="Вы не являетесь педагогом.",
                buttons=[
                    MDFlatButton(
                        text="ОК",
                        on_release=self.close_dialog
                    )
                ]
            )
            self.dialog.open()

    def close_dialog(self, *args):
        if hasattr(self, 'dialog'):
            self.dialog.dismiss()

    def toggle_theme(self, is_dark):
        self.theme_cls.theme_style = "Dark" if is_dark else "Light"

    def show_error(self, title, message):
        """Показать диалог с ошибкой"""
        MDDialog(
            title=title,
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.stop()
                )
            ]
        ).open()


if __name__ == '__main__':
    AuthApp().run()