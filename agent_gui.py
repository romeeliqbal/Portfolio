#!/usr/bin/env python3
import datetime as _dt
import json
import os
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk

from sentiment_core import (
    classify_sentiment,
    describe_sentiment,
    format_score,
    get_analyzer,
    normalize_text,
)


AGENT_NAME = "Sentiment Agent"


@dataclass
class ChatTurn:
    role: str  # "user" or "agent" or "system"
    text: str
    label: str | None = None
    score: float | None = None
    timestamp_iso: str | None = None


class SentimentAgentGUI(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=12)
        self.master = master
        self.master.title(f"{AGENT_NAME}")

        self._analyzer = get_analyzer()
        self._history: list[ChatTurn] = []
        self._dark = False

        self._build_layout()
        self._post_system_greeting()

    # UI construction
    def _build_layout(self) -> None:
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        self.grid(sticky="nsew")

        # Header
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(1, weight=1)

        self.avatar = ttk.Label(header, text="🤖", font=("Segoe UI Emoji", 18))
        self.avatar.grid(row=0, column=0, padx=(0, 8))

        self.title_lbl = ttk.Label(header, text=f"{AGENT_NAME}", font=("TkDefaultFont", 12, "bold"))
        self.title_lbl.grid(row=0, column=1, sticky="w")

        self.theme_btn = ttk.Button(header, text="🌗 Theme", command=self._toggle_theme)
        self.theme_btn.grid(row=0, column=2, padx=(8, 0))

        # Transcript
        transcript_frame = ttk.Frame(self)
        transcript_frame.grid(row=1, column=0, sticky="nsew")
        self.rowconfigure(1, weight=1)
        transcript_frame.rowconfigure(0, weight=1)
        transcript_frame.columnconfigure(0, weight=1)

        self.transcript = tk.Text(
            transcript_frame,
            wrap="word",
            height=16,
            state="disabled",
            undo=False,
            padx=8,
            pady=8,
        )
        self.transcript.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(transcript_frame, orient="vertical", command=self.transcript.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.transcript.configure(yscrollcommand=yscroll.set)

        # Define tags for styling
        self.transcript.tag_configure("user", foreground="#0b5394")
        self.transcript.tag_configure("agent", foreground="#274e13")
        self.transcript.tag_configure("system", foreground="#666666")
        self.transcript.tag_configure("strong", font=("TkDefaultFont", 10, "bold"))

        # Input row
        input_row = ttk.Frame(self)
        input_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        input_row.columnconfigure(0, weight=1)

        self.input = tk.Text(input_row, height=4, wrap="word")
        self.input.grid(row=0, column=0, sticky="ew")

        btns = ttk.Frame(input_row)
        btns.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.send_btn = ttk.Button(btns, text="Send", command=self._on_send)
        self.send_btn.grid(row=0, column=0)
        self.clear_btn = ttk.Button(btns, text="Clear", command=self._on_clear)
        self.clear_btn.grid(row=0, column=1, padx=(6, 0))

        # Footer actions
        footer = ttk.Frame(self)
        footer.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        footer.columnconfigure(1, weight=1)
        self.examples = ttk.Frame(footer)
        self.examples.grid(row=0, column=0, sticky="w")
        for t in [
            "I love this product!",
            "I don't like this experience",
            "It was okay, nothing special",
        ]:
            ttk.Button(self.examples, text=t, command=lambda s=t: self._fill_and_focus(s)).grid(
                row=0, column=self.examples.grid_size()[0], padx=(0, 6)
            )

        right_actions = ttk.Frame(footer)
        right_actions.grid(row=0, column=1, sticky="e")
        ttk.Button(right_actions, text="Export", command=self._export_chat).grid(row=0, column=0)

        # Key bindings
        self.master.bind("<Return>", self._on_return)
        self.master.bind("<Control-Return>", self._on_ctrl_return)

    # Helpers
    def _append(self, role: str, text: str, extra_tags: tuple[str, ...] = ()) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{role.title() if role!='agent' else AGENT_NAME}: ", (role, "strong"))
        self.transcript.insert("end", text + "\n\n", (role,) + extra_tags)
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _post_system_greeting(self) -> None:
        self._append(
            "system",
            "Hi! I'm your offline sentiment agent. Type feedback and press Send.",
        )
        self._append(
            "system",
            "I'll classify it as Positive, Negative, or Neutral and show a confidence score.",
        )

    def _toggle_theme(self) -> None:
        self._dark = not self._dark
        try:
            style = ttk.Style()
            if self._dark:
                self.master.configure(bg="#1e1e1e")
                style.configure("TFrame", background="#1e1e1e")
                style.configure("TLabel", background="#1e1e1e", foreground="#e0e0e0")
                style.configure("TButton")
                self.transcript.configure(background="#252526", foreground="#e0e0e0")
                self.input.configure(background="#2d2d30", foreground="#e0e0e0")
            else:
                self.master.configure(bg="")
                style.configure("TFrame", background="")
                style.configure("TLabel", background="", foreground="")
                self.transcript.configure(background="white", foreground="black")
                self.input.configure(background="white", foreground="black")
        except Exception:
            pass

    def _fill_and_focus(self, sample: str) -> None:
        self.input.delete("1.0", tk.END)
        self.input.insert("1.0", sample)
        self.input.focus_set()

    def _timestamp(self) -> str:
        return _dt.datetime.now().isoformat(timespec="seconds")

    # Events
    def _on_return(self, event) -> None:
        # plain Enter submits, Shift+Enter creates newline (Tk default)
        if event.state & 0x0001:  # Shift
            return
        self._on_send()

    def _on_ctrl_return(self, _event) -> None:
        self._on_send()

    def _on_clear(self) -> None:
        self.input.delete("1.0", tk.END)

    def _on_send(self) -> None:
        raw = self.input.get("1.0", tk.END)
        cleaned = normalize_text(raw)
        if cleaned == "":
            self._append("agent", "⚠️ Please enter feedback.")
            return

        self._history.append(ChatTurn(role="user", text=cleaned, timestamp_iso=self._timestamp()))
        self._append("user", cleaned)
        self.input.delete("1.0", tk.END)

        # Analyze and respond
        label, score = classify_sentiment(cleaned, self._analyzer)
        summary = describe_sentiment(label, score)
        response = (
            f"{summary}\n"
            f"Label: {label} | Score: {format_score(score)}\n"
            f"Suggestion: "
            + self._suggest_follow_up(label)
        )

        self._history.append(
            ChatTurn(
                role="agent",
                text=response,
                label=label,
                score=score,
                timestamp_iso=self._timestamp(),
            )
        )
        self._append("agent", response)

    def _suggest_follow_up(self, label: str) -> str:
        if label == "Negative":
            return "Tell me what went wrong and what you expected instead."
        if label == "Positive":
            return "Share what you liked most so we can amplify it."
        return "Add specifics so I can better understand your experience."

    def _export_chat(self) -> None:
        if not self._history:
            messagebox.showinfo("Export", "No conversation yet.")
            return
        default_name = f"sentiment_chat_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".txt"):
                with open(path, "w", encoding="utf-8") as f:
                    for turn in self._history:
                        prefix = (
                            f"{turn.timestamp_iso} {AGENT_NAME}: " if turn.role == "agent" else
                            f"{turn.timestamp_iso} User: " if turn.role == "user" else
                            f"{turn.timestamp_iso} System: "
                        )
                        f.write(prefix + turn.text + "\n\n")
            else:
                payload = [turn.__dict__ for turn in self._history]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Export", f"Saved to {os.path.basename(path)}")
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Export failed", str(exc))


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    app = SentimentAgentGUI(root)
    root.minsize(640, 480)
    root.mainloop()


if __name__ == "__main__":
    main()

