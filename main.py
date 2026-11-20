# main.py
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDFloatingActionButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivy.properties import StringProperty, NumericProperty
from kivy.metrics import dp

from database import Database
from parser import parse_phrase


class Tab(MDBoxLayout, MDTabsBase):
    pass


class AddOperationContent(MDBoxLayout):
    hint_text = StringProperty("")

    def __init__(self, op_type, **kwargs):
        super().__init__(**kwargs)
        self.op_type = op_type
        self.hint_text = (
            "Например: название один 3 штуки 1500"
            if op_type == "PURCHASE"
            else "Например: название три 2 штуки 720"
        )


def make_row(name, c1, c2, c3, extra_widget=None):
    """Единая строка: 4 колонки, высота 44, шрифт Caption. extra_widget — кнопка справа (опционально)."""
    box = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44))
    widths = [0.4, 0.15, 0.2, 0.25]
    values = [name, c1, c2, c3]
    for txt, w in zip(values, widths):
        box.add_widget(
            MDLabel(text=str(txt), halign="center", size_hint_x=w, font_style="Caption")
        )
    if extra_widget is not None:
        box.add_widget(extra_widget)
    return box

def make_stock_row(name, stock):
    """Строка для Остатка: 2 колонки, высота 44, шрифт Caption."""
    box = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44))
    box.add_widget(MDLabel(text=str(name), halign="center", size_hint_x=0.5, font_style="Caption"))
    box.add_widget(MDLabel(text=str(stock), halign="center", size_hint_x=0.5, font_style="Caption"))
    return box


class MainScreen(MDScreen):
    purchased_total = NumericProperty(0)
    sold_total = NumericProperty(0)
    profit = NumericProperty(0)

    def __init__(self, db: Database, **kwargs):
        self.db = db
        self.dialog = None
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        self.refresh()

    def refresh(self):
        if not hasattr(self, "db") or "purchases_list" not in self.ids:
            return
        totals = self.db.get_totals()
        self.purchased_total = totals["purchased_total"]
        self.sold_total = totals["sold_total"]
        self.profit = totals["profit"]

        self.ids.purchases_list.clear_widgets()
        self.ids.sales_list.clear_widgets()
        self.ids.stock_list.clear_widgets()

        for row in self.db.get_purchases_summary():
            btn = MDIconButton(
                icon="pencil",
                size_hint_x=None,
                width=dp(40),
                on_release=lambda x, pid=row["id"], nm=row["name"]: self.edit_product_name(pid, nm),
            )
            self.ids.purchases_list.add_widget(
                make_row(row["name"], f"{row['qty']:g}", f"{row['avg_price']:.0f}", f"{row['total_rub']:.0f}", extra_widget=btn)
            )
        for row in self.db.get_sales_summary():
            self.ids.sales_list.add_widget(
                make_row(row["name"], f"{row['qty']:g}", f"{row['avg_price']:.0f}", f"{row['total_rub']:.0f}")
            )
        for row in self.db.get_stock_summary():
            self.ids.stock_list.add_widget(
                make_stock_row(row["name"], f"{row['stock']:g}")
            )

    def open_add_dialog(self, op_type):
        content = AddOperationContent(op_type)
        self.dialog = MDDialog(
            title="Закупка" if op_type == "PURCHASE" else "Продажа",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="ОТМЕНА", on_release=lambda x: self.dialog.dismiss()),
                MDFlatButton(text="ДОБАВИТЬ", on_release=lambda x: self.submit_operation(op_type, content)),
            ],
        )
        self.dialog.open()

    def submit_operation(self, op_type, content):
        phrase = content.ids.phrase_field.text
        if not phrase.strip():
            return

        products = [p["name"] for p in self.db.get_all_products()]
        parsed = parse_phrase(phrase, products, default_type=op_type)

        if not parsed["name"]:
            self.show_error("Не удалось распознать название товара. Проверь справочник.")
            return

        qty = parsed["quantity"] if parsed["quantity"] is not None else 1.0
        product = self.db.get_product_by_name(parsed["name"])

        price = parsed["price"]
        if price is None:
            price = self.db.get_last_price(product["id"], op_type)
            if price is None:
                price = 0.0

        self.db.add_operation(product["id"], op_type, qty, price)
        self.dialog.dismiss()
        self.refresh()

    def open_history(self, op_type):
        hist = self.manager.get_screen("history")
        hist.load(op_type)
        self.manager.current = "history"

    def edit_product_name(self, product_id, current_name):
        from kivymd.uix.textfield import MDTextField
        content = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(80), padding=dp(8))
        field = MDTextField(text=current_name, hint_text="Новое название товара", mode="rectangle")
        content.add_widget(field)

        def save(*args):
            new_name = field.text.strip()
            if not new_name:
                return
            # если название не изменилось — просто закрыть
            if new_name == current_name:
                self.dialog.dismiss()
                return
            # проверка, что такого товара ещё нет
            existing = self.db.get_product_by_name(new_name)
            if existing and existing["id"] != product_id:
                self.dialog.dismiss()
                self.show_error(f"Товар «{new_name}» уже существует.")
                return
            self.db.update_product(product_id, new_name)
            self.dialog.dismiss()
            self.refresh()

        self.dialog = MDDialog(
            title="Переименовать товар",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="ОТМЕНА", on_release=lambda x: self.dialog.dismiss()),
                MDFlatButton(text="СОХРАНИТЬ", on_release=save),
            ],
        )
        self.dialog.open()

    def show_error(self, text):
        d = MDDialog(
            title="Ошибка",
            text=text,
            buttons=[MDFlatButton(text="ОК", on_release=lambda x: d.dismiss())],
        )
        d.open()


class HistoryScreen(MDScreen):
    def __init__(self, db: Database, main_screen, **kwargs):
        self.db = db
        self.main_screen = main_screen
        self.current_filter = None
        self.dialog = None
        super().__init__(**kwargs)

    def load(self, op_type):
        self.current_filter = op_type
        self.refresh()

    def refresh(self):
        if "history_list" not in self.ids:
            return
        self.ids.history_list.clear_widgets()
        rows = self.db.get_operations_by_type(self.current_filter)
        if not rows:
            self.ids.history_list.add_widget(
                MDLabel(text="Операций пока нет", halign="center", size_hint_y=None, height=dp(48))
            )
            return
        for r in rows:
            self.ids.history_list.add_widget(self._make_row(r))

    def _make_row(self, r):
        box = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48))

        dt = r["created_at"].replace("T", " ")[:16]
        try:
            date_part, time_part = dt.split(" ")
            y, m, d = date_part.split("-")
            short_dt = f"{d}.{m} {time_part}"
        except Exception:
            short_dt = dt

        op_label = "Зак" if r["op_type"] == "PURCHASE" else "Прод"
        values = [
            (short_dt, 0.25),
            (op_label, 0.12),
            (r["product_name"], 0.28),
            (f"{r['quantity']:g}", 0.1),
            (f"{r['price']:.0f}", 0.1),
            (f"{r['total']:.0f}", 0.15),
        ]
        for txt, w in values:
            box.add_widget(MDLabel(text=txt, halign="center", size_hint_x=w, font_style="Caption"))

        btn = MDIconButton(icon="delete", on_release=lambda x, op_id=r["id"]: self.confirm_delete(op_id))
        box.add_widget(btn)
        return box

    def confirm_delete(self, op_id):
        self.dialog = MDDialog(
            title="Удалить операцию?",
            text="Это действие нельзя отменить.",
            buttons=[
                MDFlatButton(text="ОТМЕНА", on_release=lambda x: self.dialog.dismiss()),
                MDFlatButton(text="УДАЛИТЬ", on_release=lambda x: self.do_delete(op_id)),
            ],
        )
        self.dialog.open()

    def do_delete(self, op_id):
        self.db.delete_operation(op_id)
        self.dialog.dismiss()
        self.refresh()
        self.main_screen.refresh()

    def go_back(self):
        tab_index = 1 if self.current_filter == "PURCHASE" else 2
        self.manager.current = "main"
        self.manager.get_screen("main").ids.tabs.carousel.index = tab_index


class TrackerApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.db = Database("inventory.db")

        for i in range(1, 11):
            self.db.add_product(f"название{i}")

        from kivy.lang import Builder
        Builder.load_file("main.kv")

        sm = MDScreenManager()
        main_screen = MainScreen(self.db, name="main")
        history_screen = HistoryScreen(self.db, main_screen, name="history")
        sm.add_widget(main_screen)
        sm.add_widget(history_screen)

        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: main_screen.refresh(), 0)
        return sm

    def on_stop(self):
        self.db.close()


if __name__ == "__main__":
    TrackerApp().run()