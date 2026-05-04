# TI RI-STU-MRD2 Link Management Protocol (LMP) Notes

This document contains extracted knowledge from the TI RI-STU-MRD2 technical manual specifically regarding the serial Link Management Protocol (LMP), response formats, and status codes. This information was critical in resolving the "Ghost Tag" / Electrical Noise issue.

## 📡 Essential Command Codes
*   **`0x00`**: Single Read Normal Mode (Executes one tag read cycle)
*   **`0x01`**: Continuous Read Mode
*   **`0x03`**: Get Reader Firmware Version

*Note: Many standard TI systems use `0x00` for Get Version, but the MRD2 strictly maps `0x00` to "Single Read". Sending `0x00` expecting a version string will result in a tag read attempt.*

## 📊 Packet Structure
All LMP packets follow this byte-level structure:
`[SOH] [Length] [Command/Status] [Data Payload...] [BCC]`
*   **`SOH`**: Always `0x01` (Start of Header)
*   **`Length`**: Number of bytes in the Command/Status + Data Payload.
*   **`BCC`**: Block Check Character. Calculated by XOR-ing all bytes from the `Length` byte to the end of the `Data Payload`.

## 🚦 Status Codes (Response from a Read Command)
When sending a Read Command (`0x00`), the reader responds with a Status Code as the first byte of the data payload.

*   **`0x03` - No Transponder Detected**: The reader performed a read cycle but found no RF signature.
*   **`0x0C` - Standard Read-Only (RO) Tag Detected**: Success. The reader found a standard TI TIRIS tag (e.g., TRPGR30ATGB).
*   **`0x0D` - Read/Write (R/W) Tag Detected**: Success. 
*   **`0x07` - "Other" Transponder Detected**: The reader detected an RF signal that looked like a start-bit, but it didn't match a standard protocol perfectly. 

### 👻 The "Ghost Tag" Phenomenon (Status `0x07`)
If the antenna is in an environment with high electrical noise, the noise can mimic an RF start bit. The MRD2 reader will attempt to decode this noise, resulting in a Status `0x07` response with 15 bytes of random garbage data. 
**Solution**: Software must explicitly check the Status byte. If it is `0x07` and the environment is noisy, this data should be discarded as false reads.

## 📦 Data Payload Structure (for Status `0x07`)
When the reader returns an `0x07` status, it returns the *entire raw protocol buffer* (Length `0x0F` / 15 bytes):
*   `Byte 0`: SOH (`0x01`)
*   `Byte 1`: Length (`0x0F`)
*   `Byte 2`: **Status** (`0x07`)
*   `Byte 3`: Protocol Start Byte
*   `Bytes 4-11`: **ID Data (8-byte UID)** *(Reversed LSB-first)*
*   `Bytes 12-13`: Data BCC (CRC)
*   `Byte 14`: End Bits
*   `Byte 15`: **RSSI** (Received Signal Strength Indicator)
*   `Byte 16`: **Phase** Angle
*   `Byte 17`: LMP BCC (XOR Checksum)

*For standard successful reads (`0x0C`), the response may omit the Protocol Start byte and return a shorter, filtered payload containing just the Status and the UID.*
