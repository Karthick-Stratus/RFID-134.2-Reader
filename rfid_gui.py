import serial
import serial.tools.list_ports
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ============================================================
# TI RI-STU-MRD2 LMP Protocol - Verified from TI Microreader II
# ============================================================
# KEY FINDINGS from Microreader II raw TX/RX capture:
#
# 1. READ PAGE COMMAND (what Microreader II actually sends):
#    TX: 01 04 80 03 03 [page] [BCC]
#    BCC = 0x04^0x80^0x03^0x03^page
#
# 2. READ PAGE RESPONSE (success):
#    RX: 01 0A 00 00 [Byte3][Byte2][Byte1][Byte0][x][x][x][x] BCC
#    Length=0x0A=10, Status=0x00
#
# 3. STATUS CODES:
#    0x00 = SUCCESS
#    0x03 = No Tag Detected
#    0x07 = Other/Raw HDX data (noise OR real tag in raw mode)
#
# 4. WHY PYTHON FAILS vs Microreader II:
#    - Microreader II uses READ PAGE commands (0x80 based)
#    - Microreader II polls every ~80ms (HDX charge+listen cycle)
#    - CMD 0x00 "Single Read" requires EXACT timing with HDX cycle
#    - 500ms poll interval misses most tag read windows
#
# 5. SOLUTION:
#    - Use READ PAGE command (0x80) to read Chip ID pages 1-3
#    - Poll at 100ms intervals (10x per second)
#    - Page 1 = Chip ID Byte 3,2,1,0 (address 0x01)
#    - Page 2 = Reserved + Chip ID Byte 6,5,4 (address 0x02)
#    - Page 3 = Reserved + Chip ID Byte 9,8,7 (address 0x03)
# ============================================================

