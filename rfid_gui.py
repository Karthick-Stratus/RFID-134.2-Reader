import serial
import serial.tools.list_ports
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ============================================================
# TI RI-STU-MRD2 LMP Protocol (from TI Microreader II manual)
# ============================================================
# Packet:  [SOH=0x01] [LEN] [CMD/DATA...] [BCC=XOR of LEN..DATA]
#
# Commands:
#   0x00 = Single Read (Identify Tag)
#   0x01 = Continuous Read
#   0x03 = Get Firmware Version
#
# Read Tag Success Response (10-byte data):
#   [0x00=Status OK] [0x00=Tag Type] [8-byte UID] BCC
#
# Read Page Command:
#   01 04 80 03 03 [page] [BCC]
#   BCC = 0x04^0x80^0x03^0x03^page
#
# Read Page Success Response (10-byte data):
#   [0x00=Status] [0x00] [Byte3][Byte2][Byte1][Byte0] [?][?][?][?] BCC
#
# Status Codes:
#   0x00 = Success
#   0x03 = No Tag Detected
#   0x07 = Other/Noise (discard)
# ============================================================

class MRD2Reader:
    SOH = 0x01
    CMD_SINGLE_READ    = 0x00
    CMD_CONT_READ      = 0x01
    CMD_GET_VERSION    = 0x03

    def __init__(self, port=None, baudrate=9600, timeout=0.5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            return True
        except Exception as e:
            return str(e)

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _bcc(self, data):
        r = 0
        for b in data: r ^= b
        return r

    def _send_raw(self, payload_bytes):
        """Send raw payload (list of ints), auto-wrap in SOH+LEN+BCC."""
        if not self.ser or not self.ser.is_open:
            return None
        bcc = self._bcc(payload_bytes)
        pkt = bytearray([self.SOH] + payload_bytes + [bcc])
        self.ser.reset_input_buffer()
        self.ser.write(pkt)
        return self.ser.read(32)

    def _parse(self, raw):
        """Parse raw bytes into data list, or return None/error string."""
        if not raw or len(raw) < 4:
            return None
        if raw[0] != self.SOH:
            return None
        length = raw[1]
        if len(raw) < length + 3:
            return None
        data = raw[2:2 + length]
        bcc = raw[2 + length]
        if self._bcc([length] + list(data)) != bcc:
            return "BCC_ERROR"
        return list(data)

    def get_version(self):
        raw = self._send_raw([0x01, self.CMD_GET_VERSION])
        d = self._parse(raw)
        if d and d != "BCC_ERROR":
            return ".".join(str(b) for b in d)
        return None

    def single_read(self):
        """
        Single Read. Returns dict on success, None on no tag, 'NOISE' on noise.
        Success response (data): [0x00, 0x00, uid0..uid7]
        """
        raw = self._send_raw([0x01, self.CMD_SINGLE_READ])
        if not raw:
            return None
        d = self._parse(raw)
        if not d or d == "BCC_ERROR":
            return None
        status = d[0]
        if status == 0x03:
            return None  # No tag
        if status == 0x07:
            return "NOISE"  # Electrical noise
        if status == 0x00 and len(d) >= 10:
            uid_raw = d[2:10]   # 8 bytes, order: Byte3,2,1,0, Byte7,6,5,4
            return {
                "raw_data": d,
                "uid_raw": uid_raw,
                "status": status,
            }
        return None

    def read_page(self, page_num):
        """
        Read a specific memory page (1-16).
        Command: 01 04 80 03 03 [page] [BCC]
        Returns list of 4 data bytes [Byte3, Byte2, Byte1, Byte0] or None.
        """
        payload = [0x04, 0x80, 0x03, 0x03, page_num]
        raw = self._send_raw(payload)
        if not raw:
            return None
        d = self._parse(raw)
        if not d or d == "BCC_ERROR":
            return None
        status = d[0]
        if status == 0x00 and len(d) >= 6:
            return d[2:6]  # [Byte3, Byte2, Byte1, Byte0]
        return None

    def read_all_pages(self):
        """Read all 16 pages. Returns list of 16 entries (each is 4 bytes or None)."""
        pages = []
        for p in range(1, 17):
            data = self.read_page(p)
            pages.append(data)
            time.sleep(0.05)
        return pages

    @staticmethod
    def parse_uid(uid_raw):
        """
        uid_raw = [Byte3,Byte2,Byte1,Byte0 of ID, Byte7,Byte6,Byte5,Byte4 of ID]
        Returns full 8-byte UID as hex string (MSB first: Byte7..Byte0)
        and decimal Animal ID per ISO 11784.
        """
        if len(uid_raw) < 8:
            return None, None
        # Rearrange to Byte7..Byte0
        uid_bytes = [
            uid_raw[4], uid_raw[5], uid_raw[6], uid_raw[7],
            uid_raw[0], uid_raw[1], uid_raw[2], uid_raw[3]
        ]
        uid_hex = "".join(f"{b:02X}" for b in uid_bytes)
        # Animal ID = lower 38 bits of 64-bit value
        val = int.from_bytes(uid_bytes, "big")
        animal_id = val & 0x3FFFFFFFFF
        return uid_hex, animal_id


class RFIDApp:
    PAGE_DESCRIPTIONS = [
        "Chip ID Byte 3,2,1,0",
        "Reserved & Chip ID Byte 6,5,4",
        "Reserved & Chip ID Byte 9,8,7",
        "Config Byte 2,1 & CRC MSB,LSB",
        "User Memory", "User Memory", "User Memory", "User Memory",
        "User Memory", "User Memory", "User Memory", "User Memory",
        "User Memory", "User Memory",
        "Animal ID Byte 3,2,1,0",
        "Animal ID Byte 7,6,5,4",
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Stratus RFID Reader — TI RI-STU-MRD2")
        self.root.geometry("780x680")
        self.root.configure(bg="#1e293b")

        self.reader = MRD2Reader()
        self.polling = False
        self.poll_thread = None

        self._build_ui()
        self._refresh_ports()

    # ── UI Construction ────────────────────────────────────────
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=4)
        style.configure("Header.TLabel", font=("Segoe UI", 10, "bold"),
                        background="#1e293b", foreground="#94a3b8")
        style.configure("TLabelframe", background="#1e293b", foreground="#94a3b8")
        style.configure("TLabelframe.Label", background="#1e293b",
                        foreground="#38bdf8", font=("Segoe UI", 9, "bold"))

        # ── Top bar ────────────────────────────────────────────
        top = tk.Frame(self.root, bg="#0f172a", pady=8)
        top.pack(fill="x")

        tk.Label(top, text="TI RI-STU-MRD2  RFID Reader",
                 font=("Segoe UI", 14, "bold"), bg="#0f172a", fg="#38bdf8").pack(side="left", padx=15)
        tk.Label(top, text="134.2 kHz HDX/FDX",
                 font=("Segoe UI", 9), bg="#0f172a", fg="#64748b").pack(side="left")

        # ── Connection Frame ───────────────────────────────────
        cf = tk.Frame(self.root, bg="#1e293b")
        cf.pack(fill="x", padx=12, pady=(8, 4))

        tk.Label(cf, text="Port:", bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(cf, textvariable=self.port_var, width=10)
        self.port_combo.grid(row=0, column=1, padx=4)

        ttk.Button(cf, text="⟳", width=3, command=self._refresh_ports).grid(row=0, column=2)

        tk.Label(cf, text="Baud:", bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 9)).grid(row=0, column=3, padx=(10, 2), sticky="w")
        self.baud_var = tk.StringVar(value="9600")
        ttk.Combobox(cf, textvariable=self.baud_var, width=9,
                     values=["9600","19200","38400","57600","115200"]
                     ).grid(row=0, column=4, padx=4)

        self.btn_conn = ttk.Button(cf, text="Connect", command=self._toggle_connection, width=12)
        self.btn_conn.grid(row=0, column=5, padx=8)

        self.lbl_status = tk.Label(cf, text="● OFFLINE", fg="#ef4444",
                                   bg="#1e293b", font=("Segoe UI", 9, "bold"))
        self.lbl_status.grid(row=0, column=6, padx=6)

        self.btn_ver = ttk.Button(cf, text="Get Version", command=self._get_version, state="disabled")
        self.btn_ver.grid(row=0, column=7, padx=4)

        # ── UID Display ────────────────────────────────────────
        uid_f = tk.Frame(self.root, bg="#0f172a", pady=10)
        uid_f.pack(fill="x", padx=12, pady=4)

        tk.Label(uid_f, text="LAST DETECTED UID", font=("Segoe UI", 8, "bold"),
                 bg="#0f172a", fg="#64748b").pack()
        self.lbl_uid = tk.Label(uid_f, text="— WAITING —",
                                font=("Consolas", 22, "bold"), bg="#0f172a", fg="#38bdf8")
        self.lbl_uid.pack()
        self.lbl_animal = tk.Label(uid_f, text="Animal ID (Dec): —",
                                   font=("Segoe UI", 9), bg="#0f172a", fg="#94a3b8")
        self.lbl_animal.pack()

        # ── Controls ───────────────────────────────────────────
        ctrl = tk.Frame(self.root, bg="#1e293b")
        ctrl.pack(fill="x", padx=12, pady=4)

        self.btn_read = ttk.Button(ctrl, text="▶ Single Read", command=self._single_read,
                                   state="disabled", width=14)
        self.btn_read.pack(side="left", padx=4)

        self.poll_var = tk.BooleanVar(value=False)
        self.chk_poll = ttk.Checkbutton(ctrl, text="Auto Poll", variable=self.poll_var,
                                        command=self._toggle_poll, state="disabled")
        self.chk_poll.pack(side="left", padx=6)

        self.btn_pages = ttk.Button(ctrl, text="📄 Read All Pages",
                                    command=self._read_all_pages, state="disabled", width=16)
        self.btn_pages.pack(side="left", padx=4)

        self.noise_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="Filter Noise", variable=self.noise_var).pack(side="right", padx=6)

        # ── Page Memory Table ──────────────────────────────────
        pg_frame = ttk.LabelFrame(self.root, text=" Tag Memory Pages ")
        pg_frame.pack(fill="x", padx=12, pady=4)

        cols = ("page", "description", "byte3", "byte2", "byte1", "byte0", "status")
        self.page_tree = ttk.Treeview(pg_frame, columns=cols, show="headings", height=8)
        self.page_tree.heading("page",        text="Page")
        self.page_tree.heading("description", text="Description")
        self.page_tree.heading("byte3",       text="Byte3")
        self.page_tree.heading("byte2",       text="Byte2")
        self.page_tree.heading("byte1",       text="Byte1")
        self.page_tree.heading("byte0",       text="Byte0")
        self.page_tree.heading("status",      text="Lock")

        self.page_tree.column("page",        width=40,  anchor="center")
        self.page_tree.column("description", width=270, anchor="w")
        self.page_tree.column("byte3",       width=55,  anchor="center")
        self.page_tree.column("byte2",       width=55,  anchor="center")
        self.page_tree.column("byte1",       width=55,  anchor="center")
        self.page_tree.column("byte0",       width=55,  anchor="center")
        self.page_tree.column("status",      width=80,  anchor="center")

        self.page_tree.tag_configure("locked",   background="#7c3aed", foreground="white")
        self.page_tree.tag_configure("unlocked", background="#065f46", foreground="white")
        self.page_tree.tag_configure("empty",    background="#1e293b", foreground="#64748b")

        self.page_tree.pack(fill="x", pady=4, padx=4)
        self._init_page_table()

        # ── Log ────────────────────────────────────────────────
        log_f = ttk.LabelFrame(self.root, text=" Activity Log ")
        log_f.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        self.log_box = scrolledtext.ScrolledText(log_f, height=6,
                                                 font=("Consolas", 8),
                                                 bg="#0f172a", fg="#94a3b8",
                                                 insertbackground="white", state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=4, pady=4)

    def _init_page_table(self):
        for i, desc in enumerate(self.PAGE_DESCRIPTIONS):
            self.page_tree.insert("", "end", iid=str(i),
                                  values=(i + 1, desc, "--", "--", "--", "--", "—"),
                                  tags=("empty",))

    # ── Helpers ────────────────────────────────────────────────
    def _log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

    def _set_status(self, text, color):
        self.lbl_status.config(text=text, fg=color)

    def _enable_controls(self, en):
        state = "normal" if en else "disabled"
        for w in [self.btn_read, self.chk_poll, self.btn_pages, self.btn_ver]:
            w.config(state=state)

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if "COM17" in ports:
            self.port_var.set("COM17")
        elif ports:
            self.port_var.set(ports[0])
        self._log(f"Found {len(ports)} port(s): {', '.join(ports) or 'none'}")

    # ── Connection ─────────────────────────────────────────────
    def _toggle_connection(self):
        if not self.reader.ser or not self.reader.ser.is_open:
            self.reader.port = self.port_var.get()
            self.reader.baudrate = int(self.baud_var.get())
            res = self.reader.connect()
            if res is True:
                self._log(f"Connected to {self.reader.port} @ {self.reader.baudrate} baud.")
                self.btn_conn.config(text="Disconnect")
                self._set_status("● ONLINE", "#22c55e")
                self._enable_controls(True)
                self._get_version()
            else:
                self._log(f"Connection failed: {res}")
                messagebox.showerror("Error", res)
        else:
            self.polling = False
            self.poll_var.set(False)
            self.reader.disconnect()
            self._log("Disconnected.")
            self.btn_conn.config(text="Connect")
            self._set_status("● OFFLINE", "#ef4444")
            self._enable_controls(False)
            self.lbl_uid.config(text="— OFFLINE —", fg="#64748b")

    # ── Commands ───────────────────────────────────────────────
    def _get_version(self):
        ver = self.reader.get_version()
        if ver:
            self._log(f"Firmware Version: {ver}")
            self._set_status(f"● ONLINE  v{ver}", "#22c55e")
        else:
            self._log("No firmware version response (reader may still work).")

    def _single_read(self):
        result = self.reader.single_read()
        self._handle_read_result(result)

    def _handle_read_result(self, result):
        if result is None:
            self._log("No tag detected.")
            self.lbl_uid.config(text="NO TAG", fg="#64748b")
            self.lbl_animal.config(text="Animal ID (Dec): —")
        elif result == "NOISE":
            if not self.noise_var.get():
                self._log("Noise/Other detected — filtered.")
            self.lbl_uid.config(text="NOISE", fg="#f59e0b")
        elif isinstance(result, dict):
            uid_hex, animal_id = self.reader.parse_uid(result["uid_raw"])
            raw_hex = " ".join(f"{b:02X}" for b in result["raw_data"])
            self._log(f"Tag UID: {uid_hex}  |  Animal ID: {animal_id}  |  Raw: {raw_hex}")
            self.lbl_uid.config(text=uid_hex, fg="#38bdf8")
            self.lbl_animal.config(text=f"Animal ID (Dec): {animal_id}")

    def _read_all_pages(self):
        self._log("Reading all 16 pages...")
        # Run in thread to keep UI responsive
        threading.Thread(target=self._page_read_thread, daemon=True).start()

    def _page_read_thread(self):
        pages = self.reader.read_all_pages()
        self.root.after(0, lambda: self._update_page_table(pages))

    def _update_page_table(self, pages):
        for i, data in enumerate(pages):
            if data:
                b3, b2, b1, b0 = data
                # Locked pages are non-user pages (1-4, 15-16 are locked in the screenshot)
                locked = i < 4 or i >= 14
                tag = "locked" if locked else "unlocked"
                lock_text = "Locked" if locked else "Open"
                self.page_tree.item(str(i), values=(
                    i + 1, self.PAGE_DESCRIPTIONS[i],
                    f"{b3:02X}", f"{b2:02X}", f"{b1:02X}", f"{b0:02X}",
                    lock_text
                ), tags=(tag,))
                self._log(f"Page {i+1:2d}: {b3:02X} {b2:02X} {b1:02X} {b0:02X}  — {self.PAGE_DESCRIPTIONS[i]}")
            else:
                self.page_tree.item(str(i), values=(
                    i + 1, self.PAGE_DESCRIPTIONS[i], "??", "??", "??", "??", "N/A"
                ), tags=("empty",))

    # ── Polling ────────────────────────────────────────────────
    def _toggle_poll(self):
        if self.poll_var.get():
            self.polling = True
            self._log("Auto-polling started (0.5s interval).")
            self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.poll_thread.start()
        else:
            self.polling = False
            self._log("Auto-polling stopped.")

    def _poll_loop(self):
        while self.polling:
            result = self.reader.single_read()
            self.root.after(0, lambda r=result: self._handle_read_result(r))
            time.sleep(0.5)


if __name__ == "__main__":
    root = tk.Tk()
    app = RFIDApp(root)
    root.mainloop()
