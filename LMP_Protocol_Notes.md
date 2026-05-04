# TI RI-STU-MRD2 LMP Protocol — Complete Reference

Extracted from TI Microreader II raw TX/RX captures and TI technical documentation.

---

## 🔑 Critical Discoveries

### Why Python Code Failed vs TI Microreader II

| Factor | TI Microreader II | Python Code (old) |
|--------|------------------|-------------------|
| Command | `01 04 80 03 03 [page] [BCC]` | `01 01 00 01` (CMD 0x00) |
| Poll Rate | ~80ms (Auto mode) | 500ms |
| Method | Reads per memory page | Single Read attempt |
| Result | Stable UID every read | Noise/No Tag |

The Microreader II does NOT use the simple `CMD 0x00` for tag identification. It reads individual memory pages using the `0x80` command family.

---

## 📡 Packet Structure (LMP)

```
[SOH=0x01] [LEN] [DATA bytes...] [BCC]
BCC = XOR of (LEN ^ DATA[0] ^ DATA[1] ^ ... ^ DATA[n])
```

---

## 📋 Command Reference

### Get Firmware Version
```
TX: 01 01 03 01
    01=SOH, 01=LEN, 03=CMD, 01=BCC
```

### Read Memory Page (PRIMARY READ COMMAND)
Verified from TI Microreader II TX capture.
```
TX: 01 04 80 03 03 [page] [BCC]
    BCC = 0x04 ^ 0x80 ^ 0x03 ^ 0x03 ^ page

Example page 1:  01 04 80 03 03 01 85
Example page 14: 01 04 80 03 03 0E 8A   ← from Microreader II Tx20
Example page 12: 01 04 80 03 03 0C 88   ← from Microreader II Tx19
```

### Read Page SUCCESS Response
```
RX: 01 0A 00 00 [B3][B2][B1][B0][??][??][??][??] [BCC]
    LEN=0x0A=10 bytes, Status=0x00

Verified: 01 0A 00 00 C9 57 45 1D 07 11 10 96 5C
          → Page data: B3=C9, B2=57, B1=45, B0=1D (Chip ID upper nibble)
```

### Single Read (CMD 0x00) — HDX Timing Sensitive
```
TX: 01 01 00 01
Response status codes:
  0x00 = Success (tag in field at exact timing window)
  0x03 = No Tag Detected
  0x07 = Other/Raw HDX data — can be noise OR real tag in raw framing
```

---

## 🗺️ Tag Memory Map (HDX+ Industrial Tag — 16 Pages × 4 Bytes)

| Page | Description                      | Notes                          |
|------|----------------------------------|--------------------------------|
| 1    | Chip ID Byte 3,2,1,0             | Locked (read-only)             |
| 2    | Reserved & Chip ID Byte 6,5,4    | Locked                         |
| 3    | Reserved & Chip ID Byte 9,8,7    | Locked                         |
| 4    | Config Byte 2,1 & CRC MSB,LSB    | Locked                         |
| 5-14 | User Memory (32 bytes total)     | Read/Write if unlocked         |
| 15   | Animal ID Byte 3,2,1,0           | ISO 11784/11785 animal ID low  |
| 16   | Animal ID Byte 7,6,5,4           | ISO 11784/11785 animal ID high |

---

## 🔢 UID Reconstruction (from pages 1, 2, 3)

```
Page 1 → [B3, B2, B1, B0]   (Chip ID Byte 3,2,1,0)
Page 2 → [Res, B6, B5, B4]  (Reserved + Chip ID Byte 6,5,4)
Page 3 → [Res, B9, B8, B7]  (Reserved + Chip ID Byte 9,8,7)

64-bit UID (MSB first) = [B7][B6][B5][B4][B3][B2][B1][B0]

Example (from captured tag):
  Page1: C9 57 45 1D → B3=C9, B2=57, B1=45, B0=1D
  Page2: 1A 11 10 96 → B6=11, B5=10, B4=96
  Page3: 0B 02 13 07 → B7=07

  UID = 07 11 10 96 C9 57 45 1D
  Decimal (Animal ID, lower 38 bits) = 5092064726786552XX
```

---

## 🔢 Status Codes

| Code | Meaning                    |
|------|----------------------------|
| 0x00 | Success                    |
| 0x03 | No transponder detected    |
| 0x07 | Other/raw HDX data (noise or raw tag) |

---

## ⏱️ Timing (HDX Read Cycle)

- **Charge Phase**: ~50ms (reader energizes tag)
- **Listen Phase**: ~20ms (tag transmits stored data)
- **Reader Overhead**: ~10ms
- **Total Cycle**: ~80ms → poll at ≤100ms for reliable reads

The TI Microreader II "Auto" mode polls continuously at this ~80ms rate, which is why it reads reliably. Polling slower (500ms) misses most read windows.

---

## 📟 Verified Raw Communication (from TI Microreader II screenshots)

### Tag: HDX+(R/O Industrial Standard-Application)
- **UID**: `07 11 10 96 C9 57 45 1D`
- **Page 1**: C9 57 45 1D
- **Page 2**: 1A 11 10 96
- **Page 3**: 0B 02 13 07
- **Page 4**: 08 02 48 95 (Config + CRC)
- **Pages 5-14**: 00 00 00 00 (empty user memory)

### Exact Microreader II TX/RX captured:
```
TX Tx20: 01 04 80 03 03 0E 8A  (Read Page 14)
RX Rx20: 01 0A 00 00 C9 57 45 1D 07 11 10 96 5C

TX Tx19: 01 04 80 03 03 0C 88  (Read Page 12)
RX Rx19: 01 0A 00 00 00 00 00 00 00 00 00 00 0A  (User memory, all zeros)
```