class MRD2Reader:
    SOH            = 0x01
    CMD_VERSION    = 0x03
    CMD_SINGLE     = 0x00   # Single read (HDX timing sensitive)
    CMD_READ_PAGE  = 0x80   # Read page sub-cmd byte (per Microreader II capture)

    PAGE_LABELS = [
        "Chip ID Byte 3,2,1,0",
        "Reserved & Chip ID Byte 6,5,4",
        "Reserved & Chip ID Byte 9,8,7",
        "Config Byte 2,1 & CRC MSB,LSB",
        "User Memory","User Memory","User Memory","User Memory",
        "User Memory","User Memory","User Memory","User Memory",
        "User Memory","User Memory",
        "Animal ID Byte 3,2,1,0",
        "Animal ID Byte 7,6,5,4",
    ]

    def __init__(self, port=None, baudrate=9600, timeout=0.3):
        self.port     = port
        self.baudrate = baudrate
        self.timeout  = timeout
        self.ser      = None

    # ── Serial helpers ─────────────────────────────────────────
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate,
                                     timeout=self.timeout)
            return True
        except Exception as e:
            return str(e)

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _bcc(self, data):
        v = 0
        for b in data: v ^= b
        return v

    def _transact(self, payload):
        """Send [SOH]+payload+[BCC] and return raw bytes."""
        if not self.ser or not self.ser.is_open:
            return None
        bcc = self._bcc(payload)
        pkt = bytearray([self.SOH] + payload + [bcc])
        self.ser.reset_input_buffer()
        self.ser.write(pkt)
        return self.ser.read(32)

    def _parse(self, raw):
        """Return list of data bytes, 'BCC_ERR', or None."""
        if not raw or len(raw) < 4 or raw[0] != self.SOH:
            return None
        ln = raw[1]
        if len(raw) < ln + 3:
            return None
        data = raw[2:2+ln]
        if self._bcc([ln] + list(data)) != raw[2+ln]:
            return "BCC_ERR"
        return list(data)

    # ── Commands ───────────────────────────────────────────────
    def get_version(self):
        raw = self._transact([0x01, self.CMD_VERSION])
        d   = self._parse(raw)
        if d and d != "BCC_ERR":
            return ".".join(str(b) for b in d)
        return None

    def read_page(self, page):
        """
        Read one 4-byte memory page (1-16).
        Mirrors exact Microreader II TX: 01 04 80 03 03 [page] [BCC]
        Returns [B3,B2,B1,B0] or None.
        """
        payload = [0x04, 0x80, 0x03, 0x03, page]
        raw = self._transact(payload)
        if raw:
            raw_hex = " ".join(f"{b:02X}" for b in raw)
        d = self._parse(raw)
        if d and d != "BCC_ERR" and len(d) >= 4:
            if d[0] == 0x00:           # status OK
                return d[2:6]          # [B3, B2, B1, B0]
        return None

    def read_uid(self):
        """
        Read Chip ID from pages 1+2, reconstruct 8-byte UID.
        Returns dict with uid_hex, uid_bytes, animal_id_dec or None.
        """
        p1 = self.read_page(1)   # Byte3,2,1,0 of Chip ID
        time.sleep(0.02)
        p2 = self.read_page(2)   # Reserved,Byte6,5,4
        if not p1 or not p2:
            return None
        # p1 = [B3,B2,B1,B0], p2 = [Res,B6,B5,B4]
        b3,b2,b1,b0 = p1
        _,b6,b5,b4  = p2
        uid_msb = [b6,b5,b4,b3,b2,b1,b0]   # 7 known bytes; B7 is MSB
        # Read page 3 for Byte9,8,7
        p3 = self.read_page(3)
        b7 = p3[3] if p3 else 0x00          # [Res,B9,B8,B7]
        uid_bytes = [b7,b6,b5,b4,b3,b2,b1,b0]
        uid_hex   = "".join(f"{b:02X}" for b in uid_bytes)
        val       = int.from_bytes(uid_bytes, "big")
        animal_id = val & 0x3FFFFFFFFF
        return {"uid_hex": uid_hex,
                "uid_bytes": uid_bytes,
                "animal_id": animal_id,
                "page1": p1, "page2": p2, "page3": p3}

    def read_all_pages(self):
        """Read pages 1-16. Returns list of [B3,B2,B1,B0] or None."""
        result = []
        for pg in range(1, 17):
            result.append(self.read_page(pg))
            time.sleep(0.03)
        return result

    def single_read_raw(self):
        """
        CMD 0x00 single read — returns raw hex string for diagnostics.
        Status 0x03 = no tag, 0x07 = raw HDX data (real or noise).
        """
        raw = self._transact([0x01, self.CMD_SINGLE])
        if not raw:
            return None, None
        hex_str = " ".join(f"{b:02X}" for b in raw)
        d = self._parse(raw)
        return hex_str, d


# ── GUI ────────────────────────────────────────────────────────

