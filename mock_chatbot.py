import gradio as gr
from ui import build_ui

# Entry point: builds the UI and starts the local server.
if __name__ == "__main__":
    demo = build_ui()
    demo.launch(
        theme=gr.themes.Soft(),
        css="footer { display: none !important; }",
        ssr_mode=False,
    )
