import serial
import time

class MRD2Reader:
    """
    Python driver for the TI RI-STU-MRD2 RFID Micro-Reader.
    Uses the Link Management Protocol (LMP).
    """
    
    SOH = 0x01  # Start of Header
    
    # Common Commands
    CMD_GET_VERSION = 0x03
    CMD_IDENTIFY    = 0x00
    
    def __init__(self, port='COM17', baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"Connected to {self.port} at {self.baudrate} baud.")
            return True
        except Exception as e:
            print(f"Error connecting to {self.port}: {e}")
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Disconnected.")

    def calculate_bcc(self, packet_bytes):
        """Calculates the BCC (XOR checksum) for a list of bytes."""
        bcc = 0
        for b in packet_bytes:
            bcc ^= b
        return bcc

    def send_command(self, cmd, data=[]):
        """Constructs and sends an LMP packet."""
        if not self.ser or not self.ser.is_open:
            return None
        
        # Packet structure: [SOH] [Length] [Cmd] [Data...] [BCC]
        # Length is Cmd + Data
        length = 1 + len(data)
        payload = [length, cmd] + data
        bcc = self.calculate_bcc(payload)
        
        packet = bytearray([self.SOH] + payload + [bcc])
        
        # Clear buffers
        self.ser.reset_input_buffer()
        
        # Send
        # print(f"Sending: {packet.hex(' ')}")
        self.ser.write(packet)
        
        # Read Response
        return self.read_response()

    def read_response(self):
        """Reads and validates an LMP response packet."""
        # Read SOH
        header = self.ser.read(1)
        if not header or header[0] != self.SOH:
            return None
        
        # Read Length
        length_byte = self.ser.read(1)
        if not length_byte:
            return None
        length = length_byte[0]
        
        # Read Data (Cmd echo + Status + Payload) and BCC
        remaining = self.ser.read(length + 1)
        if len(remaining) < length + 1:
            return None
        
        data = remaining[:-1]
        received_bcc = remaining[-1]
        
        # Verify BCC
        calculated_bcc = self.calculate_bcc([length] + list(data))
        if calculated_bcc != received_bcc:
            print("BCC mismatch!")
            return None
            
        return list(data)

    def get_version(self):
        """Retrieves the firmware version."""
        response = self.send_command(self.CMD_GET_VERSION)
        if response:
            version = ".".join(map(str, response))
            return version
        return None

    def identify_tag(self):
        """
        Sends an Identify command to read a tag.
        Returns a dictionary with parsed data or None if no tag/error.
        """
        response = self.send_command(self.CMD_IDENTIFY)
        if response:
            status = response[0]
            if status == 0x03:
                # No tag detected
                return None
                
            # Dictionary to hold the extracted data
            tag_data = {
                "status": status,
                "status_hex": f"0x{status:02X}",
                "uid": None,
                "rssi": None,
                "phase": None,
                "is_noise_likely": False
            }

            if status == 0x07 and len(response) >= 10:
                # Status 0x07 (Other/Noise) includes "Protocol Start" at index 1
                # UID is from index 2 to 10
                uid_bytes = response[2:10]
                tag_data["uid"] = "".join([f"{b:02X}" for b in reversed(uid_bytes)])
                tag_data["is_noise_likely"] = True
                
                # Check for RSSI and Phase (usually at the end of the packet)
                if len(response) >= 15:
                    tag_data["rssi"] = response[13]
                    tag_data["phase"] = response[14]
                    
            elif status in [0x0C, 0x0D, 0x0E, 0x0F] and len(response) >= 9:
                # Standard read: Status + UID
                # Depending on the reader configuration, the UID might start at index 1
                uid_bytes = response[1:9]
                tag_data["uid"] = "".join([f"{b:02X}" for b in reversed(uid_bytes)])
                
                if len(response) >= 11:
                    tag_data["rssi"] = response[9]
                    tag_data["phase"] = response[10]
            else:
                # Unknown structure
                tag_data["raw_data"] = [hex(b) for b in response]

            return tag_data
            
        return None

def main():
    reader = MRD2Reader(port='COM17', baudrate=9600)
    
    if not reader.connect():
        return

    print("Testing connection...")
    version = reader.get_version()
    if version:
        print(f"Reader Firmware Version: {version}")
    else:
        print("Failed to get reader version. Check protocol or baud rate.")
        reader.disconnect()
        return

    print("\nStarting Tag Reading Loop (Ctrl+C to stop)...")
    try:
        while True:
            tag = reader.identify_tag()
            if tag:
                if tag.get("uid"):
                    noise_flag = "[NOISE/OTHER] " if tag.get("is_noise_likely") else ""
                    rssi_str = f" | RSSI: {tag['rssi']} | Phase: {tag['phase']}" if tag.get("rssi") is not None else ""
                    print(f"{noise_flag}Tag Detected: {tag['uid']}{rssi_str} (Status: {tag['status_hex']})")
                else:
                    print(f"Unknown Response Format: {tag.get('raw_data')}")
            
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        reader.disconnect()

if __name__ == "__main__":
    main()
