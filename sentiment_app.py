#!/usr/bin/env python3
"""
Single-file Sentiment Agent (GUI + optional one-off CLI)

Features:
- Offline sentiment analysis via VADER (Positive/Negative/Neutral)
- Chat-style interface with transcript, sample prompts, and theme toggle
- Confidence score shown as ±0.00; friendly agent-like responses with suggestions
- Export conversation to JSON or TXT
- One-off CLI mode: --text "your feedback"
"""

import argparse
import datetime as _dt
import json
import os
import re
import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk
from typing import Tuple


# Dependency: vaderSentiment (pip install vaderSentiment)
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except Exception as import_error:
    sys.stderr.write("Error: vaderSentiment is not installed. Run: pip install vaderSentiment\n")
    raise


AGENT_NAME = "Sentiment Agent"


def normalize_text(user_text: str | None) -> str:
    if user_text is None:
        return ""
    lowered = user_text.lower()
    collapsed = re.sub(r"\s+", " ", lowered).strip()
    return collapsed


def classify_sentiment(clean_text: str, analyzer: SentimentIntensityAnalyzer) -> Tuple[str, float]:
    scores = analyzer.polarity_scores(clean_text)
    compound = float(scores.get("compound", 0.0))
    if compound >= 0.05:
        label = "Positive"
    elif compound <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"
    return label, compound


def describe_sentiment(label: str, score: float) -> str:
    magnitude = abs(score)
    if magnitude >= 0.75:
        intensity = "very strong"
    elif magnitude >= 0.4:
        intensity = "moderate"
    elif magnitude >= 0.15:
        intensity = "mild"
    else:
        intensity = "very mild"

    if label == "Positive":
        return f"Detected {intensity} positive sentiment."
    if label == "Negative":
        return f"Detected {intensity} negative sentiment."
    return "Detected neutral sentiment."


def format_score(score: float) -> str:
    return f"{score:+.2f}"


@dataclass
class ChatTurn:
    role: str  # "user" | "agent" | "system"
    text: str
    label: str | None = None
    score: float | None = None
    timestamp_iso: str | None = None


class SentimentAgentGUI(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master, padding=12)
        self.master = master
        self.master.title(AGENT_NAME)
        self._analyzer = SentimentIntensityAnalyzer()
        self._history: list[ChatTurn] = []
        self._dark = False
        self._build_layout()
        self._post_system_greeting()

    def _build_layout(self) -> None:
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        self.grid(sticky="nsew")

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="🤖", font=("Segoe UI Emoji", 18)).grid(row=0, column=0, padx=(0, 8))
        ttk.Label(header, text=AGENT_NAME, font=("TkDefaultFont", 12, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Button(header, text="🌗 Theme", command=self._toggle_theme).grid(row=0, column=2)

        transcript_frame = ttk.Frame(self)
        transcript_frame.grid(row=1, column=0, sticky="nsew")
        self.rowconfigure(1, weight=1)
        transcript_frame.rowconfigure(0, weight=1)
        transcript_frame.columnconfigure(0, weight=1)

        self.transcript = tk.Text(transcript_frame, wrap="word", height=18, state="disabled", padx=8, pady=8)
        self.transcript.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(transcript_frame, orient="vertical", command=self.transcript.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.transcript.configure(yscrollcommand=yscroll.set)
        self.transcript.tag_configure("user", foreground="#0b5394")
        self.transcript.tag_configure("agent", foreground="#274e13")
        self.transcript.tag_configure("system", foreground="#666666")
        self.transcript.tag_configure("strong", font=("TkDefaultFont", 10, "bold"))

        input_row = ttk.Frame(self)
        input_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        input_row.columnconfigure(0, weight=1)
        self.input = tk.Text(input_row, height=4, wrap="word")
        self.input.grid(row=0, column=0, sticky="ew")
        btns = ttk.Frame(input_row)
        btns.grid(row=0, column=1, sticky="e", padx=(8, 0))
        ttk.Button(btns, text="Send", command=self._on_send).grid(row=0, column=0)
        ttk.Button(btns, text="Clear", command=self._on_clear).grid(row=0, column=1, padx=(6, 0))

        footer = ttk.Frame(self)
        footer.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        footer.columnconfigure(1, weight=1)
        examples = ttk.Frame(footer)
        examples.grid(row=0, column=0, sticky="w")
        for t in ["I love this product!", "I don't like this experience", "It was okay, nothing special"]:
            ttk.Button(examples, text=t, command=lambda s=t: self._fill_and_focus(s)).grid(
                row=0, column=examples.grid_size()[0], padx=(0, 6)
            )
        right_actions = ttk.Frame(footer)
        right_actions.grid(row=0, column=1, sticky="e")
        ttk.Button(right_actions, text="Export", command=self._export_chat).grid(row=0, column=0)

        self.master.bind("<Return>", self._on_return)
        self.master.bind("<Control-Return>", self._on_ctrl_return)

    def _append(self, role: str, text: str, extra_tags: tuple[str, ...] = ()) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{role.title() if role!='agent' else AGENT_NAME}: ", (role, "strong"))
        self.transcript.insert("end", text + "\n\n", (role,) + extra_tags)
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _post_system_greeting(self) -> None:
        self._append("system", "Hi! I'm your offline sentiment agent. Type feedback and press Send.")
        self._append("system", "I'll classify it and show a confidence score (±1.00).")

    def _toggle_theme(self) -> None:
        self._dark = not self._dark
        try:
            style = ttk.Style()
            if self._dark:
                self.master.configure(bg="#1e1e1e")
                style.configure("TFrame", background="#1e1e1e")
                style.configure("TLabel", background="#1e1e1e", foreground="#e0e0e0")
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

    def _on_return(self, event) -> None:
        if event.state & 0x0001:  # Shift inserts newline
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

        self._append("user", cleaned)
        self.input.delete("1.0", tk.END)

        label, score = classify_sentiment(cleaned, SentimentIntensityAnalyzer())
        summary = describe_sentiment(label, score)
        response = (
            f"{summary}\n"
            f"Label: {label} | Score: {format_score(score)}\n"
            f"Suggestion: {self._suggest_follow_up(label)}"
        )
        self._append("agent", response)

    def _suggest_follow_up(self, label: str) -> str:
        if label == "Negative":
            return "Tell me what went wrong and what you expected instead."
        if label == "Positive":
            return "Share what you liked most so we can amplify it."
        return "Add specifics so I can better understand your experience."

    def _export_chat(self) -> None:
        content = self.transcript.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Export", "No conversation yet.")
            return
        default_name = f"sentiment_chat_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            messagebox.showinfo("Export", f"Saved to {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))


def run_gui() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    app = SentimentAgentGUI(root)
    root.minsize(680, 520)
    root.mainloop()


def run_cli_once(text: str) -> int:
    analyzer = SentimentIntensityAnalyzer()
    cleaned = normalize_text(text)
    if cleaned == "":
        print("⚠️ Please enter feedback.")
        return 1
    label, score = classify_sentiment(cleaned, analyzer)
    print(f"Result: {label} | Score: {format_score(score)}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Single-file Sentiment Agent (GUI + optional one-off CLI)")
    parser.add_argument("--text", default=None, help="Analyze a single piece of text and exit")
    args = parser.parse_args(argv)

    if args.text is not None:
        return run_cli_once(args.text)

    run_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

