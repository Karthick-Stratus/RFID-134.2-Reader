import serial, serial.tools.list_ports, threading, time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ECM Protocol for TI RI-STU-MRD2 (SCBU049)
# Status byte validation (Table 12):
#   bit2=1 → Start byte detected, bit3=1 → DBCC OK
#   bits[1:0]: 00=RO, 01=RW, 10=MPT, 11=Other/Noise
#   VALID read = (status & 0x0C) == 0x0C  (both bit2+bit3 set)

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
        """ECM Status: 0x00=success, 0x03=no tag. Reject only no-tag."""
        if status == 0x03: return False          # No tag
        return True

    @staticmethod
    def tag_type_str(status):
        t = status & 0x03
        return {0:"RO (Read-Only)", 1:"R/W", 2:"MPT/SAMPT", 3:"Other"}.get(t,"?")

    def get_version(self):
        d = self._parse(self._cmd([0x02, 0x83, 0x00]))
        if d and len(d) >= 1: return f"v{d[0]>>4}.{d[0]&0x0F}"
        return None

    def charge_read(self):
        """Returns (status, uid_hex) or None. Double-read for noise rejection."""
        d = self._parse(self._cmd([0x03, 0x80, ECM_HDX, 0x00]))
        if not d or not self.is_valid(d[0]) or len(d) < 9: return None
        uid1 = "".join(f"{b:02X}" for b in reversed(d[1:9]))
        # Second read to confirm (rejects noise — noise gives random data each time)
        time.sleep(0.08)  # wait one HDX cycle
        d2 = self._parse(self._cmd([0x03, 0x80, ECM_HDX, 0x00]))
        if not d2 or not self.is_valid(d2[0]) or len(d2) < 9: return None
        uid2 = "".join(f"{b:02X}" for b in reversed(d2[1:9]))
        if uid1 != uid2: return None  # mismatch = noise
        return d[0], uid1

    def read_block(self, blk):
        """Read single 4-byte block. Returns [B3,B2,B1,B0] or None."""
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

