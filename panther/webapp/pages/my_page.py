from nicegui import ui

def content():
    ui.label("My Page").classes("text-h5")
    # ... build UI here
    # For example, you can add a button:
    ui.button("Click me", on_click=lambda: ui.notify("Button clicked"))


