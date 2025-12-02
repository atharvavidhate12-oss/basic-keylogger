"""
typing_practice_extended.py
Safe local typing practice + metrics tool.

Features:
- Start/Stop typing sessions (Tkinter)
- Live WPM, accuracy, elapsed time
- Per-character latency (aggregated)
- Export metrics CSV and per-key CSV
- Plot WPM over time and show per-key heatmap
- Local leaderboard (metrics only)
- Optional: minimal raw keystroke logging (OFF by default) - requires explicit opt-in; never enable on other's machines

Ethics: This app stores only anonymized metrics by default. Keystroke content is NOT saved unless you explicitly enable RAW_LOG = True and give consent.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import filedialog
from tkinter import ttk
import time
from datetime import datetime
import json
import csv
import random
import string
from statistics import mean, median
import os
import math

# plotting libs
import matplotlib.pyplot as plt
import numpy as np

# Config
RAW_LOG = False  # <-- DEFAULT: False. Set True ONLY for local debugging and explicit consent.
METRICS_FILENAME = "typing_sessions_metrics.json"
LEADERBOARD_FILE = "leaderboard.json"
CSV_METRICS = "typing_session_metrics.csv"
CSV_KEYS = "per_key_latency.csv"

PROMPTS = [
    "The quick brown fox jumps over the lazy dog.",
    "Practice typing to improve your speed and accuracy.",
    "Typing is a useful skill for programming and writing.",
    "Consistency beats intensity when learning a new skill.",
    "Focus on accuracy first; speed will follow naturally."
]

SAMPLE_TEXT = PROMPTS[0]

# Utility function (pure) — we keep it simple and re-usable
def compute_wpm_accuracy(typed_chars: int, errors: int, elapsed_seconds: float):
    elapsed_seconds = max(elapsed_seconds, 1e-6)
    words = typed_chars / 5.0
    wpm = words / (elapsed_seconds / 60.0)
    accuracy = 100.0 if typed_chars == 0 else max(0.0, ((typed_chars - errors) / typed_chars) * 100.0)
    return round(wpm, 2), round(accuracy, 2)

class TypingPracticeApp:
    def __init__(self, root):
        self.root = root
        root.title("Typing Practice — Extended (Safe)")
        root.geometry("900x540")
        root.resizable(True, True)

        # state
        self.start_time = None
        self.end_time = None
        self.typed_chars = 0
        self.error_count = 0
        self.active = False
        self.keystroke_log = []  # (time_offset, char, keysym) - only used if RAW_LOG True
        self.per_key_latencies = {}  # {char: [latencies...]}
        self.last_keystroke_time = None
        self.session_metrics = None
        self.wpm_samples = []  # (elapsed_s, wpm)
        self.current_prompt = SAMPLE_TEXT

        # UI layout
        top = ttk.Frame(root, padding=8)
        top.pack(fill="both", expand=False)

        ttk.Label(top, text="Prompt (click Load Prompt to pick a random one):", font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.prompt_display = tk.Text(top, height=4, wrap=tk.WORD, font=("Helvetica", 12))
        self.prompt_display.pack(fill="x", padx=2, pady=(2,8))
        self.prompt_display.insert("1.0", self.current_prompt)
        self.prompt_display.configure(state="disabled")

        ctrl_frame = ttk.Frame(top)
        ctrl_frame.pack(fill="x", pady=(0,8))
        ttk.Button(ctrl_frame, text="Load Prompt", command=self.load_prompt).pack(side="left")
        ttk.Button(ctrl_frame, text="Pick Prompt (Random)", command=self.pick_random_prompt).pack(side="left", padx=6)
        ttk.Button(ctrl_frame, text="Settings", command=self.show_settings).pack(side="left", padx=6)

        ttk.Label(top, text="Type here (app must have focus):", font=("Helvetica", 11, "bold")).pack(anchor="w")
        self.input_box = tk.Text(top, height=8, wrap=tk.WORD, font=("Courier", 12))
        self.input_box.pack(fill="both", expand=True, padx=2, pady=(2,8))
        self.input_box.bind("<Key>", self.on_key)

        # control buttons
        btn_frame = ttk.Frame(root, padding=8)
        btn_frame.pack(fill="x", expand=False)
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_session)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_session, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Reset", command=self.reset_session).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Save Metrics JSON", command=self.save_metrics_json).pack(side="right")
        ttk.Button(btn_frame, text="Export CSVs", command=self.export_csv).pack(side="right", padx=6)

        # visualization & utility buttons
        vis_frame = ttk.Frame(root, padding=8)
        vis_frame.pack(fill="x")
        ttk.Button(vis_frame, text="Plot WPM over time", command=self.plot_wpm).pack(side="left")
        ttk.Button(vis_frame, text="Show per-key heatmap", command=self.show_heatmap).pack(side="left", padx=6)
        ttk.Button(vis_frame, text="Save to Leaderboard", command=self.save_to_leaderboard).pack(side="left", padx=6)
        ttk.Button(vis_frame, text="Open Metrics Folder", command=self.open_metrics_folder).pack(side="left", padx=6)

        # metrics area
        metrics_frame = ttk.Frame(root, padding=8)
        metrics_frame.pack(fill="x")
        self.time_label = ttk.Label(metrics_frame, text="Elapsed: 0.00 s")
        self.time_label.pack(side="left")
        self.wpm_label = ttk.Label(metrics_frame, text="WPM: 0.00")
        self.wpm_label.pack(side="left", padx=(12,0))
        self.acc_label = ttk.Label(metrics_frame, text="Accuracy: 100.0%")
        self.acc_label.pack(side="left", padx=(12,0))
        self.errors_label = ttk.Label(metrics_frame, text="Errors: 0")
        self.errors_label.pack(side="left", padx=(12,0))

        # update loop
        self.update_clock()

    # -------------------------
    # Session control & events
    # -------------------------
    def load_prompt(self, prompt_text=None):
        if prompt_text is None:
            prompt_text = self.current_prompt
        self.prompt_display.configure(state="normal")
        self.prompt_display.delete("1.0", tk.END)
        self.prompt_display.insert("1.0", prompt_text)
        self.prompt_display.configure(state="disabled")
        self.current_prompt = prompt_text

    def pick_random_prompt(self):
        p = random.choice(PROMPTS)
        self.load_prompt(p)

    def show_settings(self):
        global RAW_LOG
        ans = messagebox.askyesno("RAW log (debugging)", "RAW_LOG is OFF by default for privacy. Do you want to enable raw keystroke logging for this session? (Only for local debugging.)")
        if ans:
            confirm = messagebox.askokcancel("Confirm RAW logging", "You agreed to enable raw keystroke logging. Keystroke content MAY be recorded for this session. ONLY enable if you OWN this machine and consent. Proceed?")
            if confirm:
                RAW_LOG = True
                messagebox.showinfo("Enabled", "RAW_LOG enabled for the running app instance. This is ephemeral and will revert to default on restart.")
            else:
                messagebox.showinfo("Cancelled", "RAW_LOG remains OFF.")
        else:
            RAW_LOG = False
            messagebox.showinfo("No change", "RAW_LOG remains OFF.")

    def start_session(self):
        self.reset_counters()
        self.active = True
        self.start_time = time.time()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.input_box.focus_set()
        self.input_box.delete("1.0", tk.END)
        self.wpm_samples.clear()
        messagebox.showinfo("Session started", "Typing session started. Metrics will be recorded locally (not raw text unless you explicitly enabled RAW_LOG).")

    def stop_session(self):
        if not self.active:
            return
        self.active = False
        self.end_time = time.time()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.compute_metrics(final=True)
        messagebox.showinfo("Session stopped", "Session ended — metrics computed. Use Save/Export to persist metrics.")

    def reset_session(self):
        if self.active:
            self.active = False
        self.reset_counters()
        self.input_box.delete("1.0", tk.END)
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_labels(0.0, 0.0, 100.0, 0)

    def reset_counters(self):
        self.start_time = None
        self.end_time = None
        self.typed_chars = 0
        self.error_count = 0
        self.keystroke_log = []
        self.per_key_latencies = {}
        self.last_keystroke_time = None
        self.session_metrics = None
        self.wpm_samples = []

    def on_key(self, event):
        # only while active
        if not self.active:
            return

        now = time.time()
        if self.start_time is None:
            self.start_time = now
            self.last_keystroke_time = now

        ts = now - self.start_time
        key = event.keysym
        char = event.char

        # optional raw log (explicit opt-in)
        if RAW_LOG:
            try:
                self.keystroke_log.append((round(ts, 4), char, key))
            except Exception:
                pass

        # latency
        latency = now - (self.last_keystroke_time or now)
        self.last_keystroke_time = now
        if len(char) == 1:
            self.per_key_latencies.setdefault(char, []).append(latency)

        # counting typed characters & simple comparison to prompt
        if key == "BackSpace":
            # adjust typed chars only if there is text in the box
            current_text = self.input_box.get("1.0", "end-1c")
            if len(current_text) > 0:
                self.typed_chars = max(0, self.typed_chars - 1)
        elif len(char) == 1:
            self.typed_chars += 1
            prompt = self.current_prompt
            pos = self.typed_chars - 1
            if pos < len(prompt):
                expected = prompt[pos]
                if char != expected:
                    self.error_count += 1
            else:
                self.error_count += 1

        self.compute_metrics(final=False)

    # -------------------------
    # Metrics computation & UI
    # -------------------------
    def compute_metrics(self, final=False):
        if self.start_time is None:
            elapsed = 0.0
        else:
            elapsed = (self.end_time - self.start_time) if (final and self.end_time) else (time.time() - self.start_time)
        elapsed = max(elapsed, 0.0001)
        chars = self.typed_chars
        wpm, accuracy = compute_wpm_accuracy(chars, self.error_count, elapsed)

        # append live samples (not on final to avoid double-sample)
        if not final:
            self.wpm_samples.append((round(elapsed, 2), round(wpm, 2)))

        self.update_labels(elapsed, wpm, accuracy, self.error_count)

        if final:
            self.session_metrics = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "elapsed_seconds": round(elapsed, 3),
                "typed_chars": chars,
                "errors": self.error_count,
                "wpm": wpm,
                "accuracy_percent": accuracy,
                "prompt": self.current_prompt,
                "raw_log_saved": RAW_LOG and bool(self.keystroke_log)
            }

    def update_labels(self, elapsed, wpm, accuracy, errors):
        self.time_label.configure(text=f"Elapsed: {elapsed:.2f} s")
        self.wpm_label.configure(text=f"WPM: {wpm:.2f}")
        self.acc_label.configure(text=f"Accuracy: {accuracy:.1f}%")
        self.errors_label.configure(text=f"Errors: {errors}")

    def update_clock(self):
        if self.active and self.start_time is not None:
            self.compute_metrics(final=False)
        self.root.after(200, self.update_clock)

    # -------------------------
    # Persistence: JSON / CSV
    # -------------------------
    def save_metrics_json(self):
        if not self.session_metrics:
            messagebox.showwarning("No metrics", "No completed session metrics to save. Run and stop a session first.")
            return
        try:
            try:
                with open(METRICS_FILENAME, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = []
            data.append(self.session_metrics)
            with open(METRICS_FILENAME, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            # optionally save raw log if enabled
            if RAW_LOG and self.keystroke_log:
                rawname = f"raw_keystrokes_{int(time.time())}.json"
                with open(rawname, "w", encoding="utf-8") as rf:
                    json.dump(self.keystroke_log, rf, indent=2)
            messagebox.showinfo("Saved", f"Session saved to {METRICS_FILENAME} (metrics only).")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save metrics: {e}")

    def export_csv(self):
        if not self.session_metrics:
            messagebox.showwarning("No metrics", "Complete a session first.")
            return

        # export metrics CSV
        metrics_header = ["timestamp", "elapsed_seconds", "typed_chars", "errors", "wpm", "accuracy_percent", "prompt"]
        write_header = not os.path.exists(CSV_METRICS)
        try:
            with open(CSV_METRICS, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if write_header:
                    w.writerow(metrics_header)
                row = [self.session_metrics.get(h, "") for h in metrics_header]
                w.writerow(row)
        except Exception as e:
            messagebox.showerror("Error", f"Could not write metrics CSV: {e}")
            return

        # export per-key latency CSV
        try:
            with open(CSV_KEYS, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["char", "count", "avg_latency_s", "median_latency_s"])
                for ch, lat_list in sorted(self.per_key_latencies.items()):
                    if not lat_list:
                        continue
                    w.writerow([ch, len(lat_list), round(mean(lat_list), 4), round(median(lat_list), 4)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not write per-key CSV: {e}")
            return

        messagebox.showinfo("Exported", f"Metrics -> {CSV_METRICS}\nPer-key -> {CSV_KEYS}")

    # -------------------------
    # Visualizations
    # -------------------------
    def plot_wpm(self):
        if not self.wpm_samples:
            messagebox.showwarning("No data", "No WPM samples collected during this session.")
            return
        t = [s for s, _ in self.wpm_samples]
        w = [v for _, v in self.wpm_samples]
        plt.figure()
        plt.plot(t, w)  # do not specify colors per instruction
        plt.xlabel("Elapsed time (s)")
        plt.ylabel("WPM")
        plt.title("WPM over time")
        plt.grid(True)
        plt.show()

    def show_heatmap(self):
        if not self.per_key_latencies:
            messagebox.showwarning("No data", "No per-key latency data collected.")
            return

        # ordered characters: a-z, 0-9, punctuation
        chars = list(string.ascii_lowercase) + list(string.digits) + list(".,;'-")
        size = int(math.ceil(math.sqrt(len(chars))))
        grid = np.full((size, size), np.nan)

        avg_lat = {ch: (sum(v)/len(v) if v else np.nan) for ch, v in self.per_key_latencies.items()}

        for idx, ch in enumerate(chars):
            r = idx // size
            c = idx % size
            grid[r, c] = avg_lat.get(ch, np.nan)

        fig, ax = plt.subplots()
        im = ax.imshow(grid, interpolation='nearest')
        ax.set_title("Average per-character latency (s)")
        # annotate each cell
        for idx, ch in enumerate(chars):
            r = idx // size
            c = idx % size
            val = grid[r, c]
            txt = ch + ("\n" + (f"{val:.3f}" if not np.isnan(val) else "-"))
            ax.text(c, r, txt, ha="center", va="center", fontsize=8)
        plt.show()

    # -------------------------
    # Leaderboard
    # -------------------------
    def save_to_leaderboard(self):
        if not self.session_metrics:
            messagebox.showwarning("No session", "Complete a session first.")
            return
        username = simpledialog.askstring("Name", "Enter your name for the leaderboard (or leave blank):")
        username = username.strip() if username else "Anonymous"
        entry = {
            "user": username,
            "timestamp": self.session_metrics["timestamp"],
            "wpm": self.session_metrics["wpm"],
            "accuracy": self.session_metrics["accuracy_percent"],
            "elapsed": self.session_metrics["elapsed_seconds"]
        }
        try:
            try:
                with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = []
            data.append(entry)
            data = sorted(data, key=lambda e: e["wpm"], reverse=True)[:100]
            with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Saved", "Leaderboard updated.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save leaderboard: {e}")

    def open_metrics_folder(self):
        folder = os.getcwd()
        messagebox.showinfo("Metrics folder", f"Metrics & CSV files are saved in:\n{folder}")

def main():
    root = tk.Tk()
    app = TypingPracticeApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
