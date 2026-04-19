import os
import flet as ft
import asyncio
import websockets
import json

async def main(page: ft.Page):
    page.title = "DuoChat"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window.width = 400
    page.window.height = 700

    user_id_field = ft.TextField(label="Ваше имя", width=300)
    chat_messages = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)
    new_message = ft.TextField(hint_text="Сообщение...", expand=True, on_submit=lambda _: asyncio.create_task(send_message_click(None)))
    
    # Храним WebSocket соединение
    state = {"ws": None}

    async def send_message_click(e):
        if state["ws"] and new_message.value:
            await state["ws"].send(new_message.value)
            new_message.value = ""
            page.update()

    async def connect_ws():
        uri = f"ws://localhost:8000/ws/{user_id_field.value}"
        SERVER_HOST = os.getenv("DUOCHAT_SERVER", "localhost")
        uri = f"ws://{SERVER_HOST}:8000/ws/{user_id_field.value}"
        try:
            async with websockets.connect(uri) as websocket:
                state["ws"] = websocket
                while True:
                    msg_raw = await websocket.recv()
                    msg_data = json.loads(msg_raw)
                    
                    is_me = msg_data["sender_id"] == user_id_field.value
                    
                    # Создаем бабл сообщения
                    chat_messages.controls.append(
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Text(msg_data['text'], color=ft.Colors.WHITE),
                                    bgcolor=ft.Colors.BLUE_700 if is_me else ft.Colors.GREY_800,
                                    padding=12,
                                    border_radius=ft.border_radius.only(
                                        top_left=15, top_right=15, 
                                        bottom_left=15 if is_me else 0, 
                                        bottom_right=0 if is_me else 15
                                    ),
                                )
                            ],
                            alignment=ft.MainAxisAlignment.END if is_me else ft.MainAxisAlignment.START
                        )
                    )
                    page.update()
        except Exception as ex:
            print(f"Ошибка связи: {ex}")

    def start_chat(e):
        if not user_id_field.value:
            user_id_field.error_text = "Введите имя!"
            page.update()
            return
            
        name = user_id_field.value
        page.clean()
        
        # Настройка интерфейса чата
        page.add(
            ft.AppBar(
                title=ft.Text(f"DuoChat: {name}"),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            ),
            ft.Container(
                content=chat_messages,
                expand=True,
                padding=20,
            ),
            ft.BottomAppBar(
                content=ft.Row([
                    new_message,
                    ft.IconButton(
                        icon=ft.Icons.SEND_ROUNDED,
                        icon_color=ft.Colors.BLUE_400,
                        on_click=lambda _: asyncio.create_task(send_message_click(None))
                    )
                ])
            )
        )
        page.update()
        # Запускаем WebSocket в фоне
        asyncio.create_task(connect_ws())

    # Экран входа
    page.add(
        ft.Column(
            [
                ft.Text("Добро пожаловать в DuoChat", size=25, weight=ft.FontWeight.BOLD),
                user_id_field,
                ft.FilledButton("Войти в чат", on_click=start_chat, width=300),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
