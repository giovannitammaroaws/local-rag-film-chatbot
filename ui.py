import gradio as gr

from pipeline import respond

EXAMPLES = [
    "What should I watch tonight alone?",
    "Who directed Inception?",
    "Is The Godfather better than Goodfellas?",
    "Plan a Halloween movie night",
    "How many Oscars did The Godfather win?",
]

# Builds and returns the full Gradio Blocks UI without launching it.
def build_ui() -> gr.Blocks:
    with gr.Blocks(title="CineRAG") as demo:

        gr.Markdown("# CineRAG - Film Chatbot\n"
                    "_Ollama - ChromaDB - Phoenix - RAGAS - MOCK VERSION_")

        # Hidden state: accumulated session cost across all queries.
        total_cost_state = gr.State(0.0)

        with gr.Row():

            # Left column: chat area
            with gr.Column(scale=3):
                chatbot  = gr.Chatbot(value=[], height=400, label="Chat")
                with gr.Row():
                    msg_box  = gr.Textbox(
                        placeholder='"What should I watch?" - "Who directed Inception?" - "Godfather vs Goodfellas?"',
                        scale=8, container=False,
                    )
                    send_btn = gr.Button("Send", scale=1, variant="primary")
                gr.Examples(examples=EXAMPLES, inputs=msg_box)

            # Right column: live metrics panel
            with gr.Column(scale=1):
                gr.Markdown("## Live Info")
                label_out = gr.Markdown("_Waiting for a query..._")
                token_out = gr.Markdown("")
                ragas_out = gr.Markdown("")
                cost_out  = gr.Markdown("")
                gr.Markdown("---")
                gr.Markdown("[Phoenix Dashboard](http://localhost:6006)")
                gr.Markdown("`llama3.1:8b` via Ollama")
                gr.Markdown("ChromaDB - 45k TMDB films")
                gr.Markdown("_Pricing: $0.01/1k in · $0.03/1k out_")

        # Bottom: pipeline log
        gr.Markdown("### Pipeline Log")
        log_box = gr.Textbox(
            value="", lines=8, max_lines=8,
            label="", interactive=False,
            placeholder="Pipeline log will appear here...",
        )

        inputs  = [msg_box, chatbot, log_box, total_cost_state]
        outputs = [msg_box, chatbot, label_out, token_out, ragas_out, cost_out, log_box, total_cost_state]

        msg_box.submit(respond, inputs, outputs)
        send_btn.click(respond, inputs, outputs)

    return demo