class App:
    def __init__(self, root):
        self.root    = root
        self.root.title("Stratus RFID — TI RI-STU-MRD2")
        self.root.geometry("800x700")
        self.root.configure(bg="#0f172a")

        self.reader  = MRD2Reader()
        self.polling = False
        self._build()
        self._refresh_ports()

    # ── Build UI ───────────────────────────────────────────────
    def _build(self):
        S = ttk.Style()
        S.theme_use("clam")
        S.configure("TLabelframe",       background="#1e293b", foreground="#94a3b8")
        S.configure("TLabelframe.Label", background="#1e293b",
                    foreground="#38bdf8", font=("Segoe UI",9,"bold"))
        S.configure("TButton",           font=("Segoe UI",9,"bold"), padding=4)
        S.configure("Treeview",          background="#1e293b", foreground="#e2e8f0",
                    fieldbackground="#1e293b", rowheight=22)
        S.configure("Treeview.Heading",  background="#0f172a", foreground="#38bdf8",
                    font=("Segoe UI",9,"bold"))
        S.map("Treeview", background=[("selected","#2563eb")])

        # Header
        hdr = tk.Frame(self.root, bg="#0f172a", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="TI RI-STU-MRD2  RFID Reader",
                 font=("Segoe UI",15,"bold"), bg="#0f172a", fg="#38bdf8").pack(side="left",padx=15)
        tk.Label(hdr, text="134.2 kHz | HDX/FDX | LMP Protocol",
                 font=("Segoe UI",9), bg="#0f172a", fg="#64748b").pack(side="left")

        # Connection bar
        cb = tk.Frame(self.root, bg="#1e293b", pady=6, padx=10)
        cb.pack(fill="x")

        tk.Label(cb,text="Port:",bg="#1e293b",fg="#94a3b8",
                 font=("Segoe UI",9)).grid(row=0,column=0,sticky="w")
        self.port_var = tk.StringVar()
        self.port_cb  = ttk.Combobox(cb, textvariable=self.port_var, width=9)
        self.port_cb.grid(row=0,column=1,padx=3)

        ttk.Button(cb,text="⟳",width=3,command=self._refresh_ports).grid(row=0,column=2)

        tk.Label(cb,text="Baud:",bg="#1e293b",fg="#94a3b8",
                 font=("Segoe UI",9)).grid(row=0,column=3,padx=(8,2))
        self.baud_var = tk.StringVar(value="9600")
        ttk.Combobox(cb,textvariable=self.baud_var,width=8,
                     values=["9600","19200","38400","57600","115200"]
                     ).grid(row=0,column=4,padx=3)

        self.btn_conn = ttk.Button(cb,text="Connect",command=self._toggle_conn,width=11)
        self.btn_conn.grid(row=0,column=5,padx=6)

        self.lbl_st = tk.Label(cb,text="● OFFLINE",fg="#ef4444",
                                bg="#1e293b",font=("Segoe UI",9,"bold"))
        self.lbl_st.grid(row=0,column=6,padx=4)

        self.btn_ver = ttk.Button(cb,text="Version",command=self._version,state="disabled",width=8)
        self.btn_ver.grid(row=0,column=7,padx=4)

        # UID display
        uf = tk.Frame(self.root, bg="#0f172a", pady=12)
        uf.pack(fill="x")
        tk.Label(uf,text="CHIP UID (64-bit)",font=("Segoe UI",8,"bold"),
                 bg="#0f172a",fg="#64748b").pack()
        self.lbl_uid = tk.Label(uf,text="— — — — — — — —",
                                font=("Consolas",24,"bold"),bg="#0f172a",fg="#38bdf8")
        self.lbl_uid.pack()
        self.lbl_aid = tk.Label(uf,text="Animal ID (ISO 11784): —",
                                font=("Segoe UI",10),bg="#0f172a",fg="#94a3b8")
        self.lbl_aid.pack()

        # Control bar
        ctrl = tk.Frame(self.root, bg="#0f172a", pady=4)
        ctrl.pack(fill="x", padx=10)

        self.btn_readuid  = ttk.Button(ctrl,text="▶ Read UID (Pages 1-3)",
                                       command=self._read_uid,state="disabled",width=22)
        self.btn_readuid.pack(side="left",padx=4)

        self.poll_var = tk.BooleanVar(value=False)
        self.chk_poll = ttk.Checkbutton(ctrl,text="Auto Poll (100ms)",
                                        variable=self.poll_var,
                                        command=self._toggle_poll,state="disabled")
        self.chk_poll.pack(side="left",padx=6)

        self.btn_pages = ttk.Button(ctrl,text="📄 All Pages",
                                    command=self._all_pages,state="disabled",width=12)
        self.btn_pages.pack(side="left",padx=4)

        self.btn_diag  = ttk.Button(ctrl,text="🔬 Diagnose",
                                    command=self._diagnose,state="disabled",width=12)
        self.btn_diag.pack(side="left",padx=4)

        # Page table
        tf = ttk.LabelFrame(self.root,text=" Tag Memory Pages ")
        tf.pack(fill="x",padx=10,pady=4)

        cols = ("pg","desc","b3","b2","b1","b0","lock")
        self.tree = ttk.Treeview(tf,columns=cols,show="headings",height=8)
        for c,w,t in [("pg",40,"Page"),("desc",275,"Description"),
                      ("b3",55,"Byte3"),("b2",55,"Byte2"),
                      ("b1",55,"Byte1"),("b0",55,"Byte0"),("lock",70,"Lock")]:
            self.tree.heading(c,text=t)
            self.tree.column(c,width=w,anchor="center" if c!="desc" else "w")
        self.tree.tag_configure("locked",  background="#7c3aed",foreground="white")
        self.tree.tag_configure("open",    background="#065f46",foreground="white")
        self.tree.tag_configure("empty",   background="#1e293b",foreground="#475569")
        self.tree.pack(fill="x",padx=4,pady=4)
        for i,lbl in enumerate(MRD2Reader.PAGE_LABELS):
            self.tree.insert("","end",iid=str(i),
                             values=(i+1,lbl,"--","--","--","--","—"),
                             tags=("empty",))

        # Log
        lf = ttk.LabelFrame(self.root,text=" Activity Log ")
        lf.pack(fill="both",expand=True,padx=10,pady=(4,8))
        self.log = scrolledtext.ScrolledText(lf,height=7,font=("Consolas",8),
                                             bg="#0f172a",fg="#94a3b8",
                                             insertbackground="white",state="disabled")
        self.log.pack(fill="both",expand=True,padx=4,pady=4)

    # ── Helpers ────────────────────────────────────────────────
    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")

    def _controls(self, state):
        for w in [self.btn_readuid,self.chk_poll,self.btn_pages,
                  self.btn_ver,self.btn_diag]:
            w.config(state=state)

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if "COM17" in ports: self.port_var.set("COM17")
        elif ports: self.port_var.set(ports[0])
        self._log(f"Ports: {', '.join(ports) or 'none'}")

    def _set_uid(self, uid_hex, animal_id):
        self.lbl_uid.config(text=" ".join(uid_hex[i:i+2] for i in range(0,16,2)),
                            fg="#22c55e")
        self.lbl_aid.config(text=f"Animal ID (ISO 11784): {animal_id}")

    def _clear_uid(self, msg="NO TAG"):
        self.lbl_uid.config(text=msg, fg="#64748b")
        self.lbl_aid.config(text="Animal ID (ISO 11784): —")

    # ── Connection ─────────────────────────────────────────────
    def _toggle_conn(self):
        if not self.reader.ser or not self.reader.ser.is_open:
            self.reader.port     = self.port_var.get()
            self.reader.baudrate = int(self.baud_var.get())
            res = self.reader.connect()
            if res is True:
                self._log(f"Connected {self.reader.port} @ {self.reader.baudrate}")
                self.btn_conn.config(text="Disconnect")
                self.lbl_st.config(text="● ONLINE", fg="#22c55e")
                self._controls("normal")
                self._version()
            else:
                self._log(f"Failed: {res}")
                messagebox.showerror("Error", res)
        else:
            self.polling = False
            self.poll_var.set(False)
            self.reader.disconnect()
            self._log("Disconnected.")
            self.btn_conn.config(text="Connect")
            self.lbl_st.config(text="● OFFLINE", fg="#ef4444")
            self._controls("disabled")
            self._clear_uid("OFFLINE")

    def _version(self):
        v = self.reader.get_version()
        if v:
            self._log(f"Firmware: {v}")
            self.lbl_st.config(text=f"● ONLINE v{v}", fg="#22c55e")
        else:
            self._log("Version: no response (reader still functional).")

    # ── Read UID ───────────────────────────────────────────────
    def _read_uid(self):
        threading.Thread(target=self._uid_thread, daemon=True).start()

    def _uid_thread(self):
        self.root.after(0, lambda: self._log("Reading UID via page reads..."))
        result = self.reader.read_uid()
        self.root.after(0, lambda: self._handle_uid(result))

    def _handle_uid(self, result):
        if result:
            self._set_uid(result["uid_hex"], result["animal_id"])
            p1 = result["page1"]
            p2 = result["page2"]
            p3 = result["page3"]
            self._log(f"UID: {result['uid_hex']}  Animal ID: {result['animal_id']}")
            self._log(f"Page1: {' '.join(f'{b:02X}' for b in p1) if p1 else 'N/A'}")
            self._log(f"Page2: {' '.join(f'{b:02X}' for b in p2) if p2 else 'N/A'}")
            self._log(f"Page3: {' '.join(f'{b:02X}' for b in p3) if p3 else 'N/A'}")
        else:
            self._clear_uid("NO TAG")
            self._log("No tag — place tag on antenna and try again.")

    # ── Poll ───────────────────────────────────────────────────
    def _toggle_poll(self):
        if self.poll_var.get():
            self.polling = True
            self._log("Auto-polling started (100ms, page-read method).")
            threading.Thread(target=self._poll_loop, daemon=True).start()
        else:
            self.polling = False
            self._log("Polling stopped.")

    def _poll_loop(self):
        last_uid = None
        while self.polling:
            result = self.reader.read_uid()
            if result:
                if result["uid_hex"] != last_uid:
                    last_uid = result["uid_hex"]
                    self.root.after(0, lambda r=result: self._handle_uid(r))
            else:
                if last_uid is not None:
                    last_uid = None
                    self.root.after(0, lambda: self._clear_uid("NO TAG"))
            time.sleep(0.1)

    # ── All Pages ──────────────────────────────────────────────
    def _all_pages(self):
        threading.Thread(target=self._pages_thread, daemon=True).start()

    def _pages_thread(self):
        self.root.after(0, lambda: self._log("Reading all 16 pages..."))
        pages = self.reader.read_all_pages()
        self.root.after(0, lambda: self._update_table(pages))

    def _update_table(self, pages):
        for i, d in enumerate(pages):
            if d and len(d) >= 4:
                locked = (i < 4 or i >= 14)
                tag    = "locked" if locked else "open"
                lock_t = "Locked" if locked else "Open"
                self.tree.item(str(i), values=(
                    i+1, MRD2Reader.PAGE_LABELS[i],
                    f"{d[0]:02X}",f"{d[1]:02X}",f"{d[2]:02X}",f"{d[3]:02X}", lock_t
                ), tags=(tag,))
                self._log(f"  Pg{i+1:2d}: {d[0]:02X} {d[1]:02X} {d[2]:02X} {d[3]:02X}  {MRD2Reader.PAGE_LABELS[i]}")
            else:
                self.tree.item(str(i),
                               values=(i+1,MRD2Reader.PAGE_LABELS[i],"??","??","??","??","N/A"),
                               tags=("empty",))

    # ── Diagnose ───────────────────────────────────────────────
    def _diagnose(self):
        self._log("=== DIAGNOSTICS ===")
        self._log("Sending CMD 0x00 (Single Read, raw)...")
        hex_str, d = self.reader.single_read_raw()
        if hex_str:
            self._log(f"  RX Raw: {hex_str}")
            if d and d != "BCC_ERR":
                self._log(f"  Status: 0x{d[0]:02X} | Data: {[hex(b) for b in d[1:]]}")
            else:
                self._log(f"  Parse result: {d}")
        else:
            self._log("  No response from CMD 0x00.")

        self._log("Testing Read Page 1...")
        p1 = self.reader.read_page(1)
        if p1:
            self._log(f"  Page 1 OK: {' '.join(f'{b:02X}' for b in p1)}")
        else:
            self._log("  Page 1: No response or error.")
        self._log("===================")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
