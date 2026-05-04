import serial
import serial.tools.list_ports
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

class MRD2Reader:
    """
    Python driver for the TI RI-STU-MRD2 RFID Micro-Reader.
    Uses the Link Management Protocol (LMP).
    """
    SOH = 0x01
    CMD_GET_VERSION = 0x03  # Send Microreader S/W version
    CMD_IDENTIFY    = 0x00  # Single Read Normal Mode

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

    def calculate_bcc(self, packet_bytes):
        bcc = 0
        for b in packet_bytes:
            bcc ^= b
        return bcc

    def send_command(self, cmd, data=[]):
        if not self.ser or not self.ser.is_open:
            return None
        
        length = 1 + len(data)
        payload = [length, cmd] + data
        bcc = self.calculate_bcc(payload)
        packet = bytearray([self.SOH] + payload + [bcc])
        
        self.ser.reset_input_buffer()
        self.ser.write(packet)
        # return the raw response bytes for debugging
        return self.read_response_raw()

    def read_response_raw(self):
        """Reads raw bytes and returns them for diagnostic purposes."""
        # Read up to 32 bytes or until timeout
        raw = self.ser.read(32)
        return raw

    def parse_lmp(self, raw):
        """Attempts to parse a raw buffer as an LMP packet."""
        if not raw or len(raw) < 4: return None
        if raw[0] != self.SOH: return None
        length = raw[1]
        if len(raw) < length + 3: return None # SOH + Length + Data + BCC
        
        data = raw[2:2+length]
        received_bcc = raw[2+length]
        calculated_bcc = self.calculate_bcc([length] + list(data))
        
        if calculated_bcc != received_bcc:
            return "BCC_ERROR"
        return list(data)

    def get_version(self):
        response = self.send_command(self.CMD_GET_VERSION)
        if response == "BCC_ERROR": return "BCC Error"
        if response and response[0] == self.CMD_GET_VERSION:
            return ".".join(map(str, response[1:]))
        return None

    def identify_tag(self):
        response = self.send_command(self.CMD_IDENTIFY)
        if response == "BCC_ERROR": return "BCC Error"
        if response and response[0] == self.CMD_IDENTIFY:
            status = response[1]
            if status == 0x00:
                uid_bytes = response[2:10]
                return "".join([f"{b:02X}" for b in reversed(uid_bytes)])
        return None

class RFIDApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stratus RFID Reader - MRD2")
        self.root.geometry("600x500")
        self.root.configure(bg="#f0f0f0")

        self.reader = MRD2Reader()
        self.polling = False
        self.poll_thread = None

        self.setup_ui()
        self.refresh_ports()

    def setup_ui(self):
        # Style
        style = ttk.Style()
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TLabel", font=("Segoe UI", 10), background="#f0f0f0")

        # Connection Frame
        conn_frame = ttk.LabelFrame(self.root, text=" Connection Settings ", padding=10)
        conn_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, sticky="w")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=15)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(conn_frame, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=5)

        ttk.Label(conn_frame, text="Baud:").grid(row=0, column=3, sticky="w", padx=(10,0))
        self.baud_var = tk.StringVar(value="9600")
        self.baud_combo = ttk.Combobox(conn_frame, textvariable=self.baud_var, values=["9600", "19200", "38400", "57600", "115200"], width=10)
        self.baud_combo.grid(row=0, column=4, padx=5, pady=5)

        self.btn_connect = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.btn_connect.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

        self.btn_version = ttk.Button(conn_frame, text="Check Version", command=self.check_version, state="disabled")
        self.btn_version.grid(row=1, column=2, padx=5, pady=10, sticky="ew")

        self.btn_ascii = ttk.Button(conn_frame, text="Test ASCII", command=self.test_ascii, state="disabled")
        self.btn_ascii.grid(row=1, column=3, columnspan=2, padx=5, pady=10, sticky="ew")

        # Display Frame
        disp_frame = tk.Frame(self.root, bg="white", bd=2, relief="sunken")
        disp_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(disp_frame, text="LAST TAG DETECTED", font=("Segoe UI", 8, "bold"), bg="white", fg="#666").pack(pady=(5,0))
        self.lbl_uid = tk.Label(disp_frame, text="NO TAG", font=("Consolas", 28, "bold"), bg="white", fg="#2c3e50")
        self.lbl_uid.pack(pady=10)

        # Control Frame
        ctrl_frame = tk.Frame(self.root, bg="#f0f0f0")
        ctrl_frame.pack(fill="x", padx=20)

        self.btn_read = ttk.Button(ctrl_frame, text="Single Read", command=self.single_read, state="disabled")
        self.btn_read.pack(side="left", expand=True, fill="x", padx=5)

        self.poll_var = tk.BooleanVar(value=False)
        self.chk_poll = ttk.Checkbutton(ctrl_frame, text="Auto Polling", variable=self.poll_var, command=self.toggle_polling, state="disabled")
        self.chk_poll.pack(side="left", padx=10)

        # Log Frame
        log_frame = ttk.LabelFrame(self.root, text=" Activity Log ", padding=5)
        log_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.log_area = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9), state="disabled")
        self.log_area.pack(fill="both", expand=True)

    def log(self, message):
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            if "COM17" in ports: self.port_var.set("COM17")
            else: self.port_var.set(ports[0])
        self.log(f"Found {len(ports)} ports.")

    def toggle_connection(self):
        if not self.reader.ser or not self.reader.ser.is_open:
            # Connect
            self.reader.port = self.port_var.get()
            self.reader.baudrate = int(self.baud_var.get())
            res = self.reader.connect()
            if res is True:
                self.log(f"Connected to {self.reader.port} at {self.reader.baudrate} baud.")
                self.btn_connect.config(text="Disconnect")
                self.btn_version.config(state="normal")
                self.btn_ascii.config(state="normal")
                self.btn_read.config(state="normal")
                self.chk_poll.config(state="normal")
                self.check_version()
            else:
                self.log(f"Connection failed: {res}")
                messagebox.showerror("Error", f"Could not open port: {res}")
        else:
            # Disconnect
            self.polling = False
            self.reader.disconnect()
            self.log("Disconnected.")
            self.btn_connect.config(text="Connect")
            self.btn_version.config(state="disabled")
            self.btn_ascii.config(state="disabled")
            self.btn_read.config(state="disabled")
            self.chk_poll.config(state="disabled")
            self.poll_var.set(False)
            self.lbl_uid.config(text="OFFLINE", fg="#95a5a6")

    def check_version(self):
        raw_res = self.reader.send_command(self.reader.CMD_GET_VERSION)
        if not raw_res:
            self.log("No response received.")
            self.lbl_uid.config(text="NO DATA", fg="#e67e22")
            return

        self.log(f"Raw RX (Hex): {raw_res.hex(' ').upper()}")
        
        parsed = self.reader.parse_lmp(raw_res)
        if parsed == "BCC_ERROR":
            self.log("LMP BCC Error! Data might be corrupted.")
        elif parsed:
            # For Get Version, the response is usually the version string/bytes
            version = ".".join(map(str, parsed))
            self.log(f"Reader Firmware: {version}")
            self.lbl_uid.config(text="CONNECTED", fg="#27ae60")
        else:
            self.log("Response does not match LMP format. Check Mode.")
            try:
                text = raw_res.decode('ascii', errors='ignore').strip()
                if text: self.log(f"Possible ASCII: '{text}'")
            except: pass

    def test_ascii(self):
        """Sends an ASCII 'v' command to see if the reader is in ASCII mode."""
        if not self.reader.ser: return
        self.log("Testing ASCII 'v\\r'...")
        self.reader.ser.reset_input_buffer()
        self.reader.ser.write(b"v\r")
        time.sleep(0.1)
        res = self.reader.ser.read(64)
        if res:
            self.log(f"ASCII RX Hex: {res.hex(' ').upper()}")
            text = res.decode('ascii', errors='ignore').strip()
            self.log(f"ASCII RX Text: '{text}'")
        else:
            self.log("No ASCII response.")

    def single_read(self):
        raw_res = self.reader.send_command(self.reader.CMD_IDENTIFY)
        if not raw_res:
            self.log("No tag response.")
            return
            
        self.log(f"Identify RX (Hex): {raw_res.hex(' ').upper()}")
        
        parsed = self.reader.parse_lmp(raw_res)
        if parsed == "BCC_ERROR":
            self.log("BCC Error in response!")
        elif parsed:
            status = parsed[0]
            if status == 0x03:
                self.log("No Tag Detected (Status: 0x03)")
                self.lbl_uid.config(text="NO TAG", fg="#95a5a6")
            elif status in [0x07, 0x0C, 0x0D, 0x0E, 0x0F] and len(parsed) >= 9:
                # Based on TI MRD2 Manual for status 0x07 (Other) or 0x0C (RO Tag)
                # parsed[0] = Status
                # parsed[1] = Protocol Start
                # parsed[2:10] = ID Data (8 bytes)
                # parsed[10:12] = CRC/BCC
                # parsed[12] = End bits
                # parsed[13] = RSSI (if enabled)
                # parsed[14] = Phase (if enabled)
                
                uid_bytes = parsed[2:10]
                uid = "".join([f"{b:02X}" for b in reversed(uid_bytes)])
                
                rssi = parsed[13] if len(parsed) > 13 else "N/A"
                phase = parsed[14] if len(parsed) > 14 else "N/A"
                
                tag_type = "Valid Tag" if status != 0x07 else "Other/Noise"
                
                self.log(f"{tag_type} (Status {status:02X}): {uid} | RSSI: {rssi}")
                
                # If it's just random noise (0x07) you might want to filter it, but we show it
                color = "#2980b9" if status != 0x07 else "#e67e22"
                self.lbl_uid.config(text=uid, fg=color)
            else:
                self.log(f"Identify Unknown Status: {status:02X} or invalid length {len(parsed)}")
                self.lbl_uid.config(text="ERROR", fg="#e74c3c")
        else:
            self.log("Could not parse Identify response.")

    def toggle_polling(self):
        if self.poll_var.get():
            self.polling = True
            self.log("Starting auto-polling...")
            self.poll_thread = threading.Thread(target=self.poll_loop, daemon=True)
            self.poll_thread.start()
        else:
            self.polling = False
            self.log("Stopping auto-polling...")

    def poll_loop(self):
        while self.polling:
            uid = self.reader.identify_tag()
            if uid and uid != "BCC_ERROR":
                self.root.after(0, lambda u=uid: self.update_uid(u))
            time.sleep(0.5)

    def update_uid(self, uid):
        self.lbl_uid.config(text=uid, fg="#2980b9")
        self.log(f"Auto-Read: {uid}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RFIDApp(root)
    root.mainloop()
