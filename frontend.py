"""
CWTS Management System - Pure Python Version (Tkinter desktop app)
Run with: python cwts_app.py
Walang HTML, walang Flask, walang kailangang i-install (Tkinter ay kasama na sa Python).
Optional: pip install qrcode[pil]   (para lang sa QR Code ng activity)

FILE LAYOUT
  1. Data store   -> nagse-save/nagloload sa cwts_data.json
  2. Helpers      -> password hashing, paghahanap, pag-format ng petsa
  3. App class    -> ang window, header/menu, at lahat ng pages (bawat page = isang method)
"""
import hashlib, json, os, shutil, threading, webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:                                   # optional ang QR code
    import qrcode
except ImportError:
    qrcode = None

# ==============================================================================
# 1. DATA STORE
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "cwts_data.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
ADMIN_CODE, MAX_ADMINS = "ADMIN2026", 3


class Store:
    DICTS = ["users", "admins", "hours", "counters"]
    LISTS = ["attendance", "reports", "documents", "activities",
             "inbox", "feedback", "announcements", "evaluations"]

    def __init__(self):
        for name in self.DICTS:
            setattr(self, name, {})
        for name in self.LISTS:
            setattr(self, name, [])
        self.photo_fingerprints = set()          # hash ng mga photo, para mahuli ang duplicate
        self._lock = threading.Lock()

    def next_id(self, kind):
        self.counters[kind] = self.counters.get(kind, 0) + 1
        return self.counters[kind]

    def save(self):
        with self._lock:
            data = {name: getattr(self, name) for name in self.DICTS + self.LISTS}
            data["photo_fingerprints"] = sorted(self.photo_fingerprints)
            with open(DATA_FILE + ".tmp", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(DATA_FILE + ".tmp", DATA_FILE)

    def load(self):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        if not os.path.exists(DATA_FILE):
            return
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        for name in self.DICTS:
            getattr(self, name).update(data.get(name, {}))
        for name in self.LISTS:
            getattr(self, name).extend(data.get(name, []))
        self.photo_fingerprints.update(data.get("photo_fingerprints", []))


db = Store()
db.load()

# ==============================================================================
# 2. HELPERS
# ==============================================================================
def hash_password(password):
    """Gawing 'scrambled' ang password (may random salt)."""
    salt = os.urandom(8).hex()
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()


def check_password(stored, password):
    salt, hashed = stored.split("$")
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex() == hashed


def find(items, **match):
    """Hanapin ang unang dictionary sa list na tugma. Hal: find(db.reports, id=5)"""
    for item in items:
        if all(str(item.get(k)) == str(v) for k, v in match.items()):
            return item
    return None


def person_name(username):
    user = db.users.get(username) or db.admins.get(username)
    return user["name"] if user else username


def activity_title(aid):
    act = find(db.activities, id=aid)
    return act["title"] if act else f"Activity #{aid}"


def fmt(value):
    """'2026-10-05T14:30:00' -> 'Oct 05, 2026 02:30 PM'"""
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value)).strftime("%b %d, %Y %I:%M %p")
    except ValueError:
        return str(value)


def hours_text(h):
    return "%.2f" % h if h is not None else "-"


def open_file(path):
    """Buksan ang file gamit ang default program ng computer."""
    try:
        os.startfile(path)                       # Windows
    except AttributeError:
        webbrowser.open("file://" + path)        # Mac/Linux


def all_students():
    return [u for u in db.users.values() if u["role"] == "student"]


# kulay (galing sa orihinal na website)
BG, BLUE, NAVY, RED, GRAY, BORDER = "#f4f6f9", "#2563eb", "#1b2a47", "#dc2626", "#64748b", "#e2e8f0"
STATUS_COLORS = {"Approved": ("#dcfce7", "#166534"), "Pending": ("#fef9c3", "#854d0e"), "Rejected": ("#fee2e2", "#991b1b")}


