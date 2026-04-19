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
    "bg": "#08080c",
    "surface": "#12121a",
    "card": "#18181f",
    "my_msg": "#3b0764",
    "my_msg_dark": "#2e1065",
    "their_msg": "#1f1f2a",
    "text": "#e2e8f0",
    "text_secondary": "#64748b",
    "accent": "#7c3aed",
    "accent_light": "#a78bfa",
    "pinned": "#f59e0b",
    "border": "#27272a",
    "input_bg": "#1a1a24",
    "card_bg": "#12121a",
    "time": "#475569",
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
        files = await file_picker.pick_files(allow_multiple=False)
        if files:
            f = files[0]
            filepath = f.path
            filename = f.name
            try:
                with open(filepath, "rb") as file_data:
                    files_req = {"file": (filename, file_data, "image/*")}
                    resp = requests.post(f"{BASE_URL}/upload", files=files_req, timeout=30)
                if resp.status_code == 200:
                    file_path = resp.json().get("file_path", "")
                    payload = json.dumps({
                        "action": "message",
                        "text": f"/image/{file_path}"
                    })
                    if state.ws:
                        await state.ws.send(payload)
                    page.update()
            except Exception as ex:
                print(f"Upload error: {ex}")
                
    async def circle_click(e):
        await page.show_snack_bar(ft.SnackBar(content=ft.Text("Запись кружочков скоро будет доступна!")))
        page.update()

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
        name_color = COLORS["accent_light"] if is_me else COLORS["text_secondary"]
        bg_color = COLORS["my_msg"] if is_me else COLORS["their_msg"]
        
        is_image = text.startswith("/image/")
        
        from datetime import datetime
        msg_time = datetime.now().strftime("%H:%M")
        
        bubble = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(
                                sender[:2].upper(),
                                size=9,
                                weight=ft.FontWeight.W_700,
                                color=COLORS["text"]
                            ),
                            bgcolor=name_color,
                            width=18,
                            height=18,
                            border_radius=9,
                            alignment=ft.Alignment(0, 0)
                        ),
                        ft.Text(
                            sender,
                            size=10,
                            color=name_color,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            msg_time,
                            size=9,
                            color=COLORS["time"],
                            weight=ft.FontWeight.W_400,
                        ),
                    ], spacing=5),
                    margin=ft.Margin(0, 0, 0, 2)
                ),
                ft.Text(
                    text,
                    size=14,
                    color=COLORS["text"],
                ),
            ], spacing=3, tight=True),
            bgcolor=bg_color,
            padding=ft.Padding(12, 8, 12, 8),
            border_radius=20,
            shadow=ft.BoxShadow(
                blur_radius=12,
                color="#00000060",
                offset=ft.Offset(0, 2)
            ),
            width=260,
        )

        if is_me:
            bubble.alignment = ft.Alignment(0.85, 0)
            bubble.margin = ft.Margin(35, 0, 0, 0)
        else:
            bubble.alignment = ft.Alignment(-0.85, 0)
            bubble.margin = ft.Margin(0, 0, 35, 0)
        
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
                        padding=15,
                        bgcolor=COLORS["surface"],
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
                                on_click=lambda _: asyncio.create_task(
                                    clipboard.set(state.dialog_code)
                                )
                            )
                        ], spacing=0)
                    ),
                    ft.Container(
                        content=chat_messages,
                        expand=True,
                        padding=10,
                    ),
                    ft.Container(
                        padding=12,
                        bgcolor=COLORS["surface"],
                        content=ft.Row([
                            ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.ATTACH_FILE,
                                    icon_color=COLORS["text_secondary"],
                                    on_click=lambda _: asyncio.create_task(attach_click(_))
                                ),
                                bgcolor=COLORS["card"],
                                border_radius=25,
                                padding=8,
                            ),
                            ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.MIC,
                                    icon_color=COLORS["text_secondary"],
                                    on_click=lambda _: asyncio.create_task(circle_click(e))
                                ),
                                bgcolor=COLORS["card"],
                                border_radius=25,
                                padding=8,
                            ),
                            ft.Container(
                                content=message_input,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.SEND,
                                    icon_color=COLORS["accent"],
                                    on_click=lambda _: asyncio.create_task(send_message())
                                ),
                                bgcolor=COLORS["accent"],
                                border_radius=25,
                                padding=8,
                            )
                        ], spacing=10)
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
        return code in app_storage.get_list("pinned")

    async def show_home():
        page.clean()

        pinned = app_storage.get_list("pinned")[:5]
        recent = app_storage.get_list("recent")[:5]

        name_input = ft.TextField(
            label="Ваше имя",
            width=280,
            value=state.my_name or "",
            text_align="center",
        )
        
        dialog_code_input = ft.TextField(
            hint_text="Код диалога",
            width=280,
            text_align="center",
        )

        async def save_name_and_continue(e=None):
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

        async def on_new_chat(e=None):
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
                            ft.Text(f"#{code}", weight=ft.FontWeight.W_600, size=14, color=COLORS["text"]),
                            ft.Text(last_msg, size=11, color=COLORS["text_secondary"], max_lines=1),
                        ], spacing=2),
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.IconButton(
                            icon=ft.Icons.PUSH_PIN if is_pin else ft.Icons.PUSH_PIN_OUTLINED,
                            icon_color=COLORS["accent"] if is_pin else COLORS["text_secondary"],
                            icon_size=18,
                            on_click=lambda _: asyncio.create_task(on_toggle_pin(code))
                        ),
                    ),
                    ft.Container(
                        content=ft.IconButton(
                            icon=ft.Icons.CHEVRON_RIGHT,
                            icon_color=COLORS["text_secondary"],
                            on_click=lambda _: asyncio.create_task(on_select_chat(code))
                        ),
                    ),
                ], spacing=5),
                bgcolor=COLORS["card"],
                padding=14,
                border_radius=14,
                margin=ft.Margin(0, 5, 0, 0),
                shadow=ft.BoxShadow(
                    blur_radius=10,
                    color="#00000050",
                    offset=ft.Offset(0, 2)
                ),
            )

        chats_list = ft.ListView(padding=15, spacing=3)

        if pinned:
            chats_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text("Закрепленные", size=12, color=COLORS["text_secondary"], weight=ft.FontWeight.W_500),
                    ], spacing=5),
                    padding=5,
                )
            )
            for code in pinned:
                chats_list.controls.append(build_chat_item(code, True))

        if recent:
            if pinned:
                chats_list.controls.append(ft.Container(height=10))
            chats_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=12, color=COLORS["text_secondary"]),
                        ft.Text("Недавние", size=11, color=COLORS["text_secondary"], weight=ft.FontWeight.W_500),
                    ], spacing=5),
                    padding=5,
                )
            )
            for code in recent:
                if code not in pinned:
                    chats_list.controls.append(build_chat_item(code, False))

        page.add(
            ft.Container(
                expand=True,
                bgcolor=COLORS["bg"],
                padding=20,
                content=ft.Column([
                    ft.Text("DuoChat", size=28, weight=ft.FontWeight.W_700, color=COLORS["text"]),
                    ft.Container(height=30),
                    name_input,
                    ft.Container(height=15),
                    dialog_code_input,
                    ft.Container(height=20),
                    ft.FilledButton(
                        "Войти / Создать",
                        width=280,
                        height=48,
                        on_click=lambda _: asyncio.create_task(save_name_and_continue())
                    ),
                    ft.Container(height=25),
                    ft.Container(
                        content=chats_list,
                        expand=True,
                    ),
                    ft.FilledButton(
                        "+ Новый чат",
                        width=280,
                        on_click=lambda _: asyncio.create_task(on_new_chat())
                    ),
                ], horizontal_alignment="center", spacing=0)
            )
        )
        page.update()

    await show_home()


if __name__ == "__main__":
    ft.app(main)