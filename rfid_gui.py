import serial, serial.tools.list_ports, threading, time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# =====================================================
# TI RI-STU-MRD2 — ECM Protocol (Easy Code Mode)
# Confirmed from RI-STU-MRD2.md datasheet (SCBU049)
#
# ECM Frame: 01 [LEN] 0x80 [DevCode] [DevCmd] [params] [BCC]
# BCC = XOR of all bytes after SOH (LEN onwards)
#
# Device Code 0x03 = HDX+ (TMS37190)
#
# Key ECM Commands for HDX+:
#   0x00 = Charge-only Read   TX: 01 03 80 03 00 80
#   0x01 = General Read       TX: 01 03 80 03 01 81
#   0x03 = Read Multi Block   TX: 01 04 80 03 03 [blk] [BCC]
#   0x05 = Read UID           TX: 01 03 80 03 05 85
#   0x06 = Read Configuration TX: 01 03 80 03 06 86
#
# Charge-only = fast UID (RO/RW), 50ms charge burst
# General Read = full memory dump including Animal ID
# Poll interval: 80ms (HDX cycle = 50ms charge + 20ms listen + overhead)
#
# STATUS BYTE (LMP Table 12):
#   bits[1:0] = 00 → RO tag     bits[1:0] = 01 → R/W tag
#   bits[1:0] = 10 → MPT/SAMPT  bits[1:0] = 11 → Other/Noise
#   bit 5 = 1 → S/W version follows
#   Status 0x03 = No Tag
# =====================================================

ECM_DEV_HDX = 0x03

class MRD2:
    SOH = 0x01

    def __init__(self, port=None, baud=9600, timeout=0.3):
        self.port    = port
        self.baud    = baud
        self.timeout = timeout
        self.ser     = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
            return True
        except Exception as e:
            return str(e)

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    @staticmethod
    def _bcc(data):
        v = 0
        for b in data: v ^= b
        return v

    def _cmd(self, payload):
        """Send [SOH]+payload+[BCC], return raw bytes."""
        if not self.ser or not self.ser.is_open:
            return None
        bcc = self._bcc(payload)
        pkt = bytearray([self.SOH] + payload + [bcc])
        self.ser.reset_input_buffer()
        self.ser.write(pkt)
        return self.ser.read(64)

    def _parse(self, raw):
        """Returns data bytes list, 'BCC_ERR', or None."""
        if not raw or len(raw) < 4 or raw[0] != self.SOH:
            return None
        ln = raw[1]
        if len(raw) < ln + 3:
            return None
        data = list(raw[2:2+ln])
        if self._bcc([ln] + data) != raw[2+ln]:
            return "BCC_ERR"
        return data

    # ── ECM Commands ─────────────────────────────────
    def get_version(self):
        """Setup Mode: Get firmware version. CMD1=0x83 CMD2=0x00"""
        raw = self._cmd([0x02, 0x83, 0x00])
        d   = self._parse(raw)
        if d and d != "BCC_ERR" and len(d) >= 1:
            return f"v{d[0] >> 4}.{d[0] & 0x0F}"
        return None

    def charge_read(self):
        """ECM Charge-only Read — fastest UID. Returns (status, uid_hex) or None."""
        raw = self._cmd([0x03, 0x80, ECM_DEV_HDX, 0x00])
        d   = self._parse(raw)
        if not d or d == "BCC_ERR":
            return None
        status = d[0]
        if status == 0x03:          # No tag
            return None
        tag_type = status & 0x03    # bits 0,1: 00=RO 01=RW 10=MPT 11=Other
        if tag_type == 0x03:        # noise
            return None
        uid_raw = d[1:9] if len(d) >= 9 else []
        if not uid_raw:
            return None
        uid_hex = "".join(f"{b:02X}" for b in reversed(uid_raw))
        return status, uid_hex

    def general_read(self):
        """ECM General Read — returns all memory blocks for HDX+."""
        raw = self._cmd([0x03, 0x80, ECM_DEV_HDX, 0x01])
        d   = self._parse(raw)
        if not d or d == "BCC_ERR":
            return None, None, None
        status = d[0]
        s2     = d[1] if len(d) > 1 else 0
        return status, s2, d[2:]   # status1, status2, data bytes

    def read_uid(self):
        """ECM Read UID command — HDX+ specific."""
        raw = self._cmd([0x03, 0x80, ECM_DEV_HDX, 0x05])
        d   = self._parse(raw)
        if not d or d == "BCC_ERR":
            return None
        status = d[0]
        if status == 0x03 or (status & 0x03) == 0x03:
            return None
        uid_raw = d[2:10] if len(d) >= 10 else d[1:9]
        if not uid_raw:
            return None
        return "".join(f"{b:02X}" for b in reversed(uid_raw))

    def read_block(self, block_num):
        """ECM Read Multi Block — single block."""
        raw = self._cmd([0x04, 0x80, ECM_DEV_HDX, 0x03, block_num])
        d   = self._parse(raw)
        if not d or d == "BCC_ERR" or d[0] == 0x03:
            return None
        return d[2:6] if len(d) >= 6 else None

    def read_all_blocks(self, count=16):
        result = []
        for i in range(count):
            result.append(self.read_block(i))
            time.sleep(0.02)
        return result


# ── GUI ────────────────────────────────────────────

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

class App:
    def __init__(self, root):
        self.root    = root
        self.root.title("Stratus RFID — TI RI-STU-MRD2  |  ECM Protocol")
        self.root.geometry("820x720")
        self.root.configure(bg="#0f172a")
        self.mrd     = MRD2()
        self.polling = False
        self._build()
        self._refresh_ports()

    def _build(self):
        S = ttk.Style(); S.theme_use("clam")
        S.configure("TLabelframe",       background="#1e293b", foreground="#94a3b8")
        S.configure("TLabelframe.Label", background="#1e293b",
                    foreground="#38bdf8", font=("Segoe UI",9,"bold"))
        S.configure("TButton", font=("Segoe UI",9,"bold"), padding=4)
        S.configure("Treeview", background="#1e293b", foreground="#e2e8f0",
                    fieldbackground="#1e293b", rowheight=22)
        S.configure("Treeview.Heading", background="#0f172a", foreground="#38bdf8",
                    font=("Segoe UI",9,"bold"))

        # Header
        h = tk.Frame(self.root, bg="#0f172a", pady=8)
        h.pack(fill="x")
        tk.Label(h, text="TI RI-STU-MRD2  RFID Reader",
                 font=("Segoe UI",15,"bold"), bg="#0f172a", fg="#38bdf8").pack(side="left", padx=14)
        tk.Label(h, text="134.2 kHz | HDX+/FDX | ECM Protocol",
                 font=("Segoe UI",9), bg="#0f172a", fg="#64748b").pack(side="left")

        # Connection bar
        cb = tk.Frame(self.root, bg="#1e293b", pady=5, padx=8)
        cb.pack(fill="x")
        tk.Label(cb,text="Port:",bg="#1e293b",fg="#94a3b8",
                 font=("Segoe UI",9)).grid(row=0,column=0,sticky="w")
        self.port_var = tk.StringVar()
        self.port_cb  = ttk.Combobox(cb, textvariable=self.port_var, width=9)
        self.port_cb.grid(row=0,column=1,padx=3)
        ttk.Button(cb,text="⟳",width=3,
                   command=self._refresh_ports).grid(row=0,column=2)
        tk.Label(cb,text="Baud:",bg="#1e293b",fg="#94a3b8",
                 font=("Segoe UI",9)).grid(row=0,column=3,padx=(8,2))
        self.baud_var = tk.StringVar(value="9600")
        ttk.Combobox(cb, textvariable=self.baud_var, width=8,
                     values=["9600","19200","38400","57600","115200"]
                     ).grid(row=0,column=4,padx=3)
        self.btn_conn = ttk.Button(cb,text="Connect",
                                   command=self._toggle_conn, width=11)
        self.btn_conn.grid(row=0,column=5,padx=6)
        self.lbl_st = tk.Label(cb,text="● OFFLINE",fg="#ef4444",
                               bg="#1e293b",font=("Segoe UI",9,"bold"))
        self.lbl_st.grid(row=0,column=6,padx=4)
        self.btn_ver = ttk.Button(cb,text="Version",
                                  command=self._get_ver,state="disabled",width=8)
        self.btn_ver.grid(row=0,column=7,padx=4)

        # UID display
        uf = tk.Frame(self.root, bg="#0f172a", pady=10)
        uf.pack(fill="x")
        tk.Label(uf,text="CHIP UID  (64-bit TIRIS)",
                 font=("Segoe UI",8,"bold"),bg="#0f172a",fg="#64748b").pack()
        self.lbl_uid = tk.Label(uf,text="—  —  —  —  —  —  —  —",
                                font=("Consolas",22,"bold"),bg="#0f172a",fg="#38bdf8")
        self.lbl_uid.pack()
        self.lbl_aid = tk.Label(uf,text="Animal ID (ISO 11784): —",
                                font=("Segoe UI",10),bg="#0f172a",fg="#94a3b8")
        self.lbl_aid.pack()
        self.lbl_type = tk.Label(uf,text="Tag Type: —",
                                 font=("Segoe UI",9),bg="#0f172a",fg="#64748b")
        self.lbl_type.pack()

        # Controls
        ctrl = tk.Frame(self.root,bg="#0f172a",pady=4)
        ctrl.pack(fill="x",padx=10)

        self.btn_cread  = ttk.Button(ctrl,text="▶ Charge Read (Fast)",
                                     command=self._charge_read,state="disabled",width=20)
        self.btn_cread.pack(side="left",padx=3)

        self.btn_uid    = ttk.Button(ctrl,text="🔑 Read UID",
                                     command=self._read_uid_cmd,state="disabled",width=12)
        self.btn_uid.pack(side="left",padx=3)

        self.poll_var   = tk.BooleanVar(value=False)
        self.chk_poll   = ttk.Checkbutton(ctrl,text="Auto Poll (80ms)",
                                          variable=self.poll_var,
                                          command=self._toggle_poll,state="disabled")
        self.chk_poll.pack(side="left",padx=6)

        self.btn_pages  = ttk.Button(ctrl,text="📄 All Blocks",
                                     command=self._all_blocks,state="disabled",width=12)
        self.btn_pages.pack(side="left",padx=3)

        self.btn_clear  = ttk.Button(ctrl,text="🗑 Clear",
                                     command=self._clear,width=8)
        self.btn_clear.pack(side="right",padx=3)

        self.btn_genread = ttk.Button(ctrl,text="📋 General Read",
                                      command=self._gen_read,state="disabled",width=14)
        self.btn_genread.pack(side="left",padx=3)

        # Page/Block table
        tf = ttk.LabelFrame(self.root,text=" Tag Memory Blocks (16 × 4 bytes) ")
        tf.pack(fill="x",padx=10,pady=4)
        cols = ("blk","desc","b3","b2","b1","b0","lock")
        self.tree = ttk.Treeview(tf,columns=cols,show="headings",height=8)
        for c,w,t in [("blk",40,"Block"),("desc",270,"Description"),
                      ("b3",55,"Byte3"),("b2",55,"Byte2"),
                      ("b1",55,"Byte1"),("b0",55,"Byte0"),("lock",72,"Status")]:
            self.tree.heading(c,text=t)
            self.tree.column(c,width=w,anchor="center" if c!="desc" else "w")
        self.tree.tag_configure("locked", background="#7c3aed",foreground="white")
        self.tree.tag_configure("open",   background="#065f46",foreground="white")
        self.tree.tag_configure("empty",  background="#1e293b",foreground="#475569")
        self.tree.pack(fill="x",padx=4,pady=4)
        for i,lbl in enumerate(PAGE_LABELS):
            self.tree.insert("","end",iid=str(i),
                             values=(i,lbl,"--","--","--","--","—"),
                             tags=("empty",))

        # Log
        lf = ttk.LabelFrame(self.root,text=" Activity Log ")
        lf.pack(fill="both",expand=True,padx=10,pady=(4,8))

        logctrl = tk.Frame(lf, bg="#1e293b")
        logctrl.pack(fill="x", padx=4, pady=(2,0))
        ttk.Button(logctrl,text="Clear Log",
                   command=self._clear_log,width=10).pack(side="right")

        self.log = scrolledtext.ScrolledText(lf,height=7,font=("Consolas",8),
                                             bg="#0f172a",fg="#94a3b8",
                                             insertbackground="white",state="disabled")
        self.log.pack(fill="both",expand=True,padx=4,pady=4)

    # ── Helpers ──────────────────────────────────────
    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert(tk.END,f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")

    def _controls(self, en):
        s = "normal" if en else "disabled"
        for w in [self.btn_cread,self.btn_uid,self.chk_poll,
                  self.btn_pages,self.btn_genread,self.btn_ver]:
            w.config(state=s)

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if "COM17" in ports: self.port_var.set("COM17")
        elif ports: self.port_var.set(ports[0])
        self._log(f"Ports detected: {', '.join(ports) or 'none'}")

    def _show_uid(self, uid_hex, tag_type_str="", animal_id=None):
        spaced = " ".join(uid_hex[i:i+2] for i in range(0,16,2))
        self.lbl_uid.config(text=spaced, fg="#22c55e")
        if animal_id is not None:
            self.lbl_aid.config(text=f"Animal ID (ISO 11784): {animal_id}")
        if tag_type_str:
            self.lbl_type.config(text=f"Tag Type: {tag_type_str}")

    def _clear(self):
        self.lbl_uid.config(text="—  —  —  —  —  —  —  —", fg="#38bdf8")
        self.lbl_aid.config(text="Animal ID (ISO 11784): —")
        self.lbl_type.config(text="Tag Type: —")
        for i in range(16):
            self.tree.item(str(i),
                           values=(i, PAGE_LABELS[i],"--","--","--","--","—"),
                           tags=("empty",))

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0","end")
        self.log.config(state="disabled")

    @staticmethod
    def _decode_status(s):
        t = s & 0x03
        return {0:"RO Tag",1:"R/W Tag",2:"MPT/SAMPT",3:"Other/Noise"}.get(t,"?")

    @staticmethod
    def _animal_id(uid_hex):
        val = int(uid_hex,16)
        return val & 0x3FFFFFFFFF

    # ── Connection ───────────────────────────────────
    def _toggle_conn(self):
        if not self.mrd.ser or not self.mrd.ser.is_open:
            self.mrd.port = self.port_var.get()
            self.mrd.baud = int(self.baud_var.get())
            res = self.mrd.connect()
            if res is True:
                self._log(f"Connected: {self.mrd.port} @ {self.mrd.baud} baud")
                self.btn_conn.config(text="Disconnect")
                self.lbl_st.config(text="● ONLINE",fg="#22c55e")
                self._controls(True)
                self._get_ver()
            else:
                self._log(f"Error: {res}")
                messagebox.showerror("Error",res)
        else:
            self.polling = False; self.poll_var.set(False)
            self.mrd.disconnect()
            self._log("Disconnected.")
            self.btn_conn.config(text="Connect")
            self.lbl_st.config(text="● OFFLINE",fg="#ef4444")
            self._controls(False)
            self._clear()

    def _get_ver(self):
        v = self.mrd.get_version()
        if v:
            self._log(f"Firmware: {v}")
            self.lbl_st.config(text=f"● ONLINE {v}",fg="#22c55e")
        else:
            self._log("Version query: no response (try ECM commands below).")

    # ── Reads ─────────────────────────────────────────
    def _charge_read(self):
        result = self.mrd.charge_read()
        if result:
            status, uid = result
            animal_id   = self._animal_id(uid)
            tag_type    = self._decode_status(status)
            self._show_uid(uid, tag_type, animal_id)
            self._log(f"Charge Read OK | UID: {uid} | Type: {tag_type} | Animal ID: {animal_id}")
        else:
            self._log("Charge Read: No tag detected.")
            self.lbl_uid.config(text="NO TAG",fg="#64748b")

    def _read_uid_cmd(self):
        uid = self.mrd.read_uid()
        if uid:
            animal_id = self._animal_id(uid)
            self._show_uid(uid,"HDX+",animal_id)
            self._log(f"Read UID OK | UID: {uid} | Animal ID: {animal_id}")
        else:
            self._log("Read UID: No tag or not supported.")

    def _gen_read(self):
        threading.Thread(target=self._gen_thread,daemon=True).start()

    def _gen_thread(self):
        self.root.after(0,lambda: self._log("ECM General Read..."))
        s1,s2,data = self.mrd.general_read()
        self.root.after(0,lambda: self._handle_gen(s1,s2,data))

    def _handle_gen(self,s1,s2,data):
        if data is None:
            self._log("General Read: No response."); return
        raw = " ".join(f"{b:02X}" for b in data)
        self._log(f"General Read | Status: {s1:02X} {s2:02X} | Data({len(data)}B): {raw}")
        tag_type = self._decode_status(s1)
        self._log(f"Tag Type: {tag_type}")
        # Parse UID (first 8 bytes of data = LSByte first)
        if len(data) >= 8:
            uid_raw   = data[:8]
            uid_hex   = "".join(f"{b:02X}" for b in reversed(uid_raw))
            animal_id = self._animal_id(uid_hex)
            self._show_uid(uid_hex,tag_type,animal_id)
            self._log(f"UID: {uid_hex} | Animal ID: {animal_id}")
        # Parse Animal ID from pages 15-16 if enough data
        if len(data) >= 72:
            aid_block_lo = data[56:60]  # block 14 (page 15)
            aid_block_hi = data[60:64]  # block 15 (page 16)
            aid_lo = "".join(f"{b:02X}" for b in aid_block_lo)
            aid_hi = "".join(f"{b:02X}" for b in aid_block_hi)
            self._log(f"Animal ID Block Low:  {aid_lo}")
            self._log(f"Animal ID Block High: {aid_hi}")

    def _all_blocks(self):
        threading.Thread(target=self._blocks_thread,daemon=True).start()

    def _blocks_thread(self):
        self.root.after(0,lambda: self._log("Reading all 16 blocks..."))
        blocks = self.mrd.read_all_blocks()
        self.root.after(0,lambda: self._update_table(blocks))

    def _update_table(self,blocks):
        for i,d in enumerate(blocks):
            if d and len(d)>=4:
                locked = (i < 4 or i >= 14)
                tag    = "locked" if locked else "open"
                lock_t = "Locked" if locked else "Open"
                self.tree.item(str(i),values=(
                    i,PAGE_LABELS[i],
                    f"{d[0]:02X}",f"{d[1]:02X}",f"{d[2]:02X}",f"{d[3]:02X}",lock_t
                ),tags=(tag,))
                self._log(f"  Block {i:2d}: {d[0]:02X} {d[1]:02X} {d[2]:02X} {d[3]:02X}  {PAGE_LABELS[i]}")

                # Populate Animal ID label from blocks 14+15
                if i == 14:
                    self._log(f"  Animal ID Lo: {d[0]:02X}{d[1]:02X}{d[2]:02X}{d[3]:02X}")
                if i == 15:
                    self._log(f"  Animal ID Hi: {d[0]:02X}{d[1]:02X}{d[2]:02X}{d[3]:02X}")
            else:
                self.tree.item(str(i),
                               values=(i,PAGE_LABELS[i],"??","??","??","??","N/A"),
                               tags=("empty",))

    # ── Poll ─────────────────────────────────────────
    def _toggle_poll(self):
        if self.poll_var.get():
            self.polling = True
            self._log("Auto-poll started (80ms, ECM Charge Read).")
            threading.Thread(target=self._poll_loop,daemon=True).start()
        else:
            self.polling = False
            self._log("Auto-poll stopped.")

    def _poll_loop(self):
        last = None
        while self.polling:
            result = self.mrd.charge_read()
            if result:
                status, uid = result
                if uid != last:
                    last      = uid
                    animal_id = self._animal_id(uid)
                    tag_type  = self._decode_status(status)
                    self.root.after(0, lambda u=uid,a=animal_id,t=tag_type:
                                    self._show_uid(u,t,a))
                    self.root.after(0, lambda u=uid,a=animal_id,t=tag_type:
                                    self._log(f"Tag: {u} | {t} | Animal ID: {a}"))
            else:
                if last is not None:
                    last = None
                    self.root.after(0, lambda:
                                    self.lbl_uid.config(text="NO TAG",fg="#64748b"))
            time.sleep(0.08)   # 80ms = HDX cycle time


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
