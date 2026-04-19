"""darts_gui_app.py

Upgraded Darts GUI application (Tkinter) with:
- 301 / 501 / Killer
- Double-In and Double-Out toggles (Option B)
- Enter 3 darts per turn (D20, T5, 25, BULL, Miss)
- Confirm / Modify entries
- Undo last turn
- Leaderboard (computed from saved games)
- Save games with date/time, players, turn history and comments (JSON)
- Game History viewer

Save this file and run with Python 3.8+ (tkinter included in standard library).
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import datetime
import os
import copy

DATA_FILE = "darts_saved_games.json"

# -------------------------
# Utility functions
# -------------------------
def parse_dart(token: str):
    """Parse a single dart token into a score and whether it was a double.
    Accepts formats: '20', 'D20', 'T20', '25', 'BULL', 'SB' (single bull=25), 'DB' (double bull=50), 'MISS'
    Returns (score:int, is_double:bool)
    Raises ValueError on invalid input."""
    if token is None:
        raise ValueError("Empty dart")
    s = token.strip().upper()
    if s in ["", "MISS"]:
        return 0, False
    if s == "BULL" or s == "SB":
        return 25, False
    if s == "DB":
        return 50, True
    if s.startswith("D") and s[1:].isdigit():
        n = int(s[1:])
        if 1 <= n <= 20:
            return 2 * n, True
        raise ValueError(f"Invalid double target: {n}")
    if s.startswith("T") and s[1:].isdigit():
        n = int(s[1:])
        if 1 <= n <= 20:
            return 3 * n, False
        raise ValueError(f"Invalid treble target: {n}")
    if s.isdigit():
        n = int(s)
        if 1 <= n <= 20:
            return n, False
        if n == 25:
            return 25, False
        raise ValueError(f"Invalid numeric target: {n}")
    raise ValueError(f"Cannot parse dart token: {token}")


def now_timestamp():
    return datetime.datetime.now().isoformat(timespec='seconds')


# -------------------------
# Data models
# -------------------------
class Player:
    def __init__(self, name):
        self.name = name
        self.score = 0
        self.history = []  # list of dicts: {darts: [...], round_score: int, was_bust: bool}
        self.is_active = True

    def to_dict(self):
        return {
            "name": self.name,
            "score": self.score,
            "history": self.history,
            "is_active": self.is_active,
        }

    @staticmethod
    def from_dict(d):
        p = Player(d["name"])
        p.score = d.get("score", 0)
        p.history = d.get("history", [])
        p.is_active = d.get("is_active", True)
        return p


class SavedGame:
    def __init__(self, meta, players, events, comment=""):
        self.meta = meta  # dict with game type, settings, timestamp
        self.players = players  # list of Player.to_dict()
        self.events = events  # list of turn events
        self.comment = comment

    def to_dict(self):
        return {
            "meta": self.meta,
            "players": [p for p in self.players],
            "events": [e for e in self.events],
            "comment": self.comment,
        }

    @staticmethod
    def from_dict(d):
        return SavedGame(d.get("meta", {}), d.get("players", []), d.get("events", []), d.get("comment", ""))


# -------------------------
# Persistence helpers
# -------------------------

def load_saved_games():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            arr = json.load(f)
            return [SavedGame.from_dict(a) for a in arr]
    except Exception:
        return []


def save_saved_games(games):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([g.to_dict() for g in games], f, indent=2)
        return True
    except Exception as e:
        print("Error saving games:", e)
        return False


# -------------------------
# Main Application
# -------------------------
class DartsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Darts Tracker")
        self.geometry("900x600")

        self.saved_games = load_saved_games()

        self._build_ui()

        # runtime game state
        self.players = []  # Player instances
        self.game_type = None
        self.double_in = False
        self.double_out = False
        self.current_index = 0
        self.turn_history = []  # events for current in-progress game
        self.undo_stack = []

    # -------------------------
    # UI Construction
    # -------------------------
    def _build_ui(self):
        # Top menu frame
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        ttk.Button(top, text="New Game", command=self.start_new_game).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Load Saved Game", command=self.show_saved_games).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Leaderboard", command=self.show_leaderboard).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Quit", command=self.destroy).pack(side=tk.RIGHT, padx=4)

        # Main area: left for input/controls, right for scoreboard/history
        main = ttk.Frame(self)
        main.pack(expand=True, fill=tk.BOTH, padx=8, pady=6)

        self.left_panel = ttk.Frame(main)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_panel = ttk.Frame(main, width=320)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y)

        # Left: dynamic content
        self.left_title = ttk.Label(self.left_panel, text="Welcome to Darts Tracker", font=(None, 16, "bold"))
        self.left_title.pack(pady=12)

        self.content_frame = ttk.Frame(self.left_panel)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Right: scoreboard
        sb_title = ttk.Label(self.right_panel, text="Scoreboard", font=(None, 14, "bold"))
        sb_title.pack(pady=6)

        self.scoreboard = tk.Text(self.right_panel, height=30, width=38, state=tk.DISABLED)
        self.scoreboard.pack(padx=6, pady=6)

        # bottom actions
        bottom = ttk.Frame(self)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=6)
        ttk.Button(bottom, text="Save Current Game", command=self.save_current_game).pack(side=tk.RIGHT, padx=6)
        ttk.Button(bottom, text="Undo Last Turn", command=self.undo_last_turn).pack(side=tk.RIGHT, padx=6)

        self.show_welcome()

    def show_welcome(self):
        for w in self.content_frame.winfo_children():
            w.destroy()
        ttk.Label(self.content_frame, text="Create a new game or load from saved games.", font=(None, 12)).pack(pady=20)

    # -------------------------
    # New Game Flow
    # -------------------------
    def start_new_game(self):
        self.reset_runtime()
        popup = tk.Toplevel(self)
        popup.title("New Game Setup")
        popup.grab_set()

        frm = ttk.Frame(popup, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Game Type:").grid(row=0, column=0, sticky=tk.W)
        game_var = tk.StringVar(value="301")
        ttk.Combobox(frm, textvariable=game_var, values=["301", "501", "Killer"], state="readonly").grid(row=0, column=1, sticky=tk.W)

        di_var = tk.BooleanVar(value=False)
        do_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Double-In (must hit double to start scoring)", variable=di_var).grid(row=1, column=0, columnspan=2, sticky=tk.W)
        ttk.Checkbutton(frm, text="Double-Out (must finish on a double)", variable=do_var).grid(row=2, column=0, columnspan=2, sticky=tk.W)

        ttk.Label(frm, text="Player names (one per line, min 1):").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(8,0))
        txt = tk.Text(frm, width=40, height=8)
        txt.grid(row=4, column=0, columnspan=2, pady=4)

        def create():
            names = [ln.strip() for ln in txt.get("1.0", tk.END).splitlines() if ln.strip()]
            if not names:
                messagebox.showerror("Error", "Enter at least one player name.")
                return
            self.game_type = game_var.get()
            self.double_in = di_var.get()
            self.double_out = do_var.get()
            self.players = [Player(n) for n in names]
            # initial scores
            if self.game_type == "301":
                for p in self.players:
                    p.score = 301
            elif self.game_type == "501":
                for p in self.players:
                    p.score = 501
            elif self.game_type == "Killer":
                for p in self.players:
                    p.score = 0
                    p.lives = 3
                    p.target = None
            popup.destroy()
            self.current_index = 0
            self.turn_history = []
            self.undo_stack = []
            self.show_game_screen()

        ttk.Button(frm, text="Create Game", command=create).grid(row=5, column=1, sticky=tk.E)

    def reset_runtime(self):
        self.players = []
        self.game_type = None
        self.double_in = False
        self.double_out = False
        self.current_index = 0
        self.turn_history = []
        self.undo_stack = []

    # -------------------------
    # Game Screen
    # -------------------------
    def show_game_screen(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

        header = ttk.Label(self.content_frame, text=f"{self.game_type} - Turn Tracker", font=(None, 14, "bold"))
        header.pack(pady=6)

        settings = ttk.Label(self.content_frame, text=f"Double-In: {self.double_in} | Double-Out: {self.double_out}")
        settings.pack()

        # current player frame
        cp_frame = ttk.Frame(self.content_frame, padding=8)
        cp_frame.pack(fill=tk.X)

        self.current_label = ttk.Label(cp_frame, text="", font=(None, 12, "bold"))
        self.current_label.pack(side=tk.LEFT)

        ttk.Button(cp_frame, text="Next", command=self.next_player_force).pack(side=tk.RIGHT)

        # dart entry
        entry_frame = ttk.Frame(self.content_frame, padding=8)
        entry_frame.pack(fill=tk.X)

        ttk.Label(entry_frame, text="Enter 3 darts (examples: 20, D20, T5, 25, DB, Bull, Miss)").pack()
        self.dart_vars = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
        row = ttk.Frame(entry_frame)
        row.pack(pady=6)
        for i in range(3):
            ttk.Entry(row, textvariable=self.dart_vars[i], width=12).grid(row=0, column=i, padx=6)

        ttk.Button(entry_frame, text="Calculate & Confirm", command=self.calculate_and_confirm).pack(pady=6)

        # history listbox
        hist_frame = ttk.Frame(self.content_frame, padding=8)
        hist_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(hist_frame, text="Turn History").pack()
        self.history_list = tk.Listbox(hist_frame, height=8)
        self.history_list.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Update displays
        self.refresh_scoreboard()
        self.update_current_player_label()

    def update_current_player_label(self):
        if not self.players:
            self.current_label.config(text="No active game")
            return
        p = self.players[self.current_index]
        self.current_label.config(text=f"{p.name}'s turn — Score: {getattr(p, 'score', '')}")

    def refresh_scoreboard(self):
        self.scoreboard.config(state=tk.NORMAL)
        self.scoreboard.delete("1.0", tk.END)
        if not self.players:
            self.scoreboard.insert(tk.END, "No game in progress.")
        else:
            for idx, p in enumerate(self.players):
                line = f"{idx+1}. {p.name} — "
                if self.game_type in ["301", "501"]:
                    line += f"Score: {p.score}"
                elif self.game_type == "Killer":
                    line += f"Lives: {getattr(p, 'lives', 3)} | Target: {getattr(p, 'target', '')}"
                self.scoreboard.insert(tk.END, line + "")
                # optionally show last round
                if p.history:
                    last = p.history[-1]
                    darts = ",".join(last.get('darts', []))
                    self.scoreboard.insert(tk.END, f"    Last: {darts} → {last.get('round_score')} ({'Bust' if last.get('was_bust') else 'OK'})")
        self.scoreboard.config(state=tk.DISABLED)

        # update history listbox
        self.history_list.delete(0, tk.END)
        for ev in self.turn_history:
            ts = ev.get('ts')
            who = ev.get('player')
            darts = ",".join(ev.get('darts', []))
            res = ev.get('round_score')
            self.history_list.insert(tk.END, f"{ts} | {who} → {darts} = {res}{' (Bust)' if ev.get('was_bust') else ''}")

    # -------------------------
    # Turn calculation & rules
    # -------------------------
    def calculate_and_confirm(self):
        if not self.players:
            return
        p = self.players[self.current_index]
        tokens = [v.get() for v in self.dart_vars]
        try:
            parsed = [parse_dart(t) for t in tokens]
        except ValueError as e:
            messagebox.showerror("Invalid dart", str(e))
            return

        scores = [s for (s, isd) in parsed]
        is_doubles = [isd for (s, isd) in parsed]

        total = sum(scores)
        # Determine busts and double-in/out rules for 301/501
        was_bust = False
        effective_points = total

        if self.game_type in ["301", "501"]:
            # check double-in: if player hasn't scored yet (i.e., still at starting score), require a double
            start_score = 301 if self.game_type == "301" else 501
            has_started = p.score != start_score
            if self.double_in and not has_started:
                # need at least one double among darts to start scoring
                if not any(is_doubles):
                    was_bust = True
                    effective_points = 0
                else:
                    # scoring begins; calculate total normally
                    was_bust = False
            # check bust: if new score < 0 -> bust
            new_score = p.score - effective_points
            if new_score < 0:
                was_bust = True
            elif new_score == 0:
                # if double-out required, ensure last dart that made score 0 was a double
                if self.double_out:
                    # compute per-dart running subtotal to find finishing dart
                    remaining = p.score
                    finished_on_double = False
                    for s, isd in parsed:
                        remaining -= s
                        if remaining == 0:
                            if isd:
                                finished_on_double = True
                            break
                    if not finished_on_double:
                        was_bust = True

        elif self.game_type == "Killer":
            # simplified killer: first dart sets player's target if not set. Hitting opponent's target reduces life.
            was_bust = False

        # show summary and confirm
        summary = f"Apply this turn for {p.name}: {tokens} → Total {total}"
        if was_bust:
            summary += "Result: BUST (no score change)"
        confirmed = messagebox.askyesno("Confirm Turn", summary)
        if not confirmed:
            return

        # push state for undo
        snapshot = {
            'players': [copy.deepcopy(pl.to_dict()) for pl in self.players],
            'current_index': self.current_index,
            'turn_history': copy.deepcopy(self.turn_history),
        }
        self.undo_stack.append(snapshot)

        # apply
        event = {
            'ts': now_timestamp(),
            'player': p.name,
            'darts': tokens,
            'round_score': total,
            'was_bust': was_bust,
        }

        if self.game_type in ["301", "501"]:
            if not was_bust:
                p.score = p.score - total
            p.history.append({
                'darts': tokens,
                'round_score': total,
                'was_bust': was_bust,
            })
            self.turn_history.append(event)
            if p.score == 0 and not was_bust:
                messagebox.showinfo("Winner", f"{p.name} wins the game!")
                # auto-save winner
                self.prompt_save_after_game(winner=p.name)
                self.show_welcome()
                return

        elif self.game_type == "Killer":
            # Simple killer implementation:
            # - If player's target not set, first dart's numeric (1-20 / 25) becomes target
            # - If they hit another player's target exactly with any dart, that player loses a life
            # - If life reaches 0, remove them from active players
            darts_vals = [t.strip().upper() for t in tokens]
            first_token = darts_vals[0]
            try:
                val, isd = parse_dart(first_token)
            except ValueError:
                val = None
            if getattr(p, 'target', None) in [None, 0]:
                # set target if numeric between 1-20 or 25
                if val and (1 <= val <= 20 or val == 25):
                    p.target = val
            # for all darts, check if hit other player's target
            for tok in darts_vals:
                try:
                    v, _ = parse_dart(tok)
                except ValueError:
                    continue
                for other in list(self.players):
                    if other is p:
                        continue
                    if getattr(other, 'target', None) == v:
                        other.lives = getattr(other, 'lives', 3) - 1
                        if other.lives <= 0:
                            # remove
                            messagebox.showinfo("Eliminated", f"{other.name} has been eliminated!")
                            self.players.remove(other)
            p.history.append({
                'darts': tokens,
                'round_score': total,
                'was_bust': False,
            })
            self.turn_history.append(event)
            if len(self.players) == 1:
                messagebox.showinfo("Winner", f"{self.players[0].name} wins the Killer game!")
                self.prompt_save_after_game(winner=self.players[0].name)
                self.show_welcome()
                return

        # advance to next player
        self.current_index = (self.current_index + 1) % len(self.players)
        self.refresh_scoreboard()
        self.update_current_player_label()
        # clear dart entries
        for v in self.dart_vars:
            v.set("")

    def next_player_force(self):
        if not self.players:
            return
        self.current_index = (self.current_index + 1) % len(self.players)
        self.update_current_player_label()

    # -------------------------
    # Undo
    # -------------------------
    def undo_last_turn(self):
        if not self.undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo")
            return
        snap = self.undo_stack.pop()
        self.players = [Player.from_dict(d) for d in snap['players']]
        self.current_index = snap['current_index']
        self.turn_history = snap['turn_history']
        self.refresh_scoreboard()
        self.update_current_player_label()

    # -------------------------
    # Save / Load
    # -------------------------
    def save_current_game(self):
        if not self.players or not self.game_type:
            messagebox.showinfo("No game", "No current game to save.")
            return
        comment = simpledialog.askstring("Save Game", "Optional comment for this saved game:")
        meta = {
            'game_type': self.game_type,
            'double_in': self.double_in,
            'double_out': self.double_out,
            'ts': now_timestamp(),
        }
        players_data = [p.to_dict() for p in self.players]
        events = copy.deepcopy(self.turn_history)
        sg = SavedGame(meta, players_data, events, comment or "")
        self.saved_games.append(sg)
        success = save_saved_games(self.saved_games)
        if success:
            messagebox.showinfo("Saved", "Game saved successfully.")
        else:
            messagebox.showerror("Error", "Saving failed.")

    def prompt_save_after_game(self, winner=None):
        msg = "Game finished. Do you want to save the game?"
        if winner:
            msg = f"{winner} won. {msg}"
        if messagebox.askyesno("Save Game", msg):
            comment = simpledialog.askstring("Comment", "Add an optional comment for this finished game:")
            meta = {
                'game_type': self.game_type,
                'double_in': self.double_in,
                'double_out': self.double_out,
                'ts': now_timestamp(),
                'winner': winner,
            }
            players_data = [p.to_dict() for p in self.players]
            events = copy.deepcopy(self.turn_history)
            sg = SavedGame(meta, players_data, events, comment or "")
            self.saved_games.append(sg)
            save_saved_games(self.saved_games)

    def show_saved_games(self):
        win = tk.Toplevel(self)
        win.title("Saved Games")
        win.geometry("700x400")
        frm = ttk.Frame(win, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)

        lb = tk.Listbox(frm)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for i, g in enumerate(self.saved_games):
            md = g.meta
            ts = md.get('ts', '')
            gt = md.get('game_type', '')
            winner = md.get('winner', '')
            comment = g.comment
            line = f"{i+1}. {gt} | {ts} | Winner: {winner} | {comment[:40]}"
            lb.insert(tk.END, line)

        detail = tk.Text(frm, width=60)
        detail.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        def on_select(evt):
            sel = lb.curselection()
            if not sel:
                return
            idx = sel[0]
            g = self.saved_games[idx]
            detail.delete("1.0", tk.END)
            detail.insert(tk.END, json.dumps(g.to_dict(), indent=2))

        lb.bind('<<ListboxSelect>>', on_select)

        def load_selected():
            sel = lb.curselection()
            if not sel:
                return
            idx = sel[0]
            g = self.saved_games[idx]
            if messagebox.askyesno("Load", "Load this saved game into the current session? (This will replace unsaved current game)"):
                self.load_saved_game(g)
                win.destroy()

        btns = ttk.Frame(win)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Load", command=load_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Export Selected...", command=lambda: self.export_saved_game(lb.curselection())).pack(side=tk.LEFT, padx=6)

    def load_saved_game(self, saved_game: SavedGame):
        self.reset_runtime()
        self.game_type = saved_game.meta.get('game_type')
        self.double_in = saved_game.meta.get('double_in', False)
        self.double_out = saved_game.meta.get('double_out', False)
        self.players = [Player.from_dict(d) for d in saved_game.players]
        self.turn_history = copy.deepcopy(saved_game.events)
        self.current_index = 0
        self.show_game_screen()

    def export_saved_game(self, selection):
        if not selection:
            messagebox.showinfo("Export", "No saved game selected.")
            return
        idx = selection[0]
        g = self.saved_games[idx]
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON files','*.json')])
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(g.to_dict(), f, indent=2)
        messagebox.showinfo("Exported", f"Saved game exported to {path}")

    # -------------------------
    # Leaderboard (simple aggregate of saved winners)
    # -------------------------
    def show_leaderboard(self):
        # Count winners from saved games
        wins = {}
        for g in self.saved_games:
            w = g.meta.get('winner')
            if w:
                wins[w] = wins.get(w, 0) + 1
        items = sorted(wins.items(), key=lambda x: -x[1])
        txt = "Leaderboard (by saved wins)"
        if not items:
            txt += "No wins recorded in saved games."
        else:
            for i, (name, count) in enumerate(items, start=1):
                txt += f"{i}. {name} — {count} wins"

        messagebox.showinfo("Leaderboard", txt)


# -------------------------
# Run app
# -------------------------
if __name__ == '__main__':
    app = DartsApp()
    app.mainloop()
