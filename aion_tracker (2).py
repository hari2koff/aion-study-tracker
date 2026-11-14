# AION Tracker — Dual UI (CustomTkinter + PyQt5)
# Choose which UI to run by setting SELECT_UI to "tk" or "pyqt" below.
# If a selected UI's library is missing, the app will show a helpful message.

SELECT_UI = "tk"  # options: "tk" or "pyqt"

import csv
import os
import time
from datetime import datetime, timedelta

LOG_FILE = "aion_tracker_log.csv"

# --------------------------- Common Utilities ---------------------------

def ensure_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="") as f:
            csv.writer(f).writerow(["Date", "Start Time", "End Time", "Duration (minutes)"])


def append_session(start_ts: float, end_ts: float):
    ensure_log()
    start_dt = datetime.fromtimestamp(start_ts)
    end_dt = datetime.fromtimestamp(end_ts)
    duration_min = round((end_dt - start_dt).total_seconds() / 60, 2)
    with open(LOG_FILE, mode="a", newline="") as f:
        csv.writer(f).writerow([
            start_dt.date(),
            start_dt.strftime("%H:%M:%S"),
            end_dt.strftime("%H:%M:%S"),
            duration_min,
        ])
    return duration_min


def load_daily_totals():
    """Return dict date->total_minutes, preserving chronological order."""
    ensure_log()
    totals = {}
    with open(LOG_FILE, mode="r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = row["Date"]
            totals[d] = totals.get(d, 0.0) + float(row["Duration (minutes)"])
    # sort by date
    return dict(sorted(totals.items(), key=lambda x: x[0]))


def today_stats():
    today = str(datetime.now().date())
    minutes = 0.0
    sessions = 0
    ensure_log()
    with open(LOG_FILE, mode="r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Date"] == today:
                minutes += float(row["Duration (minutes)"])
                sessions += 1
    return round(minutes, 2), sessions


def yesterday_minutes():
    yesterday = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
    totals = load_daily_totals()
    return round(totals.get(yesterday, 0.0), 2)


def current_streak():
    """Consecutive-day streak ending today (days with >0 minutes)."""
    totals = load_daily_totals()
    if not totals:
        return 0
    # Convert keys to dates
    days = [datetime.strptime(d, "%Y-%m-%d").date() for d in totals.keys()]
    mins = list(totals.values())
    day_map = {d: m for d, m in zip(days, mins)}

    streak = 0
    cur = datetime.now().date()
    # Count while current/previous days have >0 minutes
    while day_map.get(cur, 0) > 0:
        streak += 1
        cur = cur - timedelta(days=1)
    return streak


def earned_badges():
    """Return a list of simple achievement strings."""
    badges = []
    totals = load_daily_totals()
    if not totals:
        return badges
    # First 30 / 60 minute day
    if any(m >= 30 for m in totals.values()):
        badges.append("✨ 30+ min day")
    if any(m >= 60 for m in totals.values()):
        badges.append("🏅 60+ min day")
    # 3-day streak
    if current_streak() >= 3:
        badges.append("🔥 3-day streak")
    return badges

# --------------------------- TKINTER (CustomTkinter) ---------------------------

def run_tk_ui():
    try:
        import customtkinter as ctk
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.patches import Rectangle
    except Exception as e:
        print("\nMissing a dependency for the Tk UI. Install with:\n  pip install customtkinter matplotlib\nError:", e)
        return

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    class AIONTrackerTK(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("AION Tracker — TK")
            self.geometry("1000x700")

            # State
            self.is_running = False
            self.start_ts = None
            self.session_goal_min = ctk.StringVar(value="5")  # dropdown goal

            # Top: Timer + controls
            top = ctk.CTkFrame(self, corner_radius=16)
            top.pack(fill="x", padx=16, pady=(16, 8))

            self.timer_label = ctk.CTkLabel(top, text="00:00", font=("Helvetica", 44, "bold"))
            self.timer_label.pack(side="left", padx=16, pady=12)

            controls = ctk.CTkFrame(top)
            controls.pack(side="right", padx=16, pady=12)

            self.start_btn = ctk.CTkButton(controls, text="▶ Start", command=self.start_timer, width=110)
            self.start_btn.grid(row=0, column=0, padx=6, pady=6)

            self.pause_btn = ctk.CTkButton(controls, text="⏸ Pause", command=self.pause_timer, width=110, state="disabled")
            self.pause_btn.grid(row=0, column=1, padx=6, pady=6)

            self.stop_btn = ctk.CTkButton(controls, text="⏹ Stop & Save", command=self.stop_timer, width=110, state="disabled")
            self.stop_btn.grid(row=0, column=2, padx=6, pady=6)

            # Session goal selector
            goal_frame = ctk.CTkFrame(self)
            goal_frame.pack(fill="x", padx=16, pady=(0,8))
            ctk.CTkLabel(goal_frame, text="Session Goal (min):").pack(side="left", padx=12)
            self.goal_menu = ctk.CTkOptionMenu(goal_frame, values=["5","10","25"], variable=self.session_goal_min)
            self.goal_menu.pack(side="left")

            # Middle: Today summary + streak + badges + yesterday stat
            mid = ctk.CTkFrame(self, corner_radius=16)
            mid.pack(fill="x", padx=16, pady=8)

            self.summary_label = ctk.CTkLabel(mid, text="Today: 0.0 min • 0 sessions", font=("Helvetica", 16))
            self.summary_label.pack(side="left", padx=12, pady=12)

            self.yesterday_label = ctk.CTkLabel(mid, text="Yesterday: 0.0 min", font=("Helvetica", 14))
            self.yesterday_label.pack(side="left", padx=12)

            self.streak_label = ctk.CTkLabel(mid, text="Streak: 0 days", font=("Helvetica", 16))
            self.streak_label.pack(side="left", padx=12)

            self.badge_label = ctk.CTkLabel(mid, text="Badges: —", font=("Helvetica", 16))
            self.badge_label.pack(side="left", padx=12)

            # Progress ring (canvas arc)
            ring_frame = ctk.CTkFrame(self, corner_radius=16)
            ring_frame.pack(fill="x", padx=16, pady=8)
            self.canvas = ctk.CTkCanvas(ring_frame, width=160, height=160, bg="#2b2b2b", highlightthickness=0)
            self.canvas.pack(side="left", padx=16, pady=12)
            self.ring_text = ctk.CTkLabel(ring_frame, text="Goal progress", font=("Helvetica", 14))
            self.ring_text.pack(side="left", padx=8)

            # Bottom: Scrollable matplotlib graph
            graph_outer = ctk.CTkFrame(self, corner_radius=16)
            graph_outer.pack(fill="both", expand=True, padx=16, pady=(8,16))

            # Create a Tk canvas with scrollbar to host the matplotlib canvas (for horizontal scrolling)
            self._tk_canvas = ctk.CTkCanvas(graph_outer, height=320, bg="#242424", highlightthickness=0)
            self._tk_canvas.pack(side="top", fill="both", expand=True)

            # Add horizontal scrollbar
            self.h_scroll = ctk.CTkScrollbar(graph_outer, orientation="horizontal", command=self._on_scrollbar)
            # Note: customtkinter scrollbar doesn't support canvas.xview directly, so use tkinter.Scrollbar for reliable binding.
            # We'll create a native tkinter scrollbar and place it in graph_outer.
            import tkinter as tk
            self.native_scroll = tk.Scrollbar(graph_outer, orient=tk.HORIZONTAL, command=self._tk_canvas.xview)
            self.native_scroll.pack(side="bottom", fill="x")
            self._tk_canvas.configure(xscrollcommand=self.native_scroll.set)

            # Frame inside canvas to hold figure widget
            self.inner_frame = tk.Frame(self._tk_canvas, bg="#242424")
            self._inner_window = self._tk_canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

            # Placeholders for matplotlib objects
            self.fig = None
            self.ax = None
            self.canvas_fig = None
            self.bar_patches = []
            self.annotation = None

            # initial refresh
            self.after(250, self.refresh_dashboard)
            self.after(1000, self.tick)

        # Scrollbar callback (unused but kept for API compatibility)
        def _on_scrollbar(self, *args):
            pass

        # ---------------- Timer controls ----------------
        def start_timer(self):
            if not self.is_running:
                self.start_ts = time.time()
                self.is_running = True
                self.start_btn.configure(state="disabled")
                self.pause_btn.configure(state="normal")
                self.stop_btn.configure(state="normal")

        def pause_timer(self):
            if self.is_running and self.start_ts is not None:
                # treat pause as stop-without-save, but keep elapsed in label
                elapsed = int(time.time() - self.start_ts)
                mm, ss = divmod(elapsed, 60)
                self.timer_label.configure(text=f"{mm:02d}:{ss:02d}")
                self.is_running = False
                self.start_btn.configure(state="normal")
                self.pause_btn.configure(state="disabled")
                # keep start_ts so user can resume by pressing Start again
                # resume by adjusting start_ts so total elapsed continues
                self._paused_elapsed = elapsed
                self.start_btn.configure(command=self.resume_timer)

        def resume_timer(self):
            # resume from paused elapsed
            try:
                already = getattr(self, "_paused_elapsed", 0)
            except Exception:
                already = 0
            self.start_ts = time.time() - already
            self.is_running = True
            self.start_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal")
            self.start_btn.configure(command=self.start_timer)

        def stop_timer(self):
            if self.start_ts is not None:
                end_ts = time.time()
                minutes = append_session(self.start_ts, end_ts)
                self.is_running = False
                self.start_ts = None
                self.timer_label.configure(text="00:00")
                self.start_btn.configure(state="normal")
                self.pause_btn.configure(state="disabled")
                self.stop_btn.configure(state="disabled")
                # try to show messagebox if available
                try:
                    ctk.CTkMessagebox(title="Session saved", message=f"You studied for {minutes} minutes")
                except Exception:
                    pass
                self.refresh_dashboard()

        # ---------------- UI updates ----------------
        def tick(self):
            if self.is_running and self.start_ts is not None:
                elapsed = int(time.time() - self.start_ts)
                mm, ss = divmod(elapsed, 60)
                self.timer_label.configure(text=f"{mm:02d}:{ss:02d}")
                self.draw_ring(elapsed)
            self.after(1000, self.tick)

        def draw_ring(self, elapsed_seconds: int = 0):
            self.canvas.delete("all")
            # background circle
            self.canvas.create_oval(10, 10, 150, 150, outline="#3a3a3a", width=14)
            # progress arc based on session goal
            try:
                goal_min = int(self.session_goal_min.get())
            except Exception:
                goal_min = 5
            goal_seconds = max(goal_min * 60, 1)
            pct = max(0.0, min(1.0, elapsed_seconds / goal_seconds))
            extent = pct * 360
            # start at 90 degrees (top), draw clockwise (negative extent in Tk)
            self.canvas.create_arc(10, 10, 150, 150, start=90, extent=-extent, outline="#4caf50", width=14, style="arc")
            # center text
            self.canvas.create_text(80, 80, text=f"{int(pct*100)}%", fill="white", font=("Helvetica", 16, "bold"))

        def refresh_dashboard(self):
            mins, sess = today_stats()
            self.summary_label.configure(text=f"Today: {mins} min • {sess} sessions")
            self.streak_label.configure(text=f"Streak: {current_streak()} days")
            self.yesterday_label.configure(text=f"Yesterday: {yesterday_minutes()} min")
            b = earned_badges()
            self.badge_label.configure(text=f"Badges: {', '.join(b) if b else '—'}")
            self.update_graph()

        def update_graph(self):
            # Clear previous figure widget
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            for child in self.inner_frame.winfo_children():
                child.destroy()

            totals = load_daily_totals()
            if not totals:
                # simple placeholder label
                placeholder = ctk.CTkLabel(self.inner_frame, text="No data yet. Start a session to see your progress!", font=("Helvetica", 14))
                placeholder.pack(pady=20)
                # reset canvas scrollregion
                self._tk_canvas.update_idletasks()
                self._tk_canvas.config(scrollregion=self._tk_canvas.bbox("all"))
                return

            dates = list(totals.keys())
            minutes = list(totals.values())

            # Determine figure width based on number of bars to keep each bar readable
            # width per bar (in inches) - you can tweak this number for more/less spacing
            per_bar_width = 0.7
            fig_width = max(7, per_bar_width * max(len(dates), 7))

            # Create figure with dark background to match theme
            fig, ax = plt.subplots(figsize=(fig_width, 3.5), facecolor="#242424")
            ax.set_facecolor("#ffffff")  # white plotting area for readability
            bars = ax.bar(dates, minutes, picker=True)

            ax.set_title("Daily Minutes")
            ax.set_ylabel("Minutes")
            ax.set_xlabel("Date")
            fig.tight_layout()

            # Save references to enable hover tooltips
            self.fig = fig
            self.ax = ax
            self.bar_patches = bars

            # Create the FigureCanvas and pack into inner_frame
            canvas = FigureCanvasTkAgg(fig, master=self.inner_frame)
            canvas.draw()
            widget = canvas.get_tk_widget()
            widget.pack(fill="both", expand=True)
            self.canvas_fig = canvas

            # Create annotation for hover tooltip
            if self.annotation is None:
                self.annotation = ax.annotate(
                    "",
                    xy=(0,0),
                    xytext=(15,15),
                    textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="w"),
                    arrowprops=dict(arrowstyle="->")
                )
                self.annotation.set_visible(False)

            # Connect hover event
            def on_motion(event):
                # event has x,y in display coords
                vis = False
                if event.inaxes == ax:
                    for rect, d, m in zip(self.bar_patches, dates, minutes):
                        contains, info = rect.contains(event)
                        if contains:
                            # Show annotation
                            self.annotation.xy = (event.xdata, event.ydata)
                            txt = f"Date: {d}\nMinutes: {m}"
                            self.annotation.set_text(txt)
                            self.annotation.get_bbox_patch().set_alpha(0.95)
                            self.annotation.set_visible(True)
                            canvas.draw_idle()
                            vis = True
                            break
                if not vis and self.annotation.get_visible():
                    self.annotation.set_visible(False)
                    canvas.draw_idle()

            # Bind the motion event to the canvas
            canvas.mpl_connect("motion_notify_event", on_motion)

            # Update the scrollregion of the outer Tk canvas so horizontal scrollbar works
            self._tk_canvas.update_idletasks()
            # Get the width of the inner_frame (widget)
            widget.update_idletasks()
            inner_width = widget.winfo_reqwidth()
            inner_height = widget.winfo_reqheight()
            # Set canvas scrollregion to enclosed inner_frame size
            self._tk_canvas.config(scrollregion=(0, 0, inner_width, inner_height))
            # Ensure the inner window uses full height
            self._tk_canvas.itemconfig(self._inner_window, height=inner_height)

            # Bind resize of canvas to adjust scrollregion
            def _on_config(event):
                self._tk_canvas.configure(scrollregion=self._tk_canvas.bbox("all"))
            self._tk_canvas.bind("<Configure>", _on_config)

    app = AIONTrackerTK()
    app.mainloop()

# --------------------------- PYQT5 UI ---------------------------

def run_pyqt_ui():
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    except Exception as e:
        print("\nMissing a dependency for the PyQt UI. Install with:\n  pip install PyQt5 matplotlib\nError:", e)
        return

    class AIONTrackerQt(QtWidgets.QMainWindow):
        tick = QtCore.pyqtSignal()
        def __init__(self):
            super().__init__()
            self.setWindowTitle("AION Tracker — PyQt")
            self.resize(860, 560)
            self.setStyleSheet("QWidget { background-color: #1e1e1e; color: white; } QPushButton { background:#2d2d2d; padding:8px; border-radius:8px; } QPushButton:disabled{background:#444;} ")

            self.is_running = False
            self.start_ts = None

            central = QtWidgets.QWidget()
            self.setCentralWidget(central)
            layout = QtWidgets.QVBoxLayout(central)

            # Timer row
            timer_row = QtWidgets.QHBoxLayout()
            self.timer_lbl = QtWidgets.QLabel("00:00")
            self.timer_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.timer_lbl.setFont(QtGui.QFont("Helvetica", 40, QtGui.QFont.Bold))
            timer_row.addWidget(self.timer_lbl)
            timer_row.addStretch(1)

            self.start_btn = QtWidgets.QPushButton("▶ Start")
            self.start_btn.clicked.connect(self.start_timer)
            timer_row.addWidget(self.start_btn)

            self.pause_btn = QtWidgets.QPushButton("⏸ Pause")
            self.pause_btn.setEnabled(False)
            self.pause_btn.clicked.connect(self.pause_timer)
            timer_row.addWidget(self.pause_btn)

            self.stop_btn = QtWidgets.QPushButton("⏹ Stop & Save")
            self.stop_btn.setEnabled(False)
            self.stop_btn.clicked.connect(self.stop_timer)
            timer_row.addWidget(self.stop_btn)
            layout.addLayout(timer_row)

            # Summary row
            summary_row = QtWidgets.QHBoxLayout()
            self.summary_lbl = QtWidgets.QLabel("Today: 0.0 min • 0 sessions")
            self.streak_lbl = QtWidgets.QLabel("Streak: 0 days")
            self.badge_lbl = QtWidgets.QLabel("Badges: —")
            for w in (self.summary_lbl, self.streak_lbl, self.badge_lbl):
                w.setFont(QtGui.QFont("Helvetica", 14))
            summary_row.addWidget(self.summary_lbl)
            summary_row.addSpacing(20)
            summary_row.addWidget(self.streak_lbl)
            summary_row.addSpacing(20)
            summary_row.addWidget(self.badge_lbl)
            summary_row.addStretch(1)
            layout.addLayout(summary_row)

            # Graph canvas
            self.fig = Figure(figsize=(8,3))
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvas(self.fig)
            layout.addWidget(self.canvas, 1)

            # Timer
            self.qtimer = QtCore.QTimer(self)
            self.qtimer.timeout.connect(self.on_tick)
            self.qtimer.start(1000)

            self.refresh_dashboard()

        def start_timer(self):
            if not self.is_running:
                self.start_ts = time.time()
                self.is_running = True
                self.start_btn.setEnabled(False)
                self.pause_btn.setEnabled(True)
                self.stop_btn.setEnabled(True)

        def pause_timer(self):
            if self.is_running and self.start_ts is not None:
                self.elapsed_paused = int(time.time() - self.start_ts)
                self.is_running = False
                self.start_btn.setEnabled(True)
                self.pause_btn.setEnabled(False)
                self.start_btn.clicked.disconnect()
                self.start_btn.clicked.connect(self.resume_timer)

        def resume_timer(self):
            already = getattr(self, "elapsed_paused", 0)
            self.start_ts = time.time() - already
            self.is_running = True
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.start_btn.clicked.disconnect()
            self.start_btn.clicked.connect(self.start_timer)

        def stop_timer(self):
            if self.start_ts is not None:
                end_ts = time.time()
                minutes = append_session(self.start_ts, end_ts)
                self.is_running = False
                self.start_ts = None
                self.timer_lbl.setText("00:00")
                self.start_btn.setEnabled(True)
                self.pause_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                QtWidgets.QMessageBox.information(self, "Session saved", f"You studied for {minutes} minutes")
                self.refresh_dashboard()

        def on_tick(self):
            if self.is_running and self.start_ts is not None:
                elapsed = int(time.time() - self.start_ts)
                m, s = divmod(elapsed, 60)
                self.timer_lbl.setText(f"{m:02d}:{s:02d}")
            # always keep UI fresh
            # (no ring here; PyQt version focuses on clean text + chart)

        def refresh_dashboard(self):
            mins, sess = today_stats()
            self.summary_lbl.setText(f"Today: {mins} min • {sess} sessions")
            self.streak_lbl.setText(f"Streak: {current_streak()} days")
            b = earned_badges()
            self.badge_lbl.setText(f"Badges: {', '.join(b) if b else '—'}")
            self.update_graph()

        def update_graph(self):
            totals = load_daily_totals()
            self.ax.clear()
            if totals:
                dates = list(totals.keys())
                minutes = list(totals.values())
                self.ax.bar(dates, minutes)
                self.ax.set_title("Daily Minutes")
                self.ax.set_xlabel("Date")
                self.ax.set_ylabel("Minutes")
            else:
                self.ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
            self.fig.tight_layout()
            self.canvas.draw()

    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = AIONTrackerQt()
    win.show()
    sys.exit(app.exec_())

# --------------------------- Entrypoint ---------------------------

if __name__ == "__main__":
    ensure_log()
    if SELECT_UI.lower() == "pyqt":
        run_pyqt_ui()
    else:
        run_tk_ui()
