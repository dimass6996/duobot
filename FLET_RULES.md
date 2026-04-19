# Flet Syntax Rules (v0.21+)

## FilePicker

- **NEVER** use `on_result` parameter in `FilePicker()` constructor
- **ALWAYS** add FilePicker to `page.services`, NOT to `page.overlay`
- **USE** async methods: `await file_picker.pick_files()`, `await file_picker.save_file()`, `await file_picker.get_directory_path()`
- Methods return result directly, no callback needed

```python
# WRONG:
file_picker = ft.FilePicker(on_result=upload_file)
page.overlay.append(file_picker)

# CORRECT:
file_picker = ft.FilePicker()
page.services.append(file_picker)

async def handle_click(e):
    files = await file_picker.pick_files()
    if files:
        print(files[0].path)
```

## page.update()

- **ALWAYS** use `await page.update()` after changing page content
- **DO NOT** use sync `page.update()` without await

```python
# WRONG:
page.update()

# CORRECT:
await page.update()
```

## Event Handlers

- **USE** `asyncio.create_task()` for fire-and-forget async calls in event handlers
- **USE** `async def` for event handlers that need await

```python
# WRONG:
ft.Button(on_click=send_message)

# CORRECT:
ft.Button(on_click=lambda _: asyncio.create_task(send_message()))
```

## Order of Function Definitions

- **DEFINE** functions BEFORE using them in callbacks
- **DO NOT** reference variables before they are assigned

```python
# WRONG:
file_picker = ft.FilePicker(on_result=upload_file)  # upload_file not defined yet!

async def upload_file(e):
    ...

# CORRECT:
async def upload_file(e):
    ...

file_picker = ft.FilePicker(on_result=upload_file)
```

## Alignment

- **USE** `ft.MainAxisAlignment` and `ft.CrossAxisAlignment` enums
- **USE** string shortcuts: `"center"`, `"start"`, `"end"`, `"space_between"`
- **FOR Container alignment**: use `ft.Alignment(x, y)` or `"center"` string

```python
# WRONG:
alignment=ft.alignment.center

# CORRECT (Container):
alignment=ft.Alignment(0, 0)  # center
alignment="center"
```

## TextAlign

- **USE** string: `"left"`, `"center"`, `"right"`

```python
# WRONG:
text_align=ft.TextAlign.CENTER

# CORRECT:
text_align="center"
```

## Margin

- **USE** `ft.Margin` class, not `ft.margin.only()`

```python
# WRONG:
margin=ft.margin.only(left=10, right=0)

# CORRECT:
margin=ft.Margin(left=10, right=0, top=0, bottom=0)
```

## Clipboard

- **USE** `page.run_clipboard(text)` to copy text

```python
# WRONG:
page.set_clipboard(text)

# CORRECT:
page.run_clipboard(text)
```

## Icons

- **USE** `ft.Icons.NAME` format

```python
# WRONG:
icon="attach_file"

# CORRECT:
icon=ft.Icons.ATTACH_FILE
icon=ft.Icons.COPY
icon=ft.Icons.SEND
icon=ft.Icons.CONTENT_COPY
icon=ft.Icons.ARROW_BACK
```

## Padding

- **USE** `ft.Padding(left, top, right, bottom)` not `ft.padding.symmetric()`

```python
# WRONG:
padding=ft.padding.symmetric(horizontal=15, vertical=8)

# CORRECT:
padding=ft.Padding(15, 8, 15, 8)
# or simple number for all sides:
padding=10
```

## Border Radius

- **USE** integer for rounded corners

```python
# For modern look use large values:
border_radius=20  # smooth rounded
border_radius=24  # card style
```

## Shadows

- **USE** `ft.BoxShadow` with hex color (include alpha in color)

```python
# WRONG (opacity not available in new Flet):
shadow=ft.BoxShadow(blur_radius=20, color="#000000", opacity=0.3)

# CORRECT (use hex with alpha):
shadow=ft.BoxShadow(blur_radius=20, color="#00000033", offset=ft.Offset(0, 4))
# or
shadow=ft.BoxShadow(blur_radius=8, color="#00000033", offset=ft.Offset(0, 2))

# Alpha values: 00 (0%) to ff (100%) - e.g. #00000033 = ~20% opacity
```

## Colors (dark theme)

```python
COLORS = {
    "bg": "#09090b",
    "card_bg": "#18181b", 
    "my_msg": "#4f46e5",
    "their_msg": "#27272a",
    "text": "#e5e5e5",
    "text_secondary": "#a1a1aa",
    "accent": "#6366f1",
}
```

## Button Styles

- **USE** `ft.ButtonStyle` with `shape`

```python
style=ft.ButtonStyle(
    bgcolor=COLORS["accent"],
    color="white",
    shape=ft.RoundedRectangleBorder(radius=16),
)
```