# Tag geometry constants
TAG_TYPES = {
    "1-Block RO (64-bit)":    {"blocks": 1,  "bits": 64},
    "1-Block R/W (256-bit)":  {"blocks": 4,  "bits": 256},
    "16-Block MPT (1360-bit)":{"blocks": 16, "bits": 512},
}

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Stratus RFID — TI RI-STU-MRD2 | ECM")
        self.root.geometry("830x780")
        self.root.configure(bg="#0f172a")
        self.mrd = MRD2()
        self.polling = False
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

        # Header
        h = tk.Frame(self.root, bg="#0f172a", pady=6)
        h.pack(fill="x")
        tk.Label(h, text="TI RI-STU-MRD2", font=("Segoe UI",14,"bold"),
                 bg="#0f172a", fg="#38bdf8").pack(side="left", padx=12)
        tk.Label(h, text="134.2kHz | HDX+ | ECM Protocol",
                 font=("Segoe UI",9), bg="#0f172a", fg="#64748b").pack(side="left")

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

        # UID + Tag Info display
        uf = tk.Frame(self.root, bg="#0f172a", pady=8)
        uf.pack(fill="x")
        tk.Label(uf,text="CHIP UID",font=("Segoe UI",8,"bold"),
                 bg="#0f172a",fg="#64748b").pack()
        self.lbl_uid = tk.Label(uf,text="—  —  —  —  —  —  —  —",
                                font=("Consolas",20,"bold"),bg="#0f172a",fg="#38bdf8")
        self.lbl_uid.pack()
        info_row = tk.Frame(uf, bg="#0f172a")
        info_row.pack()
        self.lbl_type = tk.Label(info_row,text="Type: —",font=("Segoe UI",9),
                                 bg="#0f172a",fg="#94a3b8")
        self.lbl_type.pack(side="left",padx=10)
        self.lbl_aid = tk.Label(info_row,text="Animal ID: —",font=("Segoe UI",9),
                                bg="#0f172a",fg="#94a3b8")
        self.lbl_aid.pack(side="left",padx=10)

        # Controls row 1
        c1 = tk.Frame(self.root, bg="#0f172a", pady=2)
        c1.pack(fill="x", padx=10)
        self.btn_fast = ttk.Button(c1,text="⚡ FAST READ (All)",
                                   command=self._fast_read,state="disabled",width=18)
        self.btn_fast.pack(side="left",padx=3)
        self.btn_full = ttk.Button(c1,text="📄 Full Read",
                                   command=self._full_read,state="disabled",width=12)
        self.btn_full.pack(side="left",padx=3)
        self.poll_var = tk.BooleanVar(False)
        self.chk_poll = ttk.Checkbutton(c1,text="Auto Poll",
                                        variable=self.poll_var,
                                        command=self._toggle_poll,state="disabled")
        self.chk_poll.pack(side="left",padx=6)
        self.btn_export = ttk.Button(c1,text="💾 Export",command=self._export,width=9)
        self.btn_export.pack(side="right",padx=3)
        ttk.Button(c1,text="🗑 Clear",command=self._clear,width=7).pack(side="right",padx=3)

        # Read mode selector
        c2 = tk.Frame(self.root, bg="#0f172a", pady=2)
        c2.pack(fill="x", padx=10)
        tk.Label(c2,text="Tag Expect:",bg="#0f172a",fg="#94a3b8",
                 font=("Segoe UI",9)).pack(side="left")
        self.tag_mode = tk.StringVar(value="17-Block MPT (1360-bit)")
        ttk.Combobox(c2, textvariable=self.tag_mode, width=28,
                     values=list(TAG_TYPES.keys()),state="readonly").pack(side="left",padx=4)

        # Progress / Timing bar
        pf = tk.Frame(self.root, bg="#1e293b", pady=6, padx=10)
        pf.pack(fill="x", padx=10, pady=4)
        row1 = tk.Frame(pf, bg="#1e293b")
        row1.pack(fill="x")
        self.lbl_progress = tk.Label(row1,text="Progress: IDLE",
                                     font=("Consolas",9,"bold"),bg="#1e293b",fg="#94a3b8")
        self.lbl_progress.pack(side="left")
        self.lbl_timer = tk.Label(row1,text="⏱ 0.000s",
                                  font=("Consolas",10,"bold"),bg="#1e293b",fg="#f59e0b")
        self.lbl_timer.pack(side="right")
        self.lbl_bits = tk.Label(row1,text="Bits: 0",
                                 font=("Consolas",9,"bold"),bg="#1e293b",fg="#22c55e")
        self.lbl_bits.pack(side="right",padx=15)
        self.pbar = ttk.Progressbar(pf, length=780, mode="determinate",
                                    style="green.Horizontal.TProgressbar")
        self.pbar.pack(fill="x", pady=(4,0))

        # Block table
        tf = ttk.LabelFrame(self.root, text=" Tag Memory Blocks ")
        tf.pack(fill="x", padx=10, pady=2)
        cols = ("blk","desc","b3","b2","b1","b0","st")
        self.tree = ttk.Treeview(tf,columns=cols,show="headings",height=8)
        for c,w,t in [("blk",38,"Blk"),("desc",260,"Description"),
                      ("b3",50,"Byte3"),("b2",50,"Byte2"),
                      ("b1",50,"Byte1"),("b0",50,"Byte0"),("st",65,"Status")]:
            self.tree.heading(c,text=t); self.tree.column(c,width=w,
                anchor="center" if c!="desc" else "w")
        self.tree.tag_configure("ok", background="#065f46", foreground="white")
        self.tree.tag_configure("locked", background="#7c3aed", foreground="white")
        self.tree.tag_configure("empty", background="#1e293b", foreground="#475569")
        self.tree.pack(fill="x",padx=4,pady=2)
        for i,l in enumerate(PAGE_LABELS):
            self.tree.insert("","end",iid=str(i),
                             values=(i,l,"--","--","--","--","—"),tags=("empty",))

        # Log
        lf = ttk.LabelFrame(self.root, text=" Log ")
        lf.pack(fill="both", expand=True, padx=10, pady=(2,6))
        lc = tk.Frame(lf, bg="#1e293b")
        lc.pack(fill="x",padx=4,pady=(2,0))
        ttk.Button(lc,text="Clear Log",command=self._clear_log,width=9).pack(side="right")
        self.log = scrolledtext.ScrolledText(lf,height=5,font=("Consolas",8),
                    bg="#0f172a",fg="#94a3b8",insertbackground="white",state="disabled")
        self.log.pack(fill="both",expand=True,padx=4,pady=2)

    # ── Helpers ──────────────────────────────────────
    def _log(self, m):
        self.log.config(state="normal")
        self.log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {m}\n")
        self.log.see(tk.END); self.log.config(state="disabled")

    def _controls(self, en):
        s = "normal" if en else "disabled"
        for w in [self.btn_fast,self.btn_full,self.chk_poll,self.btn_ver,self.btn_export]: w.config(state=s)

    def _export(self):
        """Export tag data to text file named by UID."""
        uid_text = self.lbl_uid.cget("text").replace(" ","")
        if not uid_text or "—" in uid_text or "NO" in uid_text:
            messagebox.showwarning("Export","No tag data to export. Read a tag first.")
            return
        fname = f"RFID_TAG_{uid_text}.txt"
        lines = [f"RFID Tag Export — {time.strftime('%Y-%m-%d %H:%M:%S')}"]
        lines.append(f"Chip UID: {uid_text}")
        lines.append(f"{self.lbl_type.cget('text')}")
        lines.append(f"{self.lbl_aid.cget('text')}")
        lines.append(f"{self.lbl_progress.cget('text')}")
        lines.append("")
        lines.append(f"{'Blk':>4} | {'Description':<30} | B3   B2   B1   B0  | Status")
        lines.append("-" * 78)
        for i in range(16):
            vals = self.tree.item(str(i))["values"]
            if vals:
                lines.append(f"{vals[0]:>4} | {str(vals[1]):<30} | {vals[2]:>4} {vals[3]:>4} {vals[4]:>4} {vals[5]:>4} | {vals[6]}")
        import os
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        with open(path, "w") as f:
            f.write("\n".join(lines))
        self._log(f"Exported to {fname}")
        messagebox.showinfo("Export", f"Saved: {fname}")

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if "COM17" in ports: self.port_var.set("COM17")
        elif ports: self.port_var.set(ports[0])
        self._log(f"Ports: {', '.join(ports) or 'none'}")

    def _clear(self):
        self.lbl_uid.config(text="—  —  —  —  —  —  —  —", fg="#38bdf8")
        self.lbl_aid.config(text="Animal ID: —")
        self.lbl_type.config(text="Type: —")
        self.lbl_progress.config(text="Progress: IDLE", fg="#94a3b8")
        self.lbl_timer.config(text="⏱ 0.000s")
        self.lbl_bits.config(text="Bits: 0")
        self.pbar["value"] = 0
        for i in range(16):
            self.tree.item(str(i),values=(i,PAGE_LABELS[i],"--","--","--","--","—"),
                           tags=("empty",))

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
        aid = self._animal_id(uid)
        self.lbl_aid.config(text=f"Animal ID: {aid}")

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
            else:
                messagebox.showerror("Error", res)
        else:
            self.polling = False; self.poll_var.set(False)
            self.mrd.disconnect(); self._log("Disconnected.")
            self.btn_conn.config(text="Connect")
            self.lbl_st.config(text="● OFFLINE", fg="#ef4444")
            self._controls(False); self._clear()

    def _get_ver(self):
        v = self.mrd.get_version()
        if v:
            self._log(f"Firmware: {v}")
            self.lbl_st.config(text=f"● ONLINE {v}", fg="#22c55e")
        else:
            self._log("Version: no response.")

    # ── Fast Read (all blocks, fastest possible) ─────
    def _fast_read(self):
        self._controls(False)
        threading.Thread(target=self._fast_thread, daemon=True).start()

    def _fast_thread(self):
        result = self.mrd.charge_read()
        if not result:
            self.root.after(0, lambda: self._log("No valid tag."))
            self.root.after(0, lambda: self.lbl_uid.config(text="NO TAG",fg="#64748b"))
            self.root.after(0, lambda: self._controls(True))
            return
        status, uid = result
        self.root.after(0, lambda: self._show_uid(uid, status))
        self.root.after(0, lambda: self.lbl_progress.config(text="⚡ FAST READING...",fg="#f59e0b"))
        t0 = time.perf_counter()
        bits = 0
        self.root.after(0, lambda: self.pbar.configure(maximum=16))
        for blk_idx in range(16):
            page = blk_idx + 1  # pages 1-16
            data = self.mrd.read_block(page)
            if data:
                bits += 32
                locked = (blk_idx < 4 or blk_idx >= 14)
                tag = "locked" if locked else "ok"
                lock = "Locked" if locked else "Open"
                vals = (page,PAGE_LABELS[blk_idx],f"{data[0]:02X}",f"{data[1]:02X}",f"{data[2]:02X}",f"{data[3]:02X}",lock)
                self.root.after(0, lambda b=blk_idx,v=vals,tg=tag: self.tree.item(str(b),values=v,tags=(tg,)))
            self.root.after(0, lambda p=blk_idx+1: self.pbar.configure(value=p))
            self.root.after(0, lambda b=bits: self.lbl_bits.config(text=f"Bits: {b}/512"))
            e = time.perf_counter()-t0
            self.root.after(0, lambda e=e: self.lbl_timer.config(text=f"⏱ {e:.3f}s"))
        t_total = time.perf_counter()-t0
        self.root.after(0, lambda: self.lbl_progress.config(text=f"✅ {bits} bits in {t_total:.3f}s ({bits/t_total:.0f} bps)",fg="#22c55e"))
        self.root.after(0, lambda: self.lbl_timer.config(text=f"⏱ {t_total:.3f}s"))
        self.root.after(0, lambda: self._log(f"Fast Read done: {bits}/512 bits in {t_total:.3f}s | {uid}"))
        self.root.after(0, lambda: self._controls(True))

    # ── Full Read (All Blocks with progress) ─────────
    def _full_read(self):
        self.btn_fast.config(state="disabled")
        self.btn_full.config(state="disabled")
        threading.Thread(target=self._full_read_thread, daemon=True).start()

    def _full_read_thread(self):
        mode = self.tag_mode.get()
        cfg  = TAG_TYPES.get(mode, TAG_TYPES["17-Block MPT (1360-bit)"])
        n_blocks  = cfg["blocks"]
        total_bits = cfg["bits"]

        self.root.after(0, lambda: self.lbl_progress.config(
            text="⏳ WAITING FOR TAG...", fg="#f59e0b"))
        self.root.after(0, lambda: self.pbar.configure(maximum=n_blocks))
        self.root.after(0, lambda: self._log(
            f"Full Read: {mode} ({n_blocks} blocks, {total_bits} bits)"))

        # Step 1: Wait for valid tag
        uid_result = None
        for _ in range(50):  # try for 5 seconds
            uid_result = self.mrd.charge_read()
            if uid_result: break
            time.sleep(0.1)

        if not uid_result:
            self.root.after(0, lambda: self.lbl_progress.config(
                text="❌ NO TAG FOUND", fg="#ef4444"))
            self.root.after(0, lambda: self._controls(True))
            return

        status, uid = uid_result
        self.root.after(0, lambda: self._show_uid(uid, status))
        self.root.after(0, lambda: self._log(f"Tag detected: {uid}"))
        self.root.after(0, lambda: self.lbl_progress.config(
            text="📡 READING BLOCKS...", fg="#38bdf8"))

        # Step 2: Read blocks with timing
        t_start = time.perf_counter()
        bits_read = 0
        blocks_data = []

        for blk_idx in range(n_blocks):
            page = blk_idx + 1  # pages 1-16
            data = self.mrd.read_block(page)
            blocks_data.append(data)
            elapsed = time.perf_counter() - t_start

            if data:
                bits_read += 32
                locked = (blk_idx < 4 or blk_idx >= 14)
                tag = "locked" if locked else "ok"
                lock = "Locked" if locked else "Open"
                vals = (page, PAGE_LABELS[blk_idx],
                        f"{data[0]:02X}",f"{data[1]:02X}",
                        f"{data[2]:02X}",f"{data[3]:02X}", lock)
                self.root.after(0, lambda b=blk_idx,v=vals,tg=tag:
                    self.tree.item(str(b), values=v, tags=(tg,)))
            else:
                self.root.after(0, lambda b=blk_idx,p=page:
                    self.tree.item(str(b),
                        values=(p,PAGE_LABELS[b],"??","??","??","??","Fail"),
                        tags=("empty",)))

            pct = int((blk_idx+1) / n_blocks * 100)
            self.root.after(0, lambda p=blk_idx+1: self.pbar.configure(value=p))
            self.root.after(0, lambda b=bits_read:
                self.lbl_bits.config(text=f"Bits: {b} / {total_bits}"))
            self.root.after(0, lambda e=elapsed:
                self.lbl_timer.config(text=f"⏱ {e:.3f}s"))
            self.root.after(0, lambda p=pct:
                self.lbl_progress.config(text=f"📡 READING... {p}%"))

        # Step 3: Done
        t_total = time.perf_counter() - t_start
        bits_per_sec = bits_read / t_total if t_total > 0 else 0

        # Extract Animal ID from blocks 14+15
        aid_str = "—"
        if n_blocks >= 16 and blocks_data[14] and blocks_data[15]:
            lo = blocks_data[14]
            hi = blocks_data[15]
            aid_hex = "".join(f"{b:02X}" for b in hi + lo)
            aid_str = str(int(aid_hex, 16) & 0x3FFFFFFFFF)
            self.root.after(0, lambda a=aid_str:
                self.lbl_aid.config(text=f"Animal ID: {a}"))
            self.root.after(0, lambda l=lo,h=hi:
                self._log(f"Animal ID Lo: {l[0]:02X}{l[1]:02X}{l[2]:02X}{l[3]:02X}  "
                          f"Hi: {h[0]:02X}{h[1]:02X}{h[2]:02X}{h[3]:02X}"))

        self.root.after(0, lambda: self.lbl_progress.config(
            text=f"✅ DONE — {bits_read} bits in {t_total:.3f}s "
                 f"({bits_per_sec:.0f} bits/s)", fg="#22c55e"))
        self.root.after(0, lambda: self.lbl_timer.config(
            text=f"⏱ {t_total:.3f}s"))
        self.root.after(0, lambda: self._log(
            f"Full Read complete: {bits_read}/{total_bits} bits in {t_total:.3f}s "
            f"({bits_per_sec:.0f} bps) | Tag: {uid}"))
        self.root.after(0, lambda: self._controls(True))

    # ── Auto Poll (All Blocks) ───────────────────────
    def _toggle_poll(self):
        if self.poll_var.get():
            self.polling = True
            self._log("Auto-poll started (all blocks per cycle).")
            threading.Thread(target=self._poll_loop, daemon=True).start()
        else:
            self.polling = False; self._log("Auto-poll stopped.")

    def _poll_loop(self):
        last_uid = None
        while self.polling:
            uid_result = self.mrd.charge_read()
            if not uid_result:
                if last_uid:
                    last_uid = None
                    self.root.after(0, lambda:
                        self.lbl_uid.config(text="NO TAG", fg="#64748b"))
                time.sleep(0.08)
                continue

            status, uid = uid_result
            if uid != last_uid:
                last_uid = uid
                self.root.after(0, lambda u=uid, s=status: self._show_uid(u, s))
                self.root.after(0, lambda u=uid: self._log(f"New Tag: {u}"))

                # Read all blocks for this tag
                mode = self.tag_mode.get()
                cfg  = TAG_TYPES.get(mode, TAG_TYPES["17-Block MPT (1360-bit)"])
                n_blocks = cfg["blocks"]
                total_bits = cfg["bits"]
                t0 = time.perf_counter()
                bits = 0

                self.root.after(0, lambda: self.pbar.configure(maximum=n_blocks))

                for blk_idx in range(n_blocks):
                    if not self.polling: break
                    page = blk_idx + 1
                    data = self.mrd.read_block(page)
                    elapsed = time.perf_counter() - t0
                    if data:
                        bits += 32
                        locked = (blk_idx<4 or blk_idx>=14)
                        tag = "locked" if locked else "ok"
                        lock = "Locked" if locked else "Open"
                        vals = (page, PAGE_LABELS[blk_idx],
                                f"{data[0]:02X}",f"{data[1]:02X}",
                                f"{data[2]:02X}",f"{data[3]:02X}", lock)
                        self.root.after(0, lambda b=blk_idx,v=vals,tg=tag:
                            self.tree.item(str(b), values=v, tags=(tg,)))

                    self.root.after(0, lambda p=blk_idx+1: self.pbar.configure(value=p))
                    self.root.after(0, lambda b=bits:
                        self.lbl_bits.config(text=f"Bits: {b}/{total_bits}"))
                    self.root.after(0, lambda e=elapsed:
                        self.lbl_timer.config(text=f"⏱ {e:.3f}s"))

                t_total = time.perf_counter() - t0
                self.root.after(0, lambda b=bits,t=t_total:
                    self.lbl_progress.config(
                        text=f"✅ {b} bits in {t:.3f}s", fg="#22c55e"))
                self.root.after(0, lambda t=t_total:
                    self.lbl_timer.config(text=f"⏱ {t:.3f}s"))

            time.sleep(0.08)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
