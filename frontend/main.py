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


async def main(page: ft.Page):
    page.title = "DuoChat"
    page.theme_mode = "dark"
    page.window_width = 360
    page.window_height = 640
    page.padding = 0

    class State:
        ws = None
        my_name = None
        dialog_code = None
    state = State()

    chat_messages = ft.ListView(expand=True, spacing=8, auto_scroll=True)
    message_input = ft.TextField(hint_text="Сообщение...", expand=True)

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    async def send_message():
        if state.ws and message_input.value:
            try:
                payload = json.dumps({
                    "action": "message",
                    "text": message_input.value
                })
                await state.ws.send(payload)
                message_input.value = ""
                page.update()
            except Exception as e:
                print("Send error:", e)

    async def attach_click(e):
        files = await file_picker.pick_files()
        if files:
            for f in files:
                print(f"Selected: {f.path}")

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
                        
                        chat_messages.controls.append(
                            ft.Container(
                                content=ft.Text(text, size=14, color="white"),
                                bgcolor="#2563eb" if is_me else "#374151",
                                padding=10,
                                border_radius=12,
                                margin=ft.margin.only(
                                    left=50 if is_me else 0,
                                    right=0 if is_me else 50
                                )
                            )
                        )
                        page.update()
            except Exception as e:
                print("WS error:", e)
                await asyncio.sleep(3)

    async def show_chat():
        page.clean()
        message_input.value = ""
        chat_messages.controls.clear()
        
        page.add(
            ft.AppBar(
                title=ft.Text(f"#{state.dialog_code}", size=16),
                bgcolor="#1f2937"
            ),
            ft.Container(content=chat_messages, expand=True, padding=5),
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ATTACH_FILE,
                        icon_size=20,
                        on_click=attach_click
                    ),
                    message_input,
                    ft.IconButton(
                        icon=ft.Icons.SEND,
                        icon_size=20,
                        on_click=lambda _: asyncio.create_task(send_message())
                    )
                ], spacing=5)
            )
        )
        page.update()
        asyncio.create_task(connect_ws())

    async def create_dialog(e):
        if not state.my_name:
            return
        code = str(uuid.uuid4())[:8].upper()
        state.dialog_code = code
        await show_chat()

    async def join_dialog(e):
        if not state.my_name or not dialog_code_input.value:
            return
        state.dialog_code = dialog_code_input.value.upper()
        await show_chat()

    async def show_home():
        page.clean()
        
        name_input = ft.TextField(
            label="Ваше имя",
            width=280,
            text_align="center"
        )
        dialog_code_input = ft.TextField(
            label="Код диалога",
            width=280,
            text_align="center"
        )

        async def on_enter(e):
            if not name_input.value:
                return
            state.my_name = name_input.value.strip()
            if dialog_code_input.value:
                state.dialog_code = dialog_code_input.value.strip().upper()
                await show_chat()
            else:
                code = str(uuid.uuid4())[:8].upper()
                state.dialog_code = code
                await show_chat()

        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("DuoChat", size=32, weight="bold"),
                        ft.Text("Приватный чат для двоих", size=14, color="gray"),
                        ft.Container(height=30),
                        name_input,
                        ft.Text("или введите код собеседника", size=12, color="gray"),
                        dialog_code_input,
                        ft.Container(height=20),
                        ft.FilledButton(
                            "Войти / Создать чат",
                            width=280,
                            on_click=on_enter
                        )
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                ),
                expand=True,
                alignment=ft.Alignment(0, 0)
            )
        )
        page.update()

    await show_home()


if __name__ == "__main__":
    ft.app(main)