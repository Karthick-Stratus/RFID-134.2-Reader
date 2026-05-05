import serial, serial.tools.list_ports, threading, time, os, datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from PIL import Image, ImageTk

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

    def read_block(self, blk):
        """Read 4-byte block. blk=0..15 (0-indexed, matching Microreader II)."""
        d = self._parse(self._cmd([0x04, 0x80, ECM_HDX, 0x03, blk]))
        if not d or not self.is_valid(d[0]) or len(d) < 6: return None
        return d[2:6]

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
        self.root.title("Stratus RFID — TI RI-STU-MRD2")
        self.root.geometry("850x820")
        self.root.configure(bg="#0f172a")
        self.mrd = MRD2()
        self.loop_chipid = False
        self.loop_full = False
        self.last_blocks = [None]*16
        self.last_uid = ""
        self._build()
        self._refresh_ports()

    def _build(self):
        S = ttk.Style(); S.theme_use("clam")
        S.configure("TLabelframe", background="#1e293b", foreground="#94a3b8")
        S.configure("TLabelframe.Label", background="#1e293b",
                    foreground="#38bdf8", font=("Segoe UI",9,"bold"))
        S.configure("TButton", font=("Segoe UI",9,"bold"), padding=4)
        S.configure("Treeview", background="#1e293b", foreground="#e2e8f0",
                    fieldbackground="#1e293b", rowheight=20)
        S.configure("Treeview.Heading", background="#0f172a", foreground="#38bdf8",
                    font=("Segoe UI",8,"bold"))
        S.configure("green.Horizontal.TProgressbar", troughcolor="#1e293b",
                    background="#22c55e")

        # Header with logo
        h = tk.Frame(self.root, bg="#0f172a", pady=6)
        h.pack(fill="x")
        try:
            logo_path = os.path.join(BASE_DIR, "Stratus_Logo.png")
            img = Image.open(logo_path)
            img = img.resize((120, 40), Image.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img)
            tk.Label(h, image=self.logo_img, bg="#0f172a").pack(side="left", padx=12)
        except Exception:
            tk.Label(h, text="STRATUS", font=("Segoe UI",14,"bold"),
                     bg="#0f172a", fg="#38bdf8").pack(side="left", padx=12)
        tk.Label(h, text="TI RI-STU-MRD2  |  134.2kHz HDX+  |  ECM",
                 font=("Segoe UI",10,"bold"), bg="#0f172a", fg="#38bdf8").pack(side="left")

        # Connection
        cb = tk.Frame(self.root, bg="#1e293b", pady=4, padx=8)
        cb.pack(fill="x")
        tk.Label(cb,text="Port:",bg="#1e293b",fg="#94a3b8",font=("Segoe UI",9)
                 ).grid(row=0,column=0)
        self.port_var = tk.StringVar()
        self.port_cb = ttk.Combobox(cb, textvariable=self.port_var, width=9)
        self.port_cb.grid(row=0,column=1,padx=3)
        ttk.Button(cb,text="⟳",width=3,command=self._refresh_ports).grid(row=0,column=2)
        tk.Label(cb,text="Baud:",bg="#1e293b",fg="#94a3b8",font=("Segoe UI",9)
                 ).grid(row=0,column=3,padx=(8,2))
        self.baud_var = tk.StringVar(value="9600")
        ttk.Combobox(cb,textvariable=self.baud_var,width=7,
                     values=["9600","19200","57600","115200"]).grid(row=0,column=4,padx=3)
        self.btn_conn = ttk.Button(cb,text="Connect",command=self._toggle_conn,width=10)
        self.btn_conn.grid(row=0,column=5,padx=6)
        self.lbl_st = tk.Label(cb,text="● OFFLINE",fg="#ef4444",bg="#1e293b",
                               font=("Segoe UI",9,"bold"))
        self.lbl_st.grid(row=0,column=6,padx=4)
        self.btn_ver = ttk.Button(cb,text="Version",command=self._get_ver,
                                  state="disabled",width=7)
        self.btn_ver.grid(row=0,column=7,padx=4)

        # UID display
        uf = tk.Frame(self.root, bg="#0f172a", pady=6)
        uf.pack(fill="x")
        tk.Label(uf,text="CHIP UID",font=("Segoe UI",8,"bold"),
                 bg="#0f172a",fg="#64748b").pack()
        self.lbl_uid = tk.Label(uf,text="—  —  —  —  —  —  —  —",
                                font=("Consolas",20,"bold"),bg="#0f172a",fg="#38bdf8")
        self.lbl_uid.pack()
        info = tk.Frame(uf, bg="#0f172a")
        info.pack()
        self.lbl_type = tk.Label(info,text="Type: —",font=("Segoe UI",9),
                                 bg="#0f172a",fg="#94a3b8")
        self.lbl_type.pack(side="left",padx=10)
        self.lbl_aid = tk.Label(info,text="Animal ID: —",font=("Segoe UI",9),
                                bg="#0f172a",fg="#94a3b8")
        self.lbl_aid.pack(side="left",padx=10)

        # Controls
        c1 = tk.Frame(self.root, bg="#0f172a", pady=3)
        c1.pack(fill="x", padx=10)

        self.chipid_var = tk.BooleanVar(False)
        self.btn_chipid = ttk.Checkbutton(c1, text="🔑 Read Chip ID (Loop)",
                                          variable=self.chipid_var,
                                          command=self._toggle_chipid, state="disabled")
        self.btn_chipid.pack(side="left", padx=4)

        self.full_var = tk.BooleanVar(False)
        self.btn_fullloop = ttk.Checkbutton(c1, text="📄 Full Read (Loop)",
                                            variable=self.full_var,
                                            command=self._toggle_full, state="disabled")
        self.btn_fullloop.pack(side="left", padx=4)

        ttk.Button(c1,text="🗑 Clear",command=self._clear,width=7).pack(side="right",padx=3)
        ttk.Button(c1,text="💾 Export TXT",command=self._export_txt,width=11).pack(side="right",padx=3)

        # Progress
        pf = tk.Frame(self.root, bg="#1e293b", pady=4, padx=10)
        pf.pack(fill="x", padx=10, pady=3)
        row1 = tk.Frame(pf, bg="#1e293b")
        row1.pack(fill="x")
        self.lbl_progress = tk.Label(row1,text="IDLE",
                                     font=("Consolas",9,"bold"),bg="#1e293b",fg="#94a3b8")
        self.lbl_progress.pack(side="left")
        self.lbl_timer = tk.Label(row1,text="⏱ 0.000s",
                                  font=("Consolas",10,"bold"),bg="#1e293b",fg="#f59e0b")
        self.lbl_timer.pack(side="right")
        self.lbl_bits = tk.Label(row1,text="Bits: 0/512",
                                 font=("Consolas",9,"bold"),bg="#1e293b",fg="#22c55e")
        self.lbl_bits.pack(side="right",padx=15)
        self.lbl_reads = tk.Label(row1,text="Reads: 0",
                                  font=("Consolas",9,"bold"),bg="#1e293b",fg="#a78bfa")
        self.lbl_reads.pack(side="right",padx=15)
        self.pbar = ttk.Progressbar(pf, length=800, mode="determinate",
                                    style="green.Horizontal.TProgressbar")
        self.pbar.pack(fill="x", pady=(3,0))

        # Block table — show ALL 16 rows
        tf = ttk.LabelFrame(self.root, text=" Tag Memory Blocks (Pages 0-15) ")
        tf.pack(fill="both", expand=True, padx=10, pady=3)
        cols = ("pg","desc","b3","b2","b1","b0","st")
        self.tree = ttk.Treeview(tf,columns=cols,show="headings",height=16)
        for c,w,t in [("pg",40,"Page"),("desc",270,"Description"),
                      ("b3",55,"Byte3"),("b2",55,"Byte2"),
                      ("b1",55,"Byte1"),("b0",55,"Byte0"),("st",65,"Status")]:
            self.tree.heading(c,text=t)
            self.tree.column(c,width=w,anchor="center" if c!="desc" else "w")
        self.tree.tag_configure("locked", background="#7c3aed", foreground="white")
        self.tree.tag_configure("ok", background="#065f46", foreground="white")
        self.tree.tag_configure("empty", background="#1e293b", foreground="#475569")
        self.tree.pack(fill="both", expand=True, padx=4, pady=2)
        for i,l in enumerate(PAGE_LABELS):
            self.tree.insert("","end",iid=str(i),
                             values=(i,l,"--","--","--","--","—"),tags=("empty",))

        # Log
        lf = ttk.LabelFrame(self.root, text=" Log ")
        lf.pack(fill="x", padx=10, pady=(2,6))
        lc = tk.Frame(lf, bg="#1e293b")
        lc.pack(fill="x",padx=4,pady=(2,0))
        ttk.Button(lc,text="Clear Log",command=self._clear_log,width=9).pack(side="right")
        self.log = scrolledtext.ScrolledText(lf,height=4,font=("Consolas",8),
                    bg="#0f172a",fg="#94a3b8",insertbackground="white",state="disabled")
        self.log.pack(fill="x",padx=4,pady=2)

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
        self.lbl_uid.config(text="—  —  —  —  —  —  —  —", fg="#38bdf8")
        self.lbl_aid.config(text="Animal ID: —")
        self.lbl_type.config(text="Type: —")
        self.lbl_progress.config(text="IDLE", fg="#94a3b8")
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
        self.lbl_uid.config(text=spaced, fg="#22c55e")
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
        with open(path, "w") as f: f.write("\n".join(lines))
        self._log(f"Exported: {fname}")
        messagebox.showinfo("Export", f"Saved: {fname}")

    # ── Connection ───────────────────────────────────
    def _toggle_conn(self):
        if not self.mrd.ser or not self.mrd.ser.is_open:
            self.mrd.port = self.port_var.get()
            self.mrd.baud = int(self.baud_var.get())
            res = self.mrd.connect()
            if res is True:
                self._log(f"Connected {self.mrd.port} @ {self.mrd.baud}")
                self.btn_conn.config(text="Disconnect")
                self.lbl_st.config(text="● ONLINE", fg="#22c55e")
                self._controls(True); self._get_ver()
            else: messagebox.showerror("Error", res)
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
            self.lbl_st.config(text=f"● ONLINE {v}", fg="#22c55e")
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
            count += 1
            self.root.after(0, lambda u=uid,s=status: self._show_uid(u, s))
            self.root.after(0, lambda c=count: self.lbl_reads.config(text=f"Reads: {c}"))
            self.root.after(0, lambda: self.lbl_progress.config(
                text="📡 READING...", fg="#38bdf8"))

            # Read all 16 blocks (pages 0-15, 0-indexed)
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
                    fg="#22c55e"))
            self.root.after(0, lambda t=t_total:
                self.lbl_timer.config(text=f"⏱ {t:.3f}s"))
            self.root.after(0, lambda u=uid,c=count,b=bits,t=t_total:
                self._log(f"#{c} Full: {u} | {b}/512 bits | {t:.3f}s"))

            # Log to CSV
            self._append_excel(uid, blocks)
            time.sleep(0.1)  # brief pause before next cycle


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