# ==============================================================================
# 3. THE APP
# ==============================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CWTS Management System")
        self.geometry("1100x700")
        self.minsize(950, 600)
        self.configure(bg=BG)
        self.username = self.role = None         # sino ang naka-login
        self.admin_portal = False                # nasa admin login/register screen ba?

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#f8fafc")

        self.header = tk.Frame(self)
        self.header.pack(fill="x")
        self.body = tk.Frame(self, bg=BG)
        self.body.pack(fill="both", expand=True, padx=25, pady=15)
        self.go(self.home)

    # ---------- navigation ----------
    @property
    def color(self):
        return NAVY if self.role == "admin" or self.admin_portal else BLUE

    def go(self, page, *args, admin=False):
        """Palitan ang page: burahin ang laman, iguhit ang header, tapos gumawa ng bagong page."""
        self.admin_portal = admin
        for w in self.body.winfo_children():
            w.destroy()
        self.draw_header()
        page(*args)

    def dashboard(self):
        self.go(self.student_dashboard if self.role == "student" else self.staff_dashboard)

    def draw_header(self):
        for w in self.header.winfo_children():
            w.destroy()
        self.header.configure(bg=self.color)
        tk.Button(self.header, text="CWTS  " + ("Admin Portal" if self.color == NAVY else "Management System"),
                  command=lambda: self.go(self.home), bg=self.color, fg="white", bd=0, activebackground=self.color,
                  activeforeground="white", font=("Segoe UI", 11, "bold"), cursor="hand2").pack(side="left", padx=15, pady=10)
        if not self.username:
            return
        menus = {
            "student": [("Dashboard", self.student_dashboard), ("Time In/Out", self.student_attendance),
                        ("My Reports", self.student_reports), ("Submit Report", self.report_form)],
            "instructor": [("Dashboard", self.staff_dashboard), ("Reports", self.staff_reports),
                           ("Attendance", self.staff_attendance), ("Evaluations", self.evaluations),
                           ("Activities", self.staff_activities)],
            "admin": [("Dashboard", self.staff_dashboard), ("Students", self.admin_students),
                      ("Activities", self.staff_activities), ("Reports", self.staff_reports),
                      ("Attendance", self.staff_attendance), ("Analytics", self.admin_analytics)],
        }
        for text, page in menus[self.role] + [("Announcements", self.announcements), ("Feedback", self.feedback)]:
            tk.Button(self.header, text=text, command=lambda p=page: self.go(p), bg=self.color, fg="white", bd=0,
                      activebackground=self.color, activeforeground="white", cursor="hand2").pack(side="left", padx=6)
        tk.Button(self.header, text="Logout", command=self.logout, bg=self.color, fg="white", bd=1, cursor="hand2",
                  relief="solid").pack(side="right", padx=15)
        tk.Label(self.header, text=f"{person_name(self.username)} ({self.role})", bg=self.color, fg="white").pack(side="right")
        unread = len([n for n in db.inbox if n.get("to") == self.username and not n.get("read")])
        tk.Button(self.header, text="\U0001F514" + (f" {unread}" if unread else ""), command=lambda: self.go(self.notifications),
                  bg=self.color, fg="white", bd=0, activebackground=self.color, cursor="hand2").pack(side="right", padx=10)

    def logout(self):
        self.username = self.role = None
        self.go(self.home)

    # ---------- small widget builders ----------
    def title_label(self, text):
        tk.Label(self.body, text=text, bg=BG, font=("Segoe UI", 18, "bold"), fg="#222").pack(anchor="w", pady=(0, 10))

    def card(self, parent=None, **pack):
        frame = tk.Frame(parent or self.body, bg="white", highlightbackground=BORDER, highlightthickness=1, padx=15, pady=12)
        frame.pack(**({"fill": "x", "pady": 6} | pack))
        return frame

    def label(self, parent, text, bold=False, muted=False, size=10, bg="white", **pack):
        lab = tk.Label(parent, text=text, bg=bg, font=("Segoe UI", size, "bold" if bold else "normal"),
                       fg=GRAY if muted else "#333", justify="left", anchor="w", wraplength=950)
        lab.pack(**({"anchor": "w"} | pack))
        return lab

    def button(self, parent, text, command, color=None, **pack):
        b = tk.Button(parent, text=text, command=command, bg=color or self.color, fg="white", bd=0, padx=14, pady=5,
                      activebackground=color or self.color, activeforeground="white", cursor="hand2", font=("Segoe UI", 10))
        opts = {"side": "top", "anchor": "w"} | pack          # default: nakapatong; side="left" = magkatabi
        if opts["side"] == "left":
            opts.setdefault("padx", (0, 8))
        b.pack(**opts)
        return b

    def entry(self, parent, text, value="", show="", state="normal"):
        self.label(parent, text, bold=True, size=9, pady=(8, 0))
        e = tk.Entry(parent, show=show, relief="solid", bd=1, font=("Segoe UI", 10))
        e.insert(0, value)
        e.configure(state=state)
        e.pack(fill="x", ipady=3)
        return e

    def textbox(self, parent, text, value="", height=4):
        self.label(parent, text, bold=True, size=9, pady=(8, 0))
        t = tk.Text(parent, height=height, relief="solid", bd=1, font=("Segoe UI", 10))
        t.insert("1.0", value)
        t.pack(fill="x")
        return t

    def combo(self, parent, text, values, value=""):
        self.label(parent, text, bold=True, size=9, pady=(8, 0))
        c = ttk.Combobox(parent, values=values, state="readonly", font=("Segoe UI", 10))
        c.set(value)
        c.pack(fill="x", ipady=2)
        return c

    def stats(self, items):
        """Mga kahon ng numero sa dashboard. items = [(numero, paliwanag), ...]"""
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x", pady=(0, 8))
        for value, caption in items:
            box = tk.Frame(row, bg="white", highlightbackground=BORDER, highlightthickness=1, padx=10, pady=12)
            box.pack(side="left", fill="x", expand=True, padx=5)
            tk.Label(box, text=str(value), bg="white", fg=self.color, font=("Segoe UI", 20, "bold")).pack()
            tk.Label(box, text=caption, bg="white", fg=GRAY).pack()

    def table(self, parent, columns, rows, on_open=None, empty="No data.", height=8):
        """columns = [(pangalan, lapad)], rows = [(iid, (values...))]. Double-click = on_open(iid)."""
        if not rows:
            self.label(parent, empty, muted=True)
            return None
        ids = [f"c{i}" for i in range(len(columns))]
        tree = ttk.Treeview(parent, columns=ids, show="headings", height=height)
        for cid, (name, width) in zip(ids, columns):
            tree.heading(cid, text=name)
            tree.column(cid, width=width, anchor="w")
        for iid, values in rows:
            tree.insert("", "end", iid=str(iid), values=values)
        if on_open:
            tree.bind("<Double-1>", lambda e: tree.selection() and on_open(tree.selection()[0]))
        tree.pack(fill="both", expand=True)
        return tree

    def pill(self, parent, status):
        bg, fg = STATUS_COLORS.get(status, ("#dbeafe", "#1e40af"))
        return tk.Label(parent, text=f" {status} ", bg=bg, fg=fg, font=("Segoe UI", 9, "bold"))

    # ==========================================================================
    # PUBLIC PAGES: home, login, register
    # ==========================================================================
    def home(self):
        box = self.card(pady=20, ipady=25)
        tk.Label(box, text="CWTS Activity Reporting & Monitoring System", bg="white", font=("Segoe UI", 20, "bold")).pack()
        tk.Label(box, text="Submit community service reports, track attendance, and keep CWTS records organised in one place.",
                 bg="white", fg=GRAY).pack(pady=8)
        row = tk.Frame(box, bg="white")
        row.pack()
        if self.username:
            self.button(row, "Go to My Dashboard", self.dashboard, side="left")
        else:
            self.button(row, "Log In", lambda: self.go(self.login, False), side="left")
            self.button(row, "Register (Student/Instructor)", lambda: self.go(self.register), color=GRAY, side="left")
        info = tk.Frame(self.body, bg=BG)
        info.pack(fill="x")
        for head, text in [("Students", "Time In & Out, activity reports, photo proof, service hour tracking."),
                           ("Instructors", "Verify & approve reports, monitor attendance, evaluate student involvement."),
                           ("Administrators", "Separate administrative portal, student management, analytics dashboard.")]:
            c = tk.Frame(info, bg="white", highlightbackground=BORDER, highlightthickness=1, padx=12, pady=10)
            c.pack(side="left", fill="both", expand=True, padx=5)
            tk.Label(c, text=head, bg="white", font=("Segoe UI", 12, "bold")).pack(anchor="w")
            tk.Label(c, text=text, bg="white", fg=GRAY, wraplength=280, justify="left").pack(anchor="w")
        if not self.username:
            tk.Button(self.body, text="Admin Portal", command=lambda: self.go(self.login, True, admin=True), bg=BG,
                      fg=GRAY, bd=0, cursor="hand2").pack(side="bottom", pady=10)

    def login(self, admin):
        card = self.card(pady=40)
        card.pack_configure(fill="none")
        self.label(card, "Administrator Login" if admin else "Log In", bold=True, size=16)
        user = self.entry(card, "Username")
        pw = self.entry(card, "Password", show="*")

        def submit(event=None):
            accounts = db.admins if admin else db.users
            acct = accounts.get(user.get().strip().lower())
            if acct and check_password(acct["password"], pw.get()):
                self.username, self.role = acct["username"], acct["role"]
                self.dashboard()
            else:
                messagebox.showerror("Login", "Invalid admin credentials." if admin else "Invalid username or password.")

        pw.bind("<Return>", submit)
        self.button(card, "Log In", submit, pady=(12, 0))
        if admin:
            self.label(card, f"No admin account yet? ({MAX_ADMINS - len(db.admins)} slots left)", muted=True, pady=(12, 0))
            self.button(card, "Register Admin", lambda: self.go(self.admin_register, admin=True), color=GRAY, pady=(4, 0))
            self.button(card, "Standard Login", lambda: self.go(self.login, False), color=GRAY, pady=(4, 0))
        else:
            self.button(card, "Create an account", lambda: self.go(self.register), color=GRAY, pady=(12, 0))

    def make_account(self, role, name, email, section, username, password):
        return {"username": username, "name": name.strip(), "email": email.strip(), "section": section.strip(),
                "role": role, "password": hash_password(password)}

    def register(self):
        card = self.card(pady=10)
        card.pack_configure(fill="none")
        self.label(card, "Create an Account", bold=True, size=16)
        role = self.combo(card, "I am a", ["student", "instructor"], "student")
        name, email = self.entry(card, "Full Name"), self.entry(card, "Email")
        section, user = self.entry(card, "Section / Course"), self.entry(card, "Username")
        pw, confirm = self.entry(card, "Password (min 6 characters)", show="*"), self.entry(card, "Confirm Password", show="*")

        def submit():
            username = user.get().strip().lower()
            if not (name.get().strip() and email.get().strip() and username and pw.get()):
                messagebox.showerror("Register", "Please fill in all required fields.")
            elif username in db.users or username in db.admins:
                messagebox.showerror("Register", "Username already exists.")
            elif len(pw.get()) < 6:
                messagebox.showerror("Register", "Password must be at least 6 characters.")
            elif pw.get() != confirm.get():
                messagebox.showerror("Register", "Passwords do not match.")
            else:
                db.users[username] = self.make_account(role.get(), name.get(), email.get(), section.get(), username, pw.get())
                db.save()
                messagebox.showinfo("Register", "Registration successful! Please log in.")
                self.go(self.login, False)

        self.button(card, "Register", submit, pady=(12, 0))
        self.button(card, "Back to Log In", lambda: self.go(self.login, False), color=GRAY, pady=(12, 0))

    def admin_register(self):
        slots = MAX_ADMINS - len(db.admins)
        card = self.card(pady=10)
        card.pack_configure(fill="none")
        self.label(card, "Admin Registration", bold=True, size=16)
        self.label(card, f"Max {MAX_ADMINS} administrator accounts allowed. {slots} slots left.", muted=True)
        if slots > 0:
            name, email, user = self.entry(card, "Full Name"), self.entry(card, "Email"), self.entry(card, "Username")
            pw, confirm = self.entry(card, "Password (min 8 characters)", show="*"), self.entry(card, "Confirm Password", show="*")
            code = self.entry(card, "Admin Registration Code", show="*")

            def submit():
                username = user.get().strip().lower()
                if code.get() != ADMIN_CODE:
                    messagebox.showerror("Admin", "Invalid registration code.")
                elif not (name.get().strip() and email.get().strip() and username):
                    messagebox.showerror("Admin", "Please fill in all required fields.")
                elif username in db.users or username in db.admins:
                    messagebox.showerror("Admin", "Username already exists.")
                elif len(pw.get()) < 8 or pw.get() != confirm.get():
                    messagebox.showerror("Admin", "Passwords must match and be at least 8 characters.")
                else:
                    db.admins[username] = self.make_account("admin", name.get(), email.get(), "", username, pw.get())
                    db.save()
                    messagebox.showinfo("Admin", "Admin registered! Please log in.")
                    self.go(self.login, True, admin=True)

            self.button(card, "Register Admin", submit, pady=(12, 0))
        self.button(card, "Back to Admin Login", lambda: self.go(self.login, True, admin=True), color=GRAY, pady=(12, 0))

    # ==========================================================================
    # STUDENT PAGES
    # ==========================================================================
    def active_session(self, username):
        """Attendance record na naka-time in pero wala pang time out."""
        return next((a for a in db.attendance if a["student"] == username and not a.get("time_out")), None)

    def activity_choices(self):
        return [f"{a['id']} - {a['title']}" for a in db.activities]

    def report_rows(self, reports, with_student=False):
        rows = []
        for r in reports:
            values = (person_name(r["student"]),) if with_student else ()
            rows.append((r["id"], values + (r["title"], activity_title(r["activity_id"]), r["date"], r["status"], fmt(r["created"]))))
        return rows

    def student_dashboard(self):
        u = self.username
        mine = [r for r in db.reports if r["student"] == u]
        active = self.active_session(u)
        self.title_label("Student Dashboard")
        self.stats([("%.2f" % db.hours.get(u, 0.0), "Total Service Hours"), (len(mine), "Reports Submitted"),
                    (fmt(active["time_in"]) if active else "None", "Active Time-In")])

        card = self.card()
        self.label(card, "Active Activity Time In / Time Out", bold=True, size=12)
        if active:
            self.label(card, f"Timed in at: {fmt(active['time_in'])}")
            self.button(card, "Time Out Now", self.time_out, color=RED, pady=(6, 0))
        else:
            choice = self.combo(card, "Select Activity", self.activity_choices())
            self.button(card, "Time In Now", lambda: self.time_in(choice.get()), pady=(8, 0))

        card = self.card(fill="both", expand=True)
        self.label(card, "Recent Activity Reports", bold=True, size=12)
        self.table(card, [("Title", 300), ("Date", 120), ("Area (sq.m)", 100), ("Status", 100)],
                   [(r["id"], (r["title"], r["date"], r["area"], r["status"])) for r in mine[:5]],
                   on_open=lambda rid: self.go(self.report_detail, int(rid)), empty="No reports submitted yet.")
        self.label(card, "Double-click a report to view it.", muted=True, size=8)

    def time_in(self, choice):
        if not choice:
            return messagebox.showerror("Time In", "Please select an activity.")
        if self.active_session(self.username):
            return messagebox.showerror("Time In", "You are already timed in to an activity.")
        db.attendance.append({"id": db.next_id("att"), "student": self.username, "activity_id": choice.split(" - ")[0],
                              "time_in": datetime.now().isoformat(), "time_out": None, "hours": None})
        db.save()
        messagebox.showinfo("Time In", "Timed in successfully!")
        self.go(self.student_dashboard)

    def time_out(self):
        u = self.username
        record = self.active_session(u)
        if record:
            now = datetime.now()
            hours = max(0.0, (now - datetime.fromisoformat(record["time_in"])).total_seconds() / 3600)
            record["time_out"], record["hours"] = now.isoformat(), hours
            db.hours[u] = db.hours.get(u, 0.0) + hours
            db.save()
            messagebox.showinfo("Time Out", f"Timed out. Service hours recorded: {hours:.2f} hrs.")
        self.go(self.student_dashboard)

    def attendance_rows(self, records, with_student=False):
        rows = []
        for r in records:
            values = (person_name(r["student"]),) if with_student else ()
            rows.append((r["id"], values + (activity_title(r["activity_id"]), fmt(r["time_in"]),
                                           fmt(r["time_out"]) if r["time_out"] else "In Progress", hours_text(r["hours"]))))
        return rows

    def student_attendance(self):
        self.title_label("My Attendance Log")
        card = self.card(fill="both", expand=True)
        self.table(card, [("Activity", 300), ("Time In", 200), ("Time Out", 200), ("Hours", 80)],
                   self.attendance_rows([a for a in db.attendance if a["student"] == self.username]),
                   empty="No attendance history found.", height=15)

    def student_reports(self):
        self.title_label("My Activity Reports")
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x", pady=(0, 8))
        self.button(row, "+ Submit New Report", self.report_form, side="left")
        card = self.card(fill="both", expand=True)
        self.table(card, [("Title", 250), ("Activity", 250), ("Date", 100), ("Status", 90), ("Submitted", 180)],
                   self.report_rows([r for r in db.reports if r["student"] == self.username]),
                   on_open=lambda rid: self.go(self.report_detail, int(rid)), empty="No reports submitted.", height=15)
        self.label(card, "Double-click a report to view it.", muted=True, size=8)

    def report_form(self):
        self.title_label("Submit Activity Report")
        card = self.card()
        activity = self.combo(card, "Activity", [f"{a['id']} - {a['title']} (Limit: {a['area_limit']} sq. m)" for a in db.activities])
        title = self.entry(card, "Report Title")
        row = tk.Frame(card, bg="white")
        row.pack(fill="x")
        left, right = tk.Frame(row, bg="white"), tk.Frame(row, bg="white")
        left.pack(side="left", fill="x", expand=True, padx=(0, 8))
        right.pack(side="left", fill="x", expand=True)
        date = self.entry(left, "Activity Date (YYYY-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
        area = self.entry(right, "Area Covered (sq. m)")
        desc = self.textbox(card, "What was done")
        photos = []                                           # mga piniling photo (full path)

        self.label(card, "Photos (required) - duplicate photos will be rejected", bold=True, size=9, pady=(8, 0))
        photo_label = self.label(card, "No photos selected.", muted=True)

        def choose():
            files = filedialog.askopenfilenames(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")])
            if files:
                photos[:] = list(files)
                photo_label.config(text=", ".join(os.path.basename(p) for p in photos))

        self.button(card, "Choose Photos...", choose, color=GRAY, pady=(4, 0))

        def submit():
            try:
                datetime.strptime(date.get(), "%Y-%m-%d")
                area_value = float(area.get())
                assert area_value > 0
            except (ValueError, AssertionError):
                return messagebox.showerror("Report", "Please enter a valid date (YYYY-MM-DD) and an area greater than 0.")
            if not (activity.get() and title.get().strip() and desc.get("1.0", "end").strip() and photos):
                return messagebox.showerror("Report", "Please fill in all fields and choose at least one photo.")
            # fingerprint (MD5 hash) ng bawat photo; kapareho ng dati = duplicate
            prints = []
            for path in photos:
                with open(path, "rb") as f:
                    prints.append(hashlib.md5(f.read()).hexdigest())
            if any(p in db.photo_fingerprints for p in prints):
                return messagebox.showerror("Report", "Duplicate photo detected. Please upload unique images.")
            rid = db.next_id("rep")
            for path, fp in zip(photos, prints):
                db.photo_fingerprints.add(fp)
                stored = f"{rid}_photo_{os.path.basename(path)}".replace(" ", "_")
                shutil.copy(path, os.path.join(UPLOAD_DIR, stored))
                db.documents.append({"report_id": rid, "kind": "photo", "original": os.path.basename(path), "stored": stored})
            db.reports.append({"id": rid, "student": self.username, "activity_id": activity.get().split(" - ")[0],
                               "title": title.get().strip(), "date": date.get(), "area": area_value,
                               "description": desc.get("1.0", "end").strip(), "status": "Pending",
                               "created": datetime.now().isoformat(), "comments": []})
            db.save()
            messagebox.showinfo("Report", "Report submitted successfully!")
            self.go(self.student_reports)

        self.button(card, "Submit Report", submit, pady=(12, 0))

    # ==========================================================================
    # INSTRUCTOR & ADMIN PAGES
    # ==========================================================================
    def staff_dashboard(self):
        pending = [r for r in db.reports if r["status"] == "Pending"]
        self.title_label(("Administrator" if self.role == "admin" else "Instructor") + " Dashboard")
        self.stats([(len(all_students()), "Students"), (len(db.activities), "Activities"),
                    (len(db.reports), "Total Reports"), (len(pending), "Pending Review")])
        card = self.card(fill="both", expand=True)
        self.label(card, "Pending Reports Needing Review", bold=True, size=12)
        self.table(card, [("Student", 200), ("Report Title", 350), ("Submitted", 200)],
                   [(r["id"], (person_name(r["student"]), r["title"], fmt(r["created"]))) for r in pending],
                   on_open=lambda rid: self.go(self.report_detail, int(rid)), empty="No pending reports!")
        self.label(card, "Double-click a report to review it.", muted=True, size=8)

    def staff_reports(self):
        self.title_label("Student Reports Management")
        card = self.card(fill="both", expand=True)
        self.table(card, [("Student", 160), ("Title", 250), ("Activity", 220), ("Date", 90), ("Status", 90), ("Submitted", 160)],
                   self.report_rows(db.reports, with_student=True), on_open=lambda rid: self.go(self.report_detail, int(rid)),
                   empty="No reports found.", height=15)
        self.label(card, "Double-click a report to view/review it.", muted=True, size=8)

    def staff_attendance(self):
        self.title_label("Attendance Log")
        card = self.card(fill="both", expand=True)
        self.table(card, [("Student", 200), ("Activity", 250), ("Time In", 180), ("Time Out", 180), ("Hours", 70)],
                   self.attendance_rows(db.attendance, with_student=True), empty="No attendance logs found.", height=15)

    def report_detail(self, rid):
        rep = find(db.reports, id=rid)
        head = tk.Frame(self.body, bg=BG)
        head.pack(fill="x")
        tk.Label(head, text=rep["title"], bg=BG, font=("Segoe UI", 18, "bold")).pack(side="left")
        self.pill(head, rep["status"]).pack(side="left", padx=10)

        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x", pady=8)
        details = tk.Frame(row, bg="white", highlightbackground=BORDER, highlightthickness=1, padx=15, pady=12)
        details.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.label(details, "Details", bold=True, size=12)
        self.label(details, f"Student: {person_name(rep['student'])}\nActivity: {activity_title(rep['activity_id'])}\n"
                            f"Date: {rep['date']}\nArea: {rep['area']} sq. m")
        self.label(details, rep["description"], pady=(8, 0))
        for c in rep["comments"]:
            self.label(details, f"{person_name(c['by'])} ({c['role']}): {c['text']}", muted=True, pady=(4, 0))

        proof = tk.Frame(row, bg="white", highlightbackground=BORDER, highlightthickness=1, padx=15, pady=12)
        proof.pack(side="left", fill="both", expand=True)
        self.label(proof, "Proof Files", bold=True, size=12)
        files = [d for d in db.documents if d["report_id"] == rid and d["kind"] == "photo"]
        for d in files:
            self.button(proof, f"Open {d['original']}", lambda s=d["stored"]: open_file(os.path.join(UPLOAD_DIR, s)),
                        color=GRAY, side="top", anchor="w", pady=2)
        if not files:
            self.label(proof, "No photos.", muted=True)

        if self.role in ("instructor", "admin"):
            card = self.card()
            self.label(card, "Review & Action", bold=True, size=12)
            comment = self.textbox(card, "Comment / Remarks")
            btns = tk.Frame(card, bg="white")
            btns.pack(anchor="w", pady=(10, 0))
            self.button(btns, "Approve", lambda: self.review(rid, "Approved", comment.get("1.0", "end")), side="left")
            self.button(btns, "Reject", lambda: self.review(rid, "Rejected", comment.get("1.0", "end")), color=RED, side="left")

    def review(self, rid, status, comment):
        rep = find(db.reports, id=rid)
        rep["status"] = status
        now = datetime.now().isoformat()
        if comment.strip():
            rep["comments"].append({"by": self.username, "role": self.role, "text": comment.strip(), "at": now})
        db.inbox.append({"to": rep["student"], "message": f"Your report '{rep['title']}' was {status}.", "read": False, "at": now})
        db.save()
        messagebox.showinfo("Review", f"Report status updated to {status}.")
        self.go(self.report_detail, rid)

    def staff_activities(self):
        self.title_label("Activities Management")
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x", pady=(0, 8))
        card = self.card(fill="both", expand=True)
        tree = self.table(card, [("Title", 220), ("Location", 180), ("Limit (sq.m)", 90), ("Max", 60), ("Goal", 380)],
                          [(a["id"], (a["title"], a["location"], a["area_limit"], a["max_participants"], a["goal"])) for a in db.activities],
                          empty="No activities found.", height=14)

        def selected(action):
            if tree is None or not tree.selection():
                return messagebox.showinfo("Activities", "Please select an activity first.")
            action(int(tree.selection()[0]))

        self.button(row, "+ Add New Activity", lambda: self.go(self.activity_form, None), side="left")
        self.button(row, "Edit Selected", lambda: selected(lambda aid: self.go(self.activity_form, aid)), color=GRAY, side="left")
        self.button(row, "QR Code", lambda: selected(self.show_qr), color=GRAY, side="left")

    def show_qr(self, aid):
        if qrcode is None:
            return messagebox.showerror("QR Code", "QR code library not installed.\nRun: pip install qrcode[pil]")
        path = os.path.join(UPLOAD_DIR, f"qr_{aid}.png")
        qrcode.make(f"CWTS-ACTIVITY-{aid}").save(path)
        win = tk.Toplevel(self)
        win.title(f"QR Code - {activity_title(aid)}")
        img = tk.PhotoImage(file=path)
        lab = tk.Label(win, image=img)
        lab.image = img                      # itago para hindi mawala ang larawan
        lab.pack(padx=20, pady=20)

    def activity_form(self, aid):
        act = find(db.activities, id=aid) if aid else None
        self.title_label(("Edit" if act else "Add") + " Activity")
        card = self.card()
        title = self.entry(card, "Title", act["title"] if act else "")
        goal = self.textbox(card, "Goal / Expected Outcome", act["goal"] if act else "")
        location = self.entry(card, "Location", act["location"] if act else "")
        start = self.entry(card, "Start (YYYY-MM-DD HH:MM)", act["start"].replace("T", " ") if act else "")
        end = self.entry(card, "End (YYYY-MM-DD HH:MM)", act["end"].replace("T", " ") if act else "")
        limit = self.entry(card, "Area Limit (sq. m)", act["area_limit"] if act else "")
        maxp = self.entry(card, "Max Participants", act["max_participants"] if act else "")

        def submit():
            try:
                data = {"title": title.get().strip(), "goal": goal.get("1.0", "end").strip(), "location": location.get().strip(),
                        "start": datetime.strptime(start.get(), "%Y-%m-%d %H:%M").strftime("%Y-%m-%dT%H:%M"),
                        "end": datetime.strptime(end.get(), "%Y-%m-%d %H:%M").strftime("%Y-%m-%dT%H:%M"),
                        "area_limit": float(limit.get()), "max_participants": int(maxp.get())}
                assert data["title"] and data["goal"] and data["location"]
            except (ValueError, AssertionError):
                return messagebox.showerror("Activity", "Please fill in all fields correctly (dates: YYYY-MM-DD HH:MM).")
            if act:
                act.update(data)
            else:
                data.update({"id": db.next_id("act"), "created_by": self.username})
                db.activities.append(data)
            db.save()
            messagebox.showinfo("Activity", "Activity saved!")
            self.go(self.staff_activities)

        self.button(card, "Save Activity", submit, pady=(12, 0))

    def evaluations(self):
        self.title_label("Evaluate Student Involvement")
        card = self.card()
        student = self.combo(card, "Student", [f"{s['username']} - {s['name']}" for s in all_students()])
        rating = self.combo(card, "Rating", ["5 - Excellent", "4 - Very Good", "3 - Good", "2 - Fair", "1 - Poor"], "5 - Excellent")
        remarks = self.entry(card, "Remarks")

        def submit():
            if not student.get() or not remarks.get().strip():
                return messagebox.showerror("Evaluation", "Please choose a student and enter remarks.")
            db.evaluations.append({"student": student.get().split(" - ")[0], "evaluator": self.username,
                                   "rating": int(rating.get()[0]), "remarks": remarks.get().strip(),
                                   "created": datetime.now().isoformat()})
            db.save()
            messagebox.showinfo("Evaluation", "Evaluation saved.")
            self.go(self.evaluations)

        self.button(card, "Save Evaluation", submit, pady=(12, 0))
        card = self.card(fill="both", expand=True)
        self.label(card, "Evaluation History", bold=True, size=12)
        self.table(card, [("Student", 200), ("Rating", 70), ("Remarks", 450), ("Date", 180)],
                   [(i, (person_name(e["student"]), e["rating"], e["remarks"], fmt(e["created"])))
                    for i, e in enumerate(reversed(db.evaluations))], empty="No evaluations yet.")

    # ==========================================================================
    # ADMIN-ONLY PAGES
    # ==========================================================================
    def admin_students(self):
        self.title_label("Student Management")
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x", pady=(0, 8))
        card = self.card(fill="both", expand=True)
        tree = self.table(card, [("Name", 200), ("Username", 130), ("Email", 220), ("Section", 100), ("Hours", 80)],
                          [(s["username"], (s["name"], s["username"], s["email"], s["section"] or "-", "%.2f" % db.hours.get(s["username"], 0)))
                           for s in all_students()], empty="No students registered.", height=14)

        def edit():
            if tree is None or not tree.selection():
                return messagebox.showinfo("Students", "Please select a student first.")
            self.go(self.student_form, tree.selection()[0])

        self.button(row, "+ Add New Student", lambda: self.go(self.student_form, None), side="left")
        self.button(row, "Edit Selected", edit, color=GRAY, side="left")

    def student_form(self, username):
        stu = db.users.get(username) if username else None
        self.title_label(("Edit" if stu else "Add") + " Student")
        card = self.card()
        name, email = self.entry(card, "Full Name", stu["name"] if stu else ""), self.entry(card, "Email", stu["email"] if stu else "")
        section = self.entry(card, "Section", stu["section"] if stu else "")
        user = self.entry(card, "Username", stu["username"] if stu else "", state="disabled" if stu else "normal")
        pw = self.entry(card, "Password (leave blank to keep current)" if stu else "Password", show="*")

        def submit():
            if not (name.get().strip() and email.get().strip()) or (not stu and not (user.get().strip() and pw.get())):
                return messagebox.showerror("Student", "Please fill in all required fields.")
            if stu:
                stu.update({"name": name.get().strip(), "email": email.get().strip(), "section": section.get().strip()})
                if pw.get():
                    stu["password"] = hash_password(pw.get())
            else:
                uname = user.get().strip().lower()
                if uname in db.users or uname in db.admins:
                    return messagebox.showerror("Student", "Student already exists.")
                db.users[uname] = self.make_account("student", name.get(), email.get(), section.get(), uname, pw.get())
            db.save()
            messagebox.showinfo("Student", "Student saved.")
            self.go(self.admin_students)

        self.button(card, "Save", submit, pady=(12, 0))

    def admin_analytics(self):
        n, total = len(all_students()), sum(db.hours.values())
        self.title_label("Data Analytics")
        self.stats([(n, "Total Students"), ("%.2f" % total, "Total Hours"), ("%.2f" % (total / n if n else 0.0), "Avg Hours/Student")])

    # ==========================================================================
    # ANNOUNCEMENTS, FEEDBACK, NOTIFICATIONS
    # ==========================================================================
    def announcements(self):
        self.title_label("Announcements")
        if self.role in ("instructor", "admin"):
            card = self.card()
            title, message = self.entry(card, "Title"), self.textbox(card, "Message", height=3)

            def post():
                if not (title.get().strip() and message.get("1.0", "end").strip()):
                    return messagebox.showerror("Announcement", "Please enter a title and a message.")
                db.announcements.append({"id": db.next_id("anc"), "title": title.get().strip(), "body": message.get("1.0", "end").strip(),
                                         "author": self.username, "author_role": self.role, "created": datetime.now().isoformat()})
                db.save()
                self.go(self.announcements)

            self.button(card, "Post Announcement", post, pady=(10, 0))
        box = tk.Text(self.body, wrap="word", relief="solid", bd=1, font=("Segoe UI", 10), padx=10, pady=8)
        box.tag_configure("h", font=("Segoe UI", 13, "bold"))
        box.tag_configure("m", foreground=GRAY)
        for a in reversed(db.announcements):
            box.insert("end", a["title"] + "\n", "h")
            box.insert("end", a["body"] + "\n")
            box.insert("end", f"Posted by {person_name(a['author'])} on {fmt(a['created'])}\n\n", "m")
        if not db.announcements:
            box.insert("end", "No announcements yet.", "m")
        box.configure(state="disabled")
        box.pack(fill="both", expand=True, pady=8)

    def feedback(self):
        self.title_label("Feedback & Suggestions")
        card = self.card()
        kind = self.combo(card, "Type", ["Feedback", "Suggestion"], "Feedback")
        message = self.textbox(card, "Message", height=3)

        def send():
            if not message.get("1.0", "end").strip():
                return messagebox.showerror("Feedback", "Please type a message.")
            db.feedback.append({"from": self.username, "role": self.role, "kind": kind.get(),
                                "message": message.get("1.0", "end").strip(), "created": datetime.now().isoformat()})
            db.save()
            messagebox.showinfo("Feedback", "Feedback sent!")
            self.go(self.feedback)

        self.button(card, "Send", send, pady=(10, 0))
        # students: sarili lang nilang feedback ang makikita; staff: lahat
        items = [f for f in db.feedback if self.role != "student" or f["from"] == self.username]
        card = self.card(fill="both", expand=True)
        self.label(card, "History", bold=True, size=12)
        self.table(card, [("Date", 180), ("Type", 100), ("Message", 600)],
                   [(i, (fmt(f["created"]), f["kind"], f["message"])) for i, f in enumerate(reversed(items))], empty="No entries.")

    def notifications(self):
        self.title_label("Notifications")
        items = [n for n in db.inbox if n.get("to") == self.username]
        card = self.card(fill="both", expand=True)
        if not items:
            self.label(card, "No notifications.", muted=True)
        for n in reversed(items):
            self.label(card, f"{fmt(n['at'])}:  {n['message']}", pady=3)
            n["read"] = True                         # nabasa na
        db.save()
        self.draw_header()                           # i-refresh ang bilang ng unread sa kampana


if __name__ == "__main__":
    App().mainloop()