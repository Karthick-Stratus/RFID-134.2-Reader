import serial, serial.tools.list_ports, threading, time, os, sys, datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def resource_path(relative):
    """Get path for bundled resources (works with PyInstaller EXE)."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)

# ECM Protocol for TI RI-STU-MRD2 (SCBU049)
ECM_HDX = 0x03

class MRD2:
    SOH = 0x01
    def __init__(self, port=None, baud=9600, timeout=0.3):
        self.port, self.baud, self.timeout, self.ser = port, baud, timeout, None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
            return True
        except Exception as e: return str(e)

    def disconnect(self):
        if self.ser and self.ser.is_open: self.ser.close()

    @staticmethod
    def _bcc(data):
        v = 0
        for b in data: v ^= b
        return v

    def _cmd(self, payload):
        if not self.ser or not self.ser.is_open: return None
        bcc = self._bcc(payload)
        self.ser.reset_input_buffer()
        self.ser.write(bytearray([self.SOH] + payload + [bcc]))
        return self.ser.read(64)

    def _parse(self, raw):
        if not raw or len(raw) < 4 or raw[0] != self.SOH: return None
        ln = raw[1]
        if len(raw) < ln + 3: return None
        data = list(raw[2:2+ln])
        if self._bcc([ln] + data) != raw[2+ln]: return None
        return data

    @staticmethod
    def is_valid(status):
        return status != 0x03

    @staticmethod
    def tag_type_str(status):
        t = status & 0x03
        return {0:"RO", 1:"R/W", 2:"MPT", 3:"Other"}.get(t,"?")

    def get_version(self):
        d = self._parse(self._cmd([0x02, 0x83, 0x00]))
        if d and len(d) >= 1: return f"v{d[0]>>4}.{d[0]&0x0F}"
        return None

    def charge_read(self):
        """Double-read for noise rejection. Returns (status, uid_hex) or None."""
        d = self._parse(self._cmd([0x03, 0x80, ECM_HDX, 0x00]))
        if not d or not self.is_valid(d[0]) or len(d) < 9: return None
        uid1 = "".join(f"{b:02X}" for b in reversed(d[1:9]))
        time.sleep(0.08)
        d2 = self._parse(self._cmd([0x03, 0x80, ECM_HDX, 0x00]))
        if not d2 or not self.is_valid(d2[0]) or len(d2) < 9: return None
        uid2 = "".join(f"{b:02X}" for b in reversed(d2[1:9]))
        if uid1 != uid2: return None
        return d[0], uid1

    def read_block(self, blk, retries=3):
        """Read 4-byte block with retries. blk=0..15 (0-indexed)."""
        for attempt in range(retries):
            raw = self._cmd([0x04, 0x80, ECM_HDX, 0x03, blk])
            d = self._parse(raw)
            if d and self.is_valid(d[0]) and len(d) >= 6:
                return d[2:6]
            time.sleep(0.05)  # brief pause before retry
        return None

PAGE_LABELS = [
    "Chip ID Byte 3,2,1,0", "Reserved & Chip ID 6,5,4",
    "Reserved & Chip ID 9,8,7", "Config & CRC MSB,LSB",
    "User Memory","User Memory","User Memory","User Memory",
    "User Memory","User Memory","User Memory","User Memory",
    "User Memory","User Memory",
    "Animal ID Byte 3,2,1,0", "Animal ID Byte 7,6,5,4",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Stratus RFID Reader")
        self.root.geometry("850x850")
        self.root.configure(bg="#ffffff") # Light Background
        self.mrd = MRD2()
        self.loop_chipid = False
        self.loop_full = False
        self.last_blocks = [None]*16
        self.last_uid = ""
        self._build()
        self._refresh_ports()

    # Color Palette
    BG_MAIN = "#ffffff"
    BG_ACCENT = "#f1f5f9"
    PRIMARY = "#0284c7"
    TEXT_MAIN = "#1e293b"
    TEXT_SEC = "#64748b"

    def _build(self):
        S = ttk.Style(); S.theme_use("clam")
        S.configure("TLabelframe", background=self.BG_MAIN, foreground=self.TEXT_SEC)
        S.configure("TLabelframe.Label", background=self.BG_MAIN,
                    foreground=self.PRIMARY, font=("Segoe UI",9,"bold"))
        
        # Professional Button Style
        S.configure("TButton", font=("Segoe UI",9,"bold"), padding=6, background="#f8fafc")
        S.map("TButton",
              background=[('active', '#e2e8f0'), ('disabled', '#f1f5f9')],
              foreground=[('active', self.PRIMARY), ('disabled', '#cbd5e1')])
        
        S.configure("Action.TButton", font=("Segoe UI",9,"bold"), padding=6, foreground="white", background=self.PRIMARY)
        S.map("Action.TButton",
              background=[('active', '#0369a1')],
              foreground=[('active', 'white')])

        S.configure("Treeview", background=self.BG_MAIN, foreground=self.TEXT_MAIN,
                    fieldbackground=self.BG_MAIN, rowheight=22, borderwidth=0)
        S.configure("Treeview.Heading", background=self.BG_ACCENT, foreground=self.PRIMARY,
                    font=("Segoe UI",8,"bold"))
        S.map("Treeview", background=[('selected', '#e0f2fe')], foreground=[('selected', self.PRIMARY)])

        S.configure("green.Horizontal.TProgressbar", troughcolor=self.BG_ACCENT,
                    background="#22c55e")

        # Header with logo
        h = tk.Frame(self.root, bg=self.BG_MAIN, pady=10)
        h.pack(fill="x")
        try:
            logo_path = resource_path("Stratus_Logo.png")
            img = Image.open(logo_path)
            # Preserve aspect ratio
            w, ht = img.size
            new_h = 50
            new_w = int(w * new_h / ht)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img)
            tk.Label(h, image=self.logo_img, bg=self.BG_MAIN).pack(side="left", padx=20)
        except Exception:
            tk.Label(h, text="STRATUS", font=("Segoe UI",18,"bold"),
                     bg=self.BG_MAIN, fg=self.PRIMARY).pack(side="left", padx=20)
        
        tk.Label(h, text="STRATUS LF 134.2 kHz RFID Reader HDX+",
                 font=("Segoe UI",12,"bold"), bg=self.BG_MAIN, fg=self.TEXT_MAIN).pack(side="left", pady=10)

        # Connection
        cb = tk.Frame(self.root, bg=self.BG_ACCENT, pady=8, padx=10)
        cb.pack(fill="x")
        tk.Label(cb,text="Port:",bg=self.BG_ACCENT,fg=self.TEXT_SEC,font=("Segoe UI",9,"bold")
                 ).grid(row=0,column=0)
        self.port_var = tk.StringVar()
        self.port_cb = ttk.Combobox(cb, textvariable=self.port_var, width=12)
        self.port_cb.grid(row=0,column=1,padx=5)
        ttk.Button(cb,text="⟳",width=3,command=self._refresh_ports).grid(row=0,column=2)
        
        tk.Label(cb,text="Baud:",bg=self.BG_ACCENT,fg=self.TEXT_SEC,font=("Segoe UI",9,"bold")
                 ).grid(row=0,column=3,padx=(15,5))
        self.baud_var = tk.StringVar(value="9600")
        ttk.Combobox(cb,textvariable=self.baud_var,width=10,
                     values=["9600","19200","57600","115200"]).grid(row=0,column=4,padx=5)
        
        self.btn_conn = ttk.Button(cb,text="Connect",command=self._toggle_conn,width=12, style="Action.TButton")
        self.btn_conn.grid(row=0,column=5,padx=15)
        
        self.lbl_st = tk.Label(cb,text="● OFFLINE",fg="#ef4444",bg=self.BG_ACCENT,
                               font=("Segoe UI",9,"bold"))
        self.lbl_st.grid(row=0,column=6,padx=5)
        
        self.btn_ver = ttk.Button(cb,text="Version",command=self._get_ver,
                                  state="disabled",width=10)
        self.btn_ver.grid(row=0,column=7,padx=5)

        # UID display
        uf = tk.Frame(self.root, bg=self.BG_MAIN, pady=15)
        uf.pack(fill="x")
        tk.Label(uf,text="TRANSPONDER CHIP UID",font=("Segoe UI",8,"bold"),
                 bg=self.BG_MAIN,fg=self.TEXT_SEC).pack()
        self.lbl_uid = tk.Label(uf,text="—  —  —  —  —  —  —  —",
                                font=("Consolas",26,"bold"),bg=self.BG_MAIN,fg=self.PRIMARY)
        self.lbl_uid.pack(pady=5)
        
        info = tk.Frame(uf, bg=self.BG_MAIN)
        info.pack()
        self.lbl_type = tk.Label(info,text="Type: —",font=("Segoe UI",10,"bold"),
                                 bg=self.BG_MAIN,fg=self.TEXT_MAIN)
        self.lbl_type.pack(side="left",padx=20)
        self.lbl_aid = tk.Label(info,text="Animal ID: —",font=("Segoe UI",10,"bold"),
                                bg=self.BG_MAIN,fg=self.TEXT_MAIN)
        self.lbl_aid.pack(side="left",padx=20)

        # Controls
        c1 = tk.Frame(self.root, bg=self.BG_MAIN, pady=10)
        c1.pack(fill="x", padx=20)

        self.chipid_var = tk.BooleanVar(False)
        self.btn_chipid = ttk.Checkbutton(c1, text="🔑 Read Chip ID (Loop)",
                                          variable=self.chipid_var,
                                          command=self._toggle_chipid, state="disabled")
        self.btn_chipid.pack(side="left", padx=10)

        self.full_var = tk.BooleanVar(False)
        self.btn_fullloop = ttk.Checkbutton(c1, text="📄 Full Read (Loop)",
                                            variable=self.full_var,
                                            command=self._toggle_full, state="disabled")
        self.btn_fullloop.pack(side="left", padx=10)

        ttk.Button(c1,text="🗑 Clear Data",command=self._clear,width=12).pack(side="right",padx=5)
        ttk.Button(c1,text="💾 Export TXT",command=self._export_txt,width=12).pack(side="right",padx=5)

        # Progress
        pf = tk.Frame(self.root, bg=self.BG_ACCENT, pady=8, padx=15)
        pf.pack(fill="x", padx=20, pady=5)
        row1 = tk.Frame(pf, bg=self.BG_ACCENT)
        row1.pack(fill="x")
        self.lbl_progress = tk.Label(row1,text="IDLE",
                                     font=("Segoe UI",9,"bold"),bg=self.BG_ACCENT,fg=self.TEXT_SEC)
        self.lbl_progress.pack(side="left")
        self.lbl_timer = tk.Label(row1,text="⏱ 0.000s",
                                  font=("Segoe UI",10,"bold"),bg=self.BG_ACCENT,fg="#f59e0b")
        self.lbl_timer.pack(side="right")
        self.lbl_bits = tk.Label(row1,text="Bits: 0/512",
                                 font=("Segoe UI",9,"bold"),bg=self.BG_ACCENT,fg="#10b981")
        self.lbl_bits.pack(side="right",padx=20)
        self.lbl_reads = tk.Label(row1,text="Reads: 0",
                                  font=("Segoe UI",9,"bold"),bg=self.BG_ACCENT,fg="#8b5cf6")
        self.lbl_reads.pack(side="right",padx=20)
        self.pbar = ttk.Progressbar(pf, length=800, mode="determinate",
                                    style="green.Horizontal.TProgressbar")
        self.pbar.pack(fill="x", pady=(8,0))

        # Block table
        tf = ttk.LabelFrame(self.root, text=" TAG MEMORY MAP ")
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        cols = ("pg","desc","b3","b2","b1","b0","st")
        self.tree = ttk.Treeview(tf,columns=cols,show="headings",height=16)
        for c,w,t in [("pg",50,"PAGE"),("desc",300,"DESCRIPTION"),
                      ("b3",60,"BYTE 3"),("b2",60,"BYTE 2"),
                      ("b1",60,"BYTE 1"),("b0",60,"BYTE 0"),("st",80,"STATUS")]:
            self.tree.heading(c,text=t)
            self.tree.column(c,width=w,anchor="center" if c!="desc" else "w")
        
        self.tree.tag_configure("locked", background="#f3e8ff", foreground="#7e22ce")
        self.tree.tag_configure("ok", background="#ecfdf5", foreground="#047857")
        self.tree.tag_configure("empty", background=self.BG_MAIN, foreground="#94a3b8")
        
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        for i,l in enumerate(PAGE_LABELS):
            self.tree.insert("","end",iid=str(i),
                             values=(i,l,"--","--","--","--","—"),tags=("empty",))

        # Log
        lf = ttk.LabelFrame(self.root, text=" SYSTEM LOG ")
        lf.pack(fill="x", padx=20, pady=(5,15))
        lc = tk.Frame(lf, bg=self.BG_MAIN)
        lc.pack(fill="x",padx=5,pady=(2,0))
        ttk.Button(lc,text="Clear Log",command=self._clear_log,width=12).pack(side="right")
        self.log = scrolledtext.ScrolledText(lf,height=5,font=("Consolas",9),
                    bg="#ffffff",fg=self.TEXT_MAIN,insertbackground="black",state="disabled", borderwidth=1, relief="solid")
        self.log.pack(fill="x",padx=5,pady=5)

    # ── Helpers ──────────────────────────────────────
    def _log(self, m):
        self.log.config(state="normal")
        self.log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {m}\n")
        self.log.see(tk.END); self.log.config(state="disabled")

    def _controls(self, en):
        s = "normal" if en else "disabled"
        for w in [self.btn_chipid,self.btn_fullloop,self.btn_ver]: w.config(state=s)

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if "COM17" in ports: self.port_var.set("COM17")
        elif ports: self.port_var.set(ports[0])

    def _clear_table(self):
        for i in range(16):
            self.tree.item(str(i),values=(i,PAGE_LABELS[i],"--","--","--","--","—"),
                           tags=("empty",))
        self.last_blocks = [None]*16

    def _clear(self):
        self.lbl_uid.config(text="—  —  —  —  —  —  —  —", fg=self.PRIMARY)
        self.lbl_aid.config(text="Animal ID: —")
        self.lbl_type.config(text="Type: —")
        self.lbl_progress.config(text="IDLE", fg=self.TEXT_SEC)
        self.lbl_timer.config(text="⏱ 0.000s")
        self.lbl_bits.config(text="Bits: 0/512")
        self.lbl_reads.config(text="Reads: 0")
        self.pbar["value"] = 0
        self._clear_table()

    def _clear_log(self):
        self.log.config(state="normal"); self.log.delete("1.0","end")
        self.log.config(state="disabled")

    @staticmethod
    def _animal_id(uid_hex):
        return int(uid_hex, 16) & 0x3FFFFFFFFF

    def _show_uid(self, uid, status):
        spaced = " ".join(uid[i:i+2] for i in range(0,len(uid),2))
        self.lbl_uid.config(text=spaced, fg="#0ea5e9")
        self.lbl_type.config(text=f"Type: {MRD2.tag_type_str(status)}")
        self.lbl_aid.config(text=f"Animal ID: {self._animal_id(uid)}")
        self.last_uid = uid

    def _update_block(self, idx, data):
        locked = (idx < 4 or idx >= 14)
        tag = "locked" if locked else "ok"
        lock = "Locked" if locked else "Open"
        vals = (idx, PAGE_LABELS[idx],
                f"{data[0]:02X}",f"{data[1]:02X}",f"{data[2]:02X}",f"{data[3]:02X}", lock)
        self.tree.item(str(idx), values=vals, tags=(tag,))
        self.last_blocks[idx] = data

    def _append_excel(self, uid, blocks):
        """Append one row to Excel CSV file with timestamp."""
        fname = os.path.join(BASE_DIR, "RFID_Log.csv")
        exists = os.path.isfile(fname)
        try:
            with open(fname, "a") as f:
                if not exists:
                    hdr = "DateTime,UID,AnimalID,Type"
                    for i in range(16):
                        hdr += f",Page{i}_B3,Page{i}_B2,Page{i}_B1,Page{i}_B0"
                    f.write(hdr + "\n")
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                aid = self._animal_id(uid)
                row = f"{now},{uid},{aid},HDX+"
                for i in range(16):
                    d = blocks[i]
                    if d:
                        row += f",{d[0]:02X},{d[1]:02X},{d[2]:02X},{d[3]:02X}"
                    else:
                        row += ",,,,"
                f.write(row + "\n")
            self.root.after(0, lambda: self._log(f"Logged to RFID_Log.csv"))
        except Exception as e:
            self.root.after(0, lambda: self._log(f"CSV Log Error: {str(e)}"))

    def _export_txt(self):
        uid = self.last_uid
        if not uid:
            messagebox.showwarning("Export","No tag data. Read a tag first."); return
        fname = f"RFID_TAG_{uid}.txt"
        lines = [f"RFID Tag Export — {time.strftime('%Y-%m-%d %H:%M:%S')}",
                 f"Chip UID: {uid}", self.lbl_type.cget("text"),
                 self.lbl_aid.cget("text"), self.lbl_progress.cget("text"), "",
                 f"{'Page':>4} | {'Description':<30} | B3   B2   B1   B0  | Status",
                 "-"*78]
        for i in range(16):
            d = self.last_blocks[i]
            if d:
                locked = "Locked" if (i<4 or i>=14) else "Open"
                lines.append(f"{i:>4} | {PAGE_LABELS[i]:<30} | "
                             f"{d[0]:02X}   {d[1]:02X}   {d[2]:02X}   {d[3]:02X}  | {locked}")
            else:
                lines.append(f"{i:>4} | {PAGE_LABELS[i]:<30} |  --   --   --   --  | N/A")
        path = os.path.join(BASE_DIR, fname)
        try:
            with open(path, "w") as f: f.write("\n".join(lines))
            self._log(f"Exported: {fname}")
            messagebox.showinfo("Export", f"Saved: {fname}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ── Connection ───────────────────────────────────
    def _toggle_conn(self):
        if not self.mrd.ser or not self.mrd.ser.is_open:
            self.mrd.port = self.port_var.get()
            self.mrd.baud = int(self.baud_var.get())
            res = self.mrd.connect()
            if res is True:
                self._log(f"Connected {self.mrd.port} @ {self.mrd.baud}")
                self.btn_conn.config(text="Disconnect")
                self.lbl_st.config(text="● ONLINE", fg="#10b981")
                self._controls(True); self._get_ver()
            else: messagebox.showerror("Connection Error", res)
        else:
            self.loop_chipid = False; self.chipid_var.set(False)
            self.loop_full = False; self.full_var.set(False)
            self.mrd.disconnect(); self._log("Disconnected.")
            self.btn_conn.config(text="Connect")
            self.lbl_st.config(text="● OFFLINE", fg="#ef4444")
            self._controls(False); self._clear()

    def _get_ver(self):
        v = self.mrd.get_version()
        if v:
            self._log(f"Firmware: {v}")
            self.lbl_st.config(text=f"● ONLINE {v}", fg="#10b981")
        else: self._log("Version: no response.")

    # ── Read Chip ID Loop ────────────────────────────
    def _toggle_chipid(self):
        if self.chipid_var.get():
            self.loop_full = False; self.full_var.set(False)
            self.loop_chipid = True
            self._log("Chip ID loop started.")
            threading.Thread(target=self._chipid_loop, daemon=True).start()
        else:
            self.loop_chipid = False; self._log("Chip ID loop stopped.")

    def _chipid_loop(self):
        count = 0
        while self.loop_chipid:
            result = self.mrd.charge_read()
            if result:
                status, uid = result
                count += 1
                self.root.after(0, lambda u=uid,s=status: self._show_uid(u, s))
                self.root.after(0, lambda c=count:
                    self.lbl_reads.config(text=f"Reads: {c}"))
                self.root.after(0, lambda u=uid,s=status:
                    self._log(f"#{count} UID: {u} | {MRD2.tag_type_str(s)}"))
                # Log to CSV (chip ID only, no blocks)
                self._append_excel(uid, [None]*16)
            else:
                self.root.after(0, lambda:
                    self.lbl_uid.config(text="SCANNING...", fg="#f59e0b"))
            time.sleep(0.08)

    # ── Full Read Loop ───────────────────────────────
    def _toggle_full(self):
        if self.full_var.get():
            self.loop_chipid = False; self.chipid_var.set(False)
            self.loop_full = True
            self._log("Full Read loop started.")
            threading.Thread(target=self._full_loop, daemon=True).start()
        else:
            self.loop_full = False; self._log("Full Read loop stopped.")

    def _full_loop(self):
        count = 0
        while self.loop_full:
            # Clear table for fresh read
            self.root.after(0, self._clear_table)
            self.root.after(0, lambda: self.lbl_progress.config(
                text="⏳ WAITING...", fg="#f59e0b"))
            self.root.after(0, lambda: self.pbar.configure(maximum=16, value=0))

            # Wait for tag
            result = self.mrd.charge_read()
            if not result:
                self.root.after(0, lambda:
                    self.lbl_uid.config(text="SCANNING...", fg="#f59e0b"))
                time.sleep(0.08)
                continue

            status, uid = result
            self.root.after(0, lambda u=uid,s=status: self._show_uid(u, s))
            count += 1
            self.root.after(0, lambda c=count: self.lbl_reads.config(text=f"Reads: {c}"))
            self.root.after(0, lambda: self.lbl_progress.config(
                text="📡 READING BLOCKS...", fg=self.PRIMARY))

            # Read all 16 blocks (pages 0-15)
            t0 = time.perf_counter()
            bits = 0
            blocks = [None]*16

            for pg in range(16):
                if not self.loop_full: break
                data = self.mrd.read_block(pg)
                blocks[pg] = data
                if data:
                    bits += 32
                    self.root.after(0, lambda i=pg,d=data: self._update_block(i, d))
                else:
                    self.root.after(0, lambda i=pg: self._log(
                        f"⚠ Page {i} failed after 3 retries"))

                self.root.after(0, lambda p=pg+1: self.pbar.configure(value=p))
                self.root.after(0, lambda b=bits: self.lbl_bits.config(
                    text=f"Bits: {b}/512"))
                e = time.perf_counter() - t0
                self.root.after(0, lambda e=e: self.lbl_timer.config(
                    text=f"⏱ {e:.3f}s"))

            t_total = time.perf_counter() - t0
            bps = bits/t_total if t_total > 0 else 0
            self.root.after(0, lambda b=bits,t=t_total,r=bps:
                self.lbl_progress.config(
                    text=f"✅ #{count} — {b} bits in {t:.3f}s ({r:.0f} bps)",
                    fg="#10b981"))
            self.root.after(0, lambda t=t_total:
                self.lbl_timer.config(text=f"⏱ {t:.3f}s"))
            self.root.after(0, lambda u=uid,c=count,b=bits,t=t_total:
                self._log(f"#{c} Full: {u} | {b}/512 bits | {t:.3f}s"))

            # Log to CSV
            self._append_excel(uid, blocks)
            time.sleep(0.1)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
