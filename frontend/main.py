import flet as ft
import asyncio
import websockets
import json

async def main(page: ft.Page):
    page.title = "DuoChat"
    page.theme_mode = ft.ThemeMode.DARK [cite: 6]
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    user_id = ft.TextField(label="Ваше имя", width=200)
    chat_messages = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)
    new_message = ft.TextField(hint_text="Сообщение...", expand=True)
    
    ws = None

    async def on_message(e):
        if ws:
            await ws.send(new_message.value)
            new_message.value = ""
            page.update()

    async def connect_ws():
        nonlocal ws
        uri = f"ws://localhost:8000/ws/{user_id.value}"
        async with websockets.connect(uri) as websocket:
            ws = websocket
            while True:
                msg_raw = await websocket.recv()
                msg_data = json.loads(msg_raw)
                # Логика баблов: свои справа, чужие слева [cite: 6]
                is_me = msg_data["sender_id"] == user_id.value
                chat_messages.controls.append(
                    ft.Container(
                        content=ft.Text(f"{msg_data['sender_id']}: {msg_data['text']}"),
                        alignment=ft.alignment.center_right if is_me else ft.alignment.center_left,
                        bgcolor=ft.colors.BLUE_700 if is_me else ft.colors.GREY_800,
                        padding=10,
                        border_radius=10,
                    )
                )
                page.update()

    def start_chat(e):
        page.clean()
        page.add(
            ft.AppBar(title=ft.Text(f"Чат: {user_id.value}"), bgcolor=ft.colors.SURFACE_VARIANT),
            chat_messages,
            ft.Row([new_message, ft.IconButton(ft.icons.SEND, on_click=lambda _: asyncio.create_task(on_message(None)))]),
        )
        asyncio.create_task(connect_ws())

    page.add(user_id, ft.ElevatedButton("Войти", on_click=start_chat)) [cite: 6]

ft.app(target=main)
