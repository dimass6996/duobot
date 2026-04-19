import flet as ft
import asyncio
import websockets
import json
import os
import requests
import uuid

SERVER_HOST = os.getenv("DUOCHAT_SERVER", "localhost")
SERVER_PORT = os.getenv("DUOCHAT_PORT", "8000")
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

COLORS = {
    "bg": "#09090b",
    "card_bg": "#18181b",
    "my_msg": "#4f46e5",
    "their_msg": "#27272a",
    "text": "#e5e5e5",
    "text_secondary": "#a1a1aa",
    "accent": "#6366f1",
    "input_bg": "#27272a",
    "border": "#3f3f46",
    "pinned": "#fbbf24",
}


async def main(page: ft.Page):
    page.title = "DuoChat"
    page.theme_mode = "dark"
    page.window_width = 360
    page.window_height = 640
    page.padding = 0
    page.bgcolor = COLORS["bg"]

    class Storage:
        def __init__(self, page):
            self.page = page
            self._data = {"name": "", "pinned": [], "recent": []}
            
        async def init(self):
            try:
                if hasattr(self.page, 'client_storage'):
                    saved_str = await self.page.client_storage.get("duochat_data")
                    if saved_str:
                        self._data = json.loads(saved_str)
            except:
                pass
                
        async def save(self):
            try:
                if hasattr(self.page, 'client_storage'):
                    await self.page.client_storage.set("duochat_data", json.dumps(self._data))
            except:
                pass
                
        def get(self, key):
            return self._data.get(key, "")
            
        def set(self, key, value):
            self._data[key] = value
            
        def get_list(self, key):
            return self._data.get(key, [])
            
        def set_list(self, key, value):
            self._data[key] = value

    app_storage = Storage(page)
    await app_storage.init()

    class State:
        ws = None
        my_name = app_storage.get("name") or None
        dialog_code = None
    state = State()

    chat_messages = ft.ListView(expand=True, spacing=12, auto_scroll=True, padding=10)
    message_input = ft.TextField(
        hint_text="Сообщение...",
        expand=True,
        bgcolor=COLORS["input_bg"],
        border_color="transparent",
        focused_border_color=COLORS["accent"],
        border_radius=20,
        content_padding=15,
    )

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    clipboard = ft.Clipboard()
    page.services.append(clipboard)

    async def save_data():
        app_storage.set("name", state.my_name or "")
        app_storage.set_list("pinned", app_storage.get_list("pinned"))
        app_storage.set_list("recent", app_storage.get_list("recent"))
        await app_storage.save()

    async def vibrate():
        try:
            if hasattr(page, 'platform'):
                pass
        except:
            pass

    async def send_message():
        if state.ws and message_input.value:
            try:
                payload = json.dumps({
                    "action": "message",
                    "text": message_input.value
                })
                await state.ws.send(payload)
                message_input.value = ""
                await update_recent_chat(state.dialog_code)
                page.update()
            except Exception as e:
                print("Send error:", e)

    async def attach_click(e):
        files = await file_picker.pick_files()
        if files:
            for f in files:
                print(f"Selected: {f.path}")

    async def update_recent_chat(code):
        recent = app_storage.get_list("recent")
        if code in recent:
            recent.remove(code)
        recent.insert(0, code)
        recent = recent[:5]
        app_storage.set_list("recent", recent)
        await app_storage.save()

    async def toggle_pin(code):
        pinned = app_storage.get_list("pinned")
        if code in pinned:
            pinned.remove(code)
        else:
            pinned.insert(0, code)
        app_storage.set_list("pinned", pinned[:5])
        await app_storage.save()

    async def connect_ws():
        uri = f"ws://{SERVER_HOST}:{SERVER_PORT}/ws"
        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    state.ws = websocket
                    await websocket.send(json.dumps({
                        "action": "join",
                        "dialog_code": state.dialog_code,
                        "name": state.my_name
                    }))
                    while True:
                        msg_raw = await websocket.recv()
                        try:
                            data = json.loads(msg_raw)
                        except:
                            data = {"text": msg_raw, "sender": "unknown"}

                        text = data.get("text", "")
                        sender = data.get("sender", "unknown")
                        is_me = sender == state.my_name

                        await add_message(sender, text, is_me)
                        page.update()
            except Exception as e:
                print("WS error:", e)
                await asyncio.sleep(3)

    async def add_message(sender, text, is_me=False):
        name_color = "#818cf8" if is_me else "#d4d4d8"
        
        bubble = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(
                                sender[:2].upper(),
                                size=10,
                                weight=ft.FontWeight.W_700,
                                color=COLORS["bg"]
                            ),
                            bgcolor=name_color,
                            width=20,
                            height=20,
                            border_radius=10,
                            alignment=ft.Alignment(0, 0)
                        ),
                        ft.Text(
                            sender,
                            size=11,
                            color=name_color,
                            weight=ft.FontWeight.W_600,
                        ),
                    ], spacing=6),
                    margin=ft.Margin(0, 0, 0, 4)
                ),
                ft.Text(
                    text,
                    size=15,
                    color=COLORS["text"],
                    selectable=True
                ),
            ], spacing=4, tight=True),
            bgcolor=COLORS["my_msg"] if is_me else COLORS["their_msg"],
            padding=ft.Padding(12, 10, 12, 10),
            border_radius=20,
            shadow=ft.BoxShadow(
                blur_radius=10,
                color="#00000040",
                offset=ft.Offset(0, 3)
            ),
            width=280
        )
        
        if is_me:
            bubble.alignment = ft.Alignment(0.9, 0)
            bubble.margin = ft.Margin(40, 0, 0, 0)
        else:
            bubble.alignment = ft.Alignment(-0.9, 0)
            bubble.margin = ft.Margin(0, 0, 40, 0)
        
        chat_messages.controls.append(bubble)

    async def show_chat():
        page.clean()
        message_input.value = ""
        chat_messages.controls.clear()

        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["bg"],
                content=ft.Column([
                    ft.Container(
                        padding=ft.Padding(15, 8, 15, 8),
                        bgcolor=f"{COLORS['card_bg']}f5",
                        content=ft.Row([
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                icon_color=COLORS["text_secondary"],
                                on_click=lambda _: asyncio.create_task(show_home())
                            ),
                            ft.Text(
                                f"#{state.dialog_code}",
                                size=16,
                                color=COLORS["text"],
                                weight=ft.FontWeight.W_600,
                                expand=True
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CONTENT_COPY,
                                icon_color=COLORS["text_secondary"],
                                icon_size=20,
                                on_click=lambda _: asyncio.create_task(
                                    clipboard.set(state.dialog_code)
                                )
                            )
                        ], spacing=0)
                    ),
                    ft.Container(
                        content=chat_messages,
                        expand=True,
                    ),
                    ft.Container(
                        padding=10,
                        bgcolor=f"{COLORS['card_bg']}ee",
                        content=ft.Row([
                            ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.ATTACH_FILE,
                                    icon_color=COLORS["text_secondary"],
                                    icon_size=22,
                                    on_click=attach_click
                                ),
                                bgcolor=COLORS["input_bg"],
                                border_radius=20,
                            ),
                            ft.Container(
                                content=message_input,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.SEND,
                                    icon_color=COLORS["accent"],
                                    icon_size=22,
                                    on_click=lambda _: asyncio.create_task(send_message())
                                ),
                                bgcolor=COLORS["input_bg"],
                                border_radius=20,
                            )
                        ], spacing=8)
                    )
                ], spacing=0)
            )
        )
        page.update()

        try:
            resp = requests.get(f"{BASE_URL}/dialog/{state.dialog_code}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("messages", []):
                    await add_message(m["sender"], m["text"], m["sender"] == state.my_name)
                page.update()
        except Exception as e:
            print(f"Load history error: {e}")

        asyncio.create_task(connect_ws())

    def is_pinned(code):
        return code in saved_data.get("pinned", [])

    async def show_home():
        page.clean()

        pinned = app_storage.get_list("pinned")[:5]
        recent = app_storage.get_list("recent")[:5]

        name_input = ft.TextField(
            label="Ваше имя",
            width=280,
            value=state.my_name or "",
            text_align="center",
            bgcolor=COLORS["card_bg"],
            border_color="transparent",
            focused_border_color=COLORS["accent"],
            border_radius=16,
            content_padding=15,
        )
        
        dialog_code_input = ft.TextField(
            label="Код диалога",
            width=280,
            text_align="center",
            bgcolor=COLORS["card_bg"],
            border_color="transparent",
            focused_border_color=COLORS["accent"],
            border_radius=16,
            content_padding=15,
        )

        async def save_name_and_continue(e):
            name = name_input.value.strip()
            if not name:
                return
            state.my_name = name
            app_storage.set("name", name)
            await app_storage.save()
            if dialog_code_input.value:
                state.dialog_code = dialog_code_input.value.strip().upper()
                await show_chat()
            else:
                code = str(uuid.uuid4())[:8].upper()
                state.dialog_code = code
                await show_chat()

        async def on_new_chat(e):
            code = str(uuid.uuid4())[:8].upper()
            state.dialog_code = code
            await update_recent_chat(code)
            await show_chat()

        async def on_select_chat(code):
            state.dialog_code = code
            await update_recent_chat(code)
            await show_chat()

        async def on_toggle_pin(code):
            pinned = app_storage.get_list("pinned")
            if code in pinned:
                pinned.remove(code)
            else:
                pinned.insert(0, code)
            app_storage.set_list("pinned", pinned[:5])
            await app_storage.save()
            await show_home()

        def build_chat_item(code, is_pin=False, last_msg=""):
            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"#{code}", weight=ft.FontWeight.W_600, size=15),
                            ft.Text(last_msg, size=11, color=COLORS["text_secondary"], max_lines=1),
                        ], spacing=2),
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.PUSH_PIN if is_pin else ft.Icons.PUSH_PIN_OUTLINED,
                        icon_color=COLORS["pinned"] if is_pin else COLORS["text_secondary"],
                        icon_size=18,
                        on_click=lambda _: on_toggle_pin(code)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_RIGHT,
                        icon_color=COLORS["text_secondary"],
                        on_click=lambda _: on_select_chat(code)
                    ),
                ], spacing=5),
                bgcolor=COLORS["card_bg"],
                padding=15,
                border_radius=12,
                margin=ft.Margin(0, 5, 0, 0),
                on_click=lambda _: on_select_chat(code)
            )

        chats_list = ft.ListView(padding=10, spacing=5)

        if pinned:
            chats_list.controls.append(
                ft.Text("Закрепленные", size=12, color=COLORS["text_secondary"], weight=ft.FontWeight.W_500)
            )
            for code in pinned:
                chats_list.controls.append(build_chat_item(code, True))

        if recent:
            if pinned:
                chats_list.controls.append(ft.Container(height=15))
            chats_list.controls.append(
                ft.Text("Недавние", size=12, color=COLORS["text_secondary"], weight=ft.FontWeight.W_500)
            )
            for code in recent:
                if code not in pinned:
                    chats_list.controls.append(build_chat_item(code, False))

        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["bg"],
                alignment=ft.Alignment(0, 0),
                content=ft.Column([
                    ft.Container(
                        padding=15,
                        bgcolor=f"{COLORS['card_bg']}f2",
                        content=ft.Text("DuoChat", size=20, weight=ft.FontWeight.W_700),
                    ),
                    ft.Container(
                        content=name_input,
                        padding=15,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Введите код для входа", size=12, color=COLORS["text_secondary"]),
                            dialog_code_input,
                            ft.FilledButton(
                                "Войти",
                                width=280,
                                on_click=save_name_and_continue
                            ),
                        ], spacing=10, horizontal_alignment="center"),
                        padding=20,
                        bgcolor=f"{COLORS['card_bg']}f2",
                        border_radius=16,
                    ),
                    ft.Container(height=15),
                    ft.Container(
                        content=chats_list,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.FilledButton(
                            "+ Новый чат",
                            width=280,
                            bgcolor=COLORS["input_bg"],
                            color=COLORS["text"],
                            on_click=on_new_chat
                        ),
                        padding=15,
                    ),
                ], spacing=0, horizontal_alignment="center")
            )
        )
        page.update()

    await show_home()


if __name__ == "__main__":
    ft.app(main)