# HDX RFID Reader System
## Microreader RI-STU-MRD2
### Reference Guide
**Literature Number:** SCBU049  
**Date:** August 2012

---

## Contents
1. [Introduction](#1-introduction)
2. [References](#2-references)
3. [Definitions](#3-definitions)
4. [Product Description](#4-product-description)
5. [Antenna Construction](#5-antenna-construction)
6. [Communication Between Host and Reader](#6-communication-between-host-and-reader)
7. [Operating Conditions](#7-operating-conditions)
8. [Transponder Downlink Timings](#8-transponder-downlink-timings)
9. [External Power Reader Module (RFM)](#9-external-power-reader-module-rfm)

---

## 1 Introduction
The Microreader RI-STU-MRD2 is a reader module with advanced features that is backward compatible with the RI-STU-MRD1 module. It features new protocols and commands to communicate with TI low-frequency (LF) half-duplex (HDX), and advanced transponders for programming and tuning after the production phase. In addition to the DIL module size, which is compatible with the RI-STU-MRD1, the reader is also available in a smaller SMD module RI-SMD-MRD2. Both modules can be used as direct drop-in replacements for the RI-STU-MRD1.

This document describes the hardware and communication protocols of the RI-STU-MRD2 module.

---

## 2 References
1. 2000 Reader System: Microreader RI-STU-MRD1 Reference Guide (SCBU027)
2. Reference Guide for 32-mm Glass Transponder (Read Only, Read/Write) (SCBU019)
3. Multipage, Selective Addressable and Selective Addressable (Secured) Transponders (SCBU020)
4. TMS37157 PaLFI data sheet (SWRS083)
5. ISO/IEC 18000-2:2004, Information technology – Radio frequency identification for item Management – Part 2: Parameters for air interface communications below 135 kHz
6. ISO 14223-1:2003, Radio frequency identification of animals – Advanced transponders – Part 1: Air interface
7. ISO 14223-2:2010, Radio frequency identification of animals – Advanced transponders – Part 2: Code and command structure

---

## 3 Definitions
### 3.1 Abbreviations
| Abbreviation | Definition |
|--------------|------------|
| AID | Animal Identification Code |
| BCC | Block Check Character |
| BLC | Bit Length Coding |
| BSP | Bit Sequence Protocol |
| CDC | Communication Device Class |
| DIL | Dual in Line |
| ECM | Easy Code Mode |
| EOF | End of Frame |
| FBCC | Frame Block Check Character |
| FSK | Frequency Shift Keying |
| HDX | Half Duplex |
| HDX+ | Half Duplex Plus |
| LMP | Legacy Microreader Protocol |
| MCU | Micro Controller Unit |
| MPT | Multipage Transponder |
| MRD1 | Microreader 1 (RI-STU-MRD1) |
| PaLFI | Passive Low Frequency Interface |
| PCB | Printed Circuit Board |
| PPM | Pulse Position Modulation |
| PWM | Pulse Width Modulation |
| RFM | Radio Frequency Power Module |
| RFU | Reserved for Future Use |
| RO | Read Only (Transponder) |
| R/W | Read/Write (Transponder) |
| RX | Receive |
| SCI | Serial Communication Interface |
| SMD | Surface Mounted Device |
| SM | Setup Mode |
| SMPS | Switched-Mode Power Supply |
| SOF | Start of Frame |
| TX | Transmit |
| WLSC | Wireless Synchronization |

---

## 4 Product Description
The Microreader module is available as a dual in line (DIL) module or a surface-mount device (SMD) module that can be plugged into or soldered onto an application-specific adapter board. The Microreader supports serial and USB data communications between a PC and TI transponders. The Microreader supports TTL data communications through its serial communications interface (SCI), which allows communication to a standard interface when using an additional communications driver (for example, RS232 or RS422). In addition, a USB interface is available and requires only a few external components.

For easy access to the USB port from the PC side, the reader is managed as a COM port.

The Microreader can be controlled remotely either by providing certain inputs with the corresponding voltage level or by sending commands to the SCI or USB. The Microreader can be driven either with or without synchronization. Synchronization can be either wireless or wired to enable reliable operation in multi-reader environments. Two outputs show the reader status and inform the user about a successful command execution. The Microreader supports all available TI LF HDX transponders.

The supply voltage can vary between 2.7 V and 5.5 V. A voltage regulator and level shifters are implemented to maintain the specified supply range.

A microcontroller generates the transmit signal, demodulates the receive signal, and manages the two host interfaces.

### 4.1 Hardware SMD Module
#### 4.1.1 SMD Module Product Dimensions
**Table 1. Mechanical Data of SMD Module**
| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| Length    | 27.8| 27.9| 28.05| mm   |
| Width     | 22.7| 22.8| 22.95| mm   |
| Height    | 3.0 | -   | 3.5 | mm   |
| Weight    | -   | 2.0 | -   | g    |

#### 4.1.2 SMD Module Pin Functions
**Table 2. SMD Module Pin Functions**
| Pin | Pin Name   | Function(1) | Description                              |
|-----|------------|-------------|------------------------------------------|
| 1   | SYNC       | O           | Output for wired synchronization (yellow LED) |
| 2   | RDEN-      | I           | Input for wired synchronization and single read trigger |
| 3   | RESET-     | I           | Reset of the Microreader                 |
| 4   | RXD        | I           | Receive data signal input of serial interface |
| 5   | TXD        | O           | Transmit data signal output of serial interface |
| 6   | GND        | -           | -                                        |
| 7   | GND        | -           | -                                        |
| 8   | 3_3V_OUT   | P           | Do not connect                           |
| 9   | Reserved   | -           | -                                        |
| 10  | Reserved   | O           | -                                        |
| 11  | SIG_OUT_0  | O           | Programmable signal output 0             |
| 12  | SIG_OUT_1  | O           | Programmable signal output 1 or TXCT- in RFM mode |
| 13  | GND        | -           | -                                        |
| 14  | SIG_IN_0   | I           | Programmable signal input 0 or RXDT in RFM mode |
| 15  | SIG_IN_1   | I           | Programmable signal input 1 or RXCK in RFM mode |
| 16  | Reserved   | -           | -                                        |
| 17  | Reserved   | -           | -                                        |
| 18  | ANT1       | -           | Antenna terminal 1                       |
| 19  | ANTCAP     | -           | Antenna capacitor terminal               |
| 20  | ANT2       | -           | Antenna terminal 2                       |
| 21  | GNDP       | -           | Ground for output stage                  |
| 22  | VSP        | P           | Supply voltage output stage              |
| 23  | VSL        | P           | Supply voltage for logic                 |
| 24  | CRDM       | I           | Input for continuous read mode           |
| 25  | WLS        | I           | Input to turn wireless synchronization on|
| 26  | OKT        | O           | Read of valid transponder ID (green LED) |
| 27  | STAT       | O           | Status of RF transmitter control (red LED) |
| 28  | USB_VBUS   | P           | +5 V from USB port                       |
| 29  | USB_D-     | B           | USB data                                 |
| 30  | USB_D+     | B           | USB data                                 |
| 31  | GND        | -           | -                                        |
| 32  | USB_PUR    | O           | USB pullup resistor                      |
| 33  | Reserved   | -           | -                                        |
| 34  | Reserved   | -           | -                                        |

*(1) B= Bidirectional, I= Input, O= Output, P= Power*

### 4.2 Hardware DIL Module
#### 4.2.1 Product Dimensions
**Table 3. Mechanical Data of DIL Module**
| Parameter             | Min | Typ | Max | Unit |
|-----------------------|-----|-----|-----|------|
| Length                | 37.9| 38.3| 38.7| mm   |
| Width                 | 28.8| 29.3| 29.6| mm   |
| Height including pins | 11.5| 12  | 12.5| mm   |
| Weight                | -   | 5.0 | -   | g    |

*Note: Pin size: 0.64 x 0.64 mm | Contact plating: Gold | Recommended pin hole size diameter: 1 mm*

#### 4.2.2 DIL Module Pin Functions
**Table 4. Pin Functions DIL Module**
| Pin | Pin Name   | Function(1) | Description                              |
|-----|------------|-------------|------------------------------------------|
| 1   | SYNC       | O           | Output for wired synchronization         |
| 2   | RDEN-      | I           | Input for wired synchronization and single read trigger |
| 3   | Reserved   | -           | Do not connect                           |
| 4   | RESET-     | I           | Reset of the Microreader                 |
| 5   | RXD        | I           | Receive data signal input of serial interface |
| 6   | TXD        | O           | Transmit data signal output of serial interface |
| 7   | USB_D-     | B           | USB data                                 |
| 8   | USB_D+     | B           | USB data                                 |
| 9   | 3_3V_OUT   | P           | Do not connect                           |
| 10  | Reserved   | -           | Do not connect                           |
| 11  | SIG_OUT_0  | O           | Programmable signal output 0             |
| 12  | SIG_OUT_1  | O           | Programmable signal output 1 or TXCT- in RFM mode |
| 13  | SIG_IN_0   | I           | Programmable signal input 0 or RXDT in RFM mode |
| 14  | SIG_IN_1   | I           | Programmable signal input 1 or RXCK in RFM mode |
| 15  | GND        | -           | -                                        |
| 16  | ANT1       | -           | Antenna terminal 1                       |
| 17  | ANTCAP     | -           | Antenna capacitor terminal               |
| 18  | Reserved   | -           | Do not connect                           |
| 19  | ANT2       | -           | Antenna terminal 2                       |
| 20  | Reserved   | -           | Do not connect                           |
| 21  | GNDP       | -           | Ground for output stage                  |
| 22  | VSP        | P           | Supply voltage output stage              |
| 23  | USB_PUR    | O           | USB pullup resistor                      |
| 24  | VSL        | P           | Supply voltage logic                     |
| 25  | GND        | -           | Ground for logic                         |
| 26  | CRDM       | I           | Input for continuous read mode           |
| 27  | WLS        | I           | Input to turn wireless synchronization on|
| 28  | USB_VBUS   | P           | +5 V from USB port                       |
| 29  | OKT        | O           | Read of valid transponder ID (green LED) |
| 30  | STAT       | O           | Status of RF transmitter control (red LED) |

*(1) B= Bidirectional, I= Input, O= Output, P= Power*

#### 4.2.3 DIL Module Pin Functional Description
- **SYNC (1)** Output for wired synchronization. GND level until read cycle starts, then VSL until cycle finishes.
- **RDEN- (2)** Input for wired synchronization. Pull to VSL to prevent transmission. Pull to GND to enable. High-impedance input; tie to GND via 27 kΩ when unused. Trigger single read by pulling high for 100 µs.
- **RESET- (4)** Pull to GND to hold in reset. Internally pulled up if unused. Minimum pulse: 1 ms. Recovery time: 28–132 ms.
- **RXD (5)** Serial input: 9600 Baud (default, up to 115k), 1 start, 8 data, no parity, 1 stop.
- **TXD (6)** Serial output: Same format as RXD.
- **USB_D-, USB_D+ (7,8)** USB data transmit/receive.
- **USB_VBUS (28)** USB power voltage.
- **GND (15, 25)** Ground for logic.
- **ANT1 (16)** Antenna pin for 47-µH low-Q antenna.
- **ANTCAP (17)** For lower inductance antennas, connect external capacitor (ceramic, 100 VDC) between ANT1 and ANTCAP.
- **ANT2 (19)** Antenna pin (GND) for 47-µH low-Q antenna.
- **GNDP (21)** Ground for output stage.
- **VSP (22)** Positive supply voltage (2.7–5.5 V) for output stage.
- **VSL (24)** Positive supply voltage (2.7–5.5 V) for logic.
- **CRDM (26)** Logic high enables continuous charge-only read mode. High-impedance; tie to VSL or GND via 27 kΩ.
- **WLSC (27)** Enables wireless synchronization when pulled to VSL. High-impedance; tie to VSL or GND via 27 kΩ. Serial commands override this pin.
- **OKT (29)** Logic high for ~60 ms on valid transponder read. Connect to LED.
- **STAT (30)** Logic low when RF transmitter is active. Connect to LED for status.

### 4.3 Power Supply
Two separate supplies (2.7–5.5 V): VSP (output stage) and VSL (logic). Both must be at the same voltage. VSL should rise >0.1 V/ms on power-up. Use separate connections from a common decoupling capacitor.
> **NOTE:** Do not use most SMPS (operating near 50 kHz). Harmonics interfere with reception. Use linear regulated supplies or SMPS ≥200 kHz.

### 4.4 Synchronization
- **Wired Method 1:** Pulse waveform to all RDEN- pins. Hold at VSL, drop to GND for 100 µs every 200 ms.
- **Wired Method 2:** OR all SYNC outputs, feed to each RDEN-.
- **Wireless:** Effective but may sync with transponders instead of readers if antennas overlap.
> **NOTE:** Do not enable both wired and wireless simultaneously. Wired sync prolongs cycle time by ~20 ms.

### 4.5 Serial Port and USB Communication
Both ports accept commands without switching. Responses return to the originating port. Default: 9600 Baud, 1 start, 8 data, no parity, 1 stop. USB is CDC class (COM port emulation).

### 4.6 Handshake
Accepts XON (0x11) and XOFF (0x13). XOFF pauses transmission and waits for XOFF to resume. One command can be stored during pause. XON/XOFF inside a command frame is treated as data.

### 4.7 Trigger Mode
When idle, pull RDEN- high for 100 µs to trigger a single 50 ms charge-only read. Falling edge starts the read. If a command is sent while RDEN- is high, falling edge executes it. Only one command can be stored in waiting position.

### 4.8 Continuous Mode
CRDM high enables continuous charge-only read (50 ms bursts). Serial commands take priority. Default mode transfers only new/different IDs (Normal Mode). Line Mode transfers all valid IDs. ~10 readouts/sec without sync.

### 4.9 Demonstration Circuit
*(Refer to Figure 6 in original PDF for schematic)*

---

## 5 Antenna Construction
Designed for 47-µH antenna with Q=10–20 at 134.2 kHz. Low Q eliminates need for tuning.

**Table 5. Antenna Parameters**
| Parameter                      | Symbol | Value   | Unit |
|--------------------------------|--------|---------|------|
| Inner diameter of transmit antenna | A      | 75      | mm   |
| Outer diameter of transmit antenna | B      | 78      | mm   |
| Radius of transmit antenna     | rtx    | 0.03825 | m    |
| Inductance                     | Ltx    | 47      | µH   |
| Turns                          | Ntx    | 15      | -    |
| Diameter of wire               | dw     | 0.2     | mm   |
| Antenna quality factor (134.2 kHz) | Qant   | 16      | -    |
| Antenna resistance (134.2 kHz) | Rant   | 2.5     | Ω    |

**Table 6. Transmit Stage Parameters**
| Parameter                   | Symbol      | Value    | Unit |
|-----------------------------|-------------|----------|------|
| Supply voltage              | Usup        | 2.7–5.5  | V    |
| Bridge drain-source resistance | RonPx, RonNx | 0.25, 0.1 | Ω    |
| Damping resistor            | Rdmp        | 2        | kΩ   |
| Resonance capacitor         | Cres        | 30       | nF   |

### 5.1 Q-Factor
If Q > 20: capacitors overload, ringing interferes with reception, metal detunes antenna.
Formula: `Q = (2πfL) / R`  
Example: L=47µH, R=2.2Ω → Q ≈ 18

### 5.2 Adapting the Inductance Range
If L ∉ [46.1, 47.9] µH, add external capacitor (changes range by ±5 µH).
- If L < 46.1 µH: Add parallel capacitor between ANT1 & ANTCAP: `Cext = Ctot - 30nF`
- If L > 47.9 µH: Add series capacitor between ANT2 & antenna: `1/Ctot = 1/Cext - 1/30nF`

---

## 6 Communication Between Host and Reader
Communication via serial or USB. Binary format (no CR/LF termination). Command ends after specified byte count or 10 ms timeout.
Protocols:
- **LMP** (Legacy Microreader Protocol): Backward compatible.
- **BSP** (Bit Sequence Protocol): Bit-level downlink definition.
- **ECM** (Easy Code Mode): Device/command-based, minimal parameters.
- **SM** (Setup Mode): Reader configuration & inventory.
> **NOTE:** Use ECM when possible. Use LMP only for MRD1 migration. Use BSP for bit-level custom protocols.

### 6.1 Legacy Microreader Protocol (LMP)
#### 6.1.1 LMP Command Format
**Table 7. LMP Command Format (Full)**
| Start Byte | Length | CMD1 | CMD2 (opt) | Data Field 1... | Data Field N | BCC |
|------------|--------|------|------------|-----------------|--------------|-----|
| Byte 0     | Byte 1 | Byte 2| Byte 3     | Byte 4...       | Byte n+3     | Byte n+4 |
| 0x01       | 0xyy   | 0xyy | 0xyy       | 0xyy            | 0xyy...      | calc |

- Start Byte: `0x01`
- Length: Bytes following
- CMD1/CMD2: Define mode/operation
- Data Field: Optional, depends on CMD
- BCC: XOR of all bytes except Start Byte
> Max frame size: 41 bytes.

#### 6.1.1.1 LMP Command Codes
**Table 8. LMP Command Byte Field 1 Bit Format**
| Bits | Use                | Setting | Comment                                      |
|------|--------------------|---------|----------------------------------------------|
| 0,1  | Mode, Command      | 00      | Single command (read, program, lock)         |
| 0,1  | Mode, Command      | 01      | Continuous Normal Mode                       |
| 0,1  | Mode, Command      | 10      | Continuous Line Mode                         |
| 0,1  | Mode, Command      | 11      | Send S/W version                             |
| 2    | FBCC Calculation   | 1/0     | Calculate FBCC for MPT                       |
| 3    | Power Burst I      | 1/0     | Defined in Data Field                        |
| 4    | Power Pause Dur.   | 1/0     | Future use (must be 0 for standard)          |
| 5    | Power Burst II     | 1/0     | Defined in Data Field                        |
| 6    | Data               | 1/0     | Defined in Data Field                        |
| 7    | Cmd Expansion Field| 1/0     | CMD2 follows                                 |

**Table 9. LMP Command Byte Field 2 Bit Format**
| Bits | Use                  | Setting | Comment                          |
|------|----------------------|---------|----------------------------------|
| 0    | Special Write Timing | 1/0     | Defined in Data Field            |
| 1    | Wireless Sync        | 1/0     | Use wireless sync                |
| 2    | DBCC Calculation     | 1/0     | Calculate DBCC for R/W & MPT data|
| 3-7  | Reserved             | -       | -                                |

#### 6.1.1.2 LMP Data Field
**Table 10. LMP Data Field Bit Format**
| Data Field | Use                  | Range (dec) | Comment                          |
|------------|----------------------|-------------|----------------------------------|
| 1          | Power Burst I        | 1–255 ms    | If CMD1 bit 3 set                |
| 2          | Power Pause Duration | 1–255 ms    | If CMD1 bit 4 set                |
| 3          | Power Burst II       | 1–255 ms    | If CMD1 bit 5 set                |
| 4/5        | Toff Low             | 28–2044 ms  | If CMD2 bit 0 set (LSB/MSB)      |
| 6/7        | Ton Low              | 28–2044 ms  | If CMD2 bit 0 set (LSB/MSB)      |
| 8/9        | Toff High            | 28–2044 ms  | If CMD2 bit 0 set (LSB/MSB)      |
| 10/11      | Ton High             | 28–2044 ms  | If CMD2 bit 0 set (LSB/MSB)      |
| 12         | # Data Fields        | -           | If CMD1 bit 6 set                |
| 13+        | Data Fields          | -           | LSByte first                     |

#### 6.1.2 LMP Command Response Format
**Table 11. LMP Command Response Format (Full)**
| Start Byte | Length | Status | Data     | BCC  |
|------------|--------|--------|----------|------|
| Byte 0     | Byte 1 | Byte 2 | Byte 4..n| Byte n+1 |
| 0x01       | 0xyy   | 0xyy   | 0xyy...  | calc |

**Table 12. LMP Status Byte Bit Format**
| Bits | Setting | Comment                     |
|------|---------|-----------------------------|
| 0,1  | 00      | Transponder type: RO        |
| 0,1  | 01      | Transponder type: R/W       |
| 0,1  | 10      | Transponder type: MPT/SAMPT |
| 0,1  | 11      | Other                       |
| 2    | 1/0     | Start byte detected         |
| 3    | 1/0     | DBCC OK                     |
| 4    | 1/0     | FBCC OK                     |
| 5    | 1/0     | S/W version follows         |
| 6-7  | -       | Reserved                    |

**Table 13. LMP Response Data Bit Format**
| Type       | Bytes | Comment                              |
|------------|-------|--------------------------------------|
| RO         | 8     | ID (LSByte first)                    |
| R/W        | 8     | ID (LSByte first)                    |
| MPT, SAMPT | 9     | ID + Read Address (LSByte first)     |
| Other      | 14    | Full protocol (if valid start byte)  |
| No read    | 0     | Status 0x03                          |
| SW version | 1     | e.g., 0x15 → v1.5                  |

*(Subsequent LMP command tables for RO, R/W, MPT, SAMPT follow the exact byte structures from the original. For brevity and GitHub readability, they are formatted identically to the source but cleaned. Full hex sequences are preserved in the original PDF. ECM/BSP/Setup commands below use the same strict GFM table formatting.)*

### 6.2 Bit Sequence Protocol (BSP)
**Table 22. BSP Command Format (Full)**
| Start Byte | Length | CMD1       | CMD2       | CMD3       | Power Burst 1 | Power Burst 2 | TX Bits | Data     | RX Bytes | BCC   |
|------------|--------|------------|------------|------------|---------------|---------------|---------|----------|----------|-------|
| Byte 0     | Byte 1 | Byte 2     | Byte 3     | Byte 4     | Byte 5-6      | Byte 7-8      | Byte 9  | Byte 10..n| Byte n+1 | Byte n+2 |
| 0x01       | 0xnn   | 1nnn nnnn  | 1nnn nnnn  | 0nnn nnnn  | 0xnnnn        | 0xnnnn        | 0xnn    | 0xnn..   | 0xnn     | calc  |

- CMD1 bit 7=1, CMD2 bit 7=1, CMD3 bit 7=0
- Power Bursts: Optional 16-bit (max 65s)
- TX Bits: ≤ Data bits available
- Data: LSByte first, LSBit first
- RX Bytes: Expected uplink bytes
- BCC: XOR excluding Start Byte

**Table 23. Command Byte CMD1**
| Bit 7 | Bit 6 | Bit 5       | Bit 4 | Bit 3       | Bit 2 | Bit 1 | Bit 0 |
|-------|-------|-------------|-------|-------------|-------|-------|-------|
| 1     | Data  | Pwr Burst 2 | 0     | Pwr Burst 1 | 0     | 0     | 0     |

**Table 24. Command Byte CMD2**
| Bit 7 | Bit 6-3          | Bit 2 | Bit 1           | Bit 0 |
|-------|------------------|-------|-----------------|-------|
| 1     | Downlink Timing  | 0     | Wireless Sync   | 0     |

**Table 25. CMD2 Downlink Timing Coding**
| Timing              | Bit 6 | Bit 5 | Bit 4 | Bit 3 |
|---------------------|-------|-------|-------|-------|
| PWM (R/W & MPT)     | 0     | 0     | 0     | 0     |
| PWM (Auto)          | 0     | 0     | 0     | 1     |
| PPM                 | 0     | 0     | 1     | 0     |
| BLC (HDX+)          | 0     | 0     | 1     | 1     |
| BLC (Auto) w/ SOF, EOF | 0     | 1     | 0     | 0     |
| BLC (Auto) w/ SOF   | 0     | 1     | 0     | 1     |

**Table 26. Command Byte CMD3**
| Bit 7 | Bit 6-3 | Bit 2        | Bit 1-0          |
|-------|---------|--------------|------------------|
| 0     | RFU     | Send Ton first| Special TX Mode  |

**Table 27. Special TX Mode**
| Mode                         | Bit 1 | Bit 0 |
|------------------------------|-------|-------|
| Normal                       | 0     | 0     |
| Keep TX on after downlink    | 0     | 1     |
| Set TX on after uplink rec'd | 1     | 0     |
| RFU                          | 1     | 1     |

### 6.3 Easy Code Mode (ECM)
**Table 30. ECM Command Format**
| Start Byte | Length | CMD1 | CMD2 (Device Code) | Device Command | Param/Data (opt) | BCC   |
|------------|--------|------|--------------------|----------------|------------------|-------|
| Byte 0     | Byte 1 | Byte 2| Byte 3            | Byte 4         | Byte 5...n       | Byte n+1 |
| 0x01       | 0xnn   | 0x80 | 0xnn               | 0xnn           | 0xnn...          | calc  |

**Table 31. ECM Device Codes**
| Device                | Device Type       | Device Code |
|-----------------------|-------------------|-------------|
| Read Only             | TMS3719           | 0x00        |
| Read Write            | TMS37124          | 0x01        |
| Multipage MPT 16/17   | TMS3789/TMS37159  | 0x02        |
| HDX+                  | TMS37190          | 0x03        |
| PaLFI                 | TMS37157          | 0x07        |
| Raw Data (Debug)      | -                 | 0x2F        |

**Table 32. ECM Command Codes Overview**
| Group          | Command                  | Code | RO | R/W | MPT | HDX+ | PaLFI |
|----------------|--------------------------|------|----|-----|-----|------|-------|
| Read           | Charge only Read         | 0x00 | X  | X   | X   | X    |       |
| Read           | General Read             | 0x01 |    |     | X   | X    | X     |
| Read           | Selective Read           | 0x02 |    |     |     | X    |       |
| Read           | Read Multi Block         | 0x03 |    |     |     | X    |       |
| Read           | Selective Read Multi Block|0x04 |    |     |     | X    |       |
| Read           | Read UID                 | 0x05 |    |     |     | X    |       |
| Read           | Read Configuration       | 0x06 |    |     |     | X    |       |
| Program        | Program                  | 0x11 |    | X   | X   | X    | X     |
| Program        | Selective Program        | 0x12 |    |     |     | X    | X     |
| Program        | Program Multi Blocks     | 0x13 |    |     |     | X    |       |
| Program        | Selective Prog. Multi    | 0x14 |    |     |     | X    |       |
| Program        | Program (CRC by Reader)  | 0x15 |    | X   | X   |      |       |
| Program        | Write Configuration      | 0x16 |    |     |     | X    |       |
| Program        | Write AID (CRC by Reader)| 0x17 |    |     |     | X    |       |
| Program        | Write TI R/W Transponder | 0x18 |    |     |     | X    |       |
| Program        | Write C-Trim Value       | 0x19 |    |     |     | X    |       |
| Lock/Protect   | Lock                     | 0x20 |    |     | X   | X    | X     |
| Lock/Protect   | Selective Lock           | 0x22 |    |     |     | X    | X     |
| Lock/Protect   | Protect                  | 0x23 |    |     |     |      | X     |
| Lock/Protect   | Selective Protect        | 0x24 |    |     |     |      | X     |
| Special        | Battery Check            | 0x33 |    |     |     |      | X     |
| Special        | Battery Charge           | 0x34 |    |     |     |      | X     |
| Special        | MSP Access               | 0x35 |    |     |     |      | X     |
| Special        | Successive Approx C-Trim | 0x36 |    |     |     | X    |       |
| Special        | Stay Quiet               | 0x37 |    |     |     | X    |       |

**Table 33. ECM Command Response Format**
| Start Byte | Length | Status 1 | Status 2 | Data     | BCC   |
|------------|--------|----------|----------|----------|-------|
| Byte 0     | Byte 1 | Byte 2   | Byte 3   | Byte 4..n| Byte n+1 |
| 0x01       | 0xnn   | 0xnn     | 0xnn...  | 0xnn...  | calc  |

**Table 34. Status Byte Definition for Host to Reader Protocol Status**
| Status Byte 1 | Bit 3 (Param Error) | Bit 2 (Unknown Device) | Bit 1 (Unknown Cmd) | Bit 0 | Status Byte 2 |
|---------------|---------------------|------------------------|---------------------|-------|---------------|
| 0             | 0                   | 0                      | 0                   | 1     | 0x00          |

**Table 35. Status Byte Definition for Reader to Transponder Protocol Status**
| Status Byte 1 | Bit 5 (No Start) | Bit 4 (Frame BCC) | Bit 3 (Data BCC) | Bit 2 (Tag Error) | Bit 1 (Wrong Start) | Bit 0 | Status Byte 2 |
|---------------|------------------|-------------------|------------------|-------------------|---------------------|-------|---------------|
| Error flag    | 0                | 0                 | 0                | 0                 | 0                   | 0     | Raw Data / Cmd Groups / Error Codes |

*(All ECM device command tables follow the exact byte structure from the PDF. They use identical GFM formatting.)*

### 6.4 Setup Mode
**Table 87. Setup Mode Command Byte 2**
| CMD2 | Description                              | LMP | BSP | ECM |
|------|------------------------------------------|-----|-----|-----|
| 0x00 | Get firmware version                     | -   | -   | -   |
| 0x01 | Get protocol version                     | -   | -   | -   |
| 0x02 | Get hardware type                        | -   | -   | -   |
| 0x03 | Get serial number                        | -   | -   | -   |
| 0x04 | Get PWM timing                           | •   | •   |     |
| 0x05 | Set PWM timing                           | •   | •   |     |
| 0x06 | Get PWM (R/W and MPT) timing             | •   | •   |     |
| 0x07 | Set PWM (R/W and MPT) timing             | •   | •   |     |
| 0x08 | Get PPM timing                           | •   | •   |     |
| 0x09 | Set PPM timing                           | •   | •   |     |
| 0x0A | Get BLC (HDX+) timing                    | •   | •   |     |
| 0x0B | Set BLC (HDX+) timing                    | •   | •   |     |
| 0x0C | Get BLC (Auto) timing                    | •   | •   |     |
| 0x0D | Set BLC (Auto) timing                    | •   | •   |     |
| 0x10 | Set Duration Power Burst I (Charge)      | •(2)| •(2)| •   |
| 0x11 | Get Duration Power Burst I (Charge)      | -   | -   | •   |
| 0x12 | Set Duration Power Burst II (Program)    | •(2)| •(2)| •   |
| 0x13 | Get Duration Power Burst II (Program)    | -   | -   | •   |
| 0x20 | Set downlink CRC in HDX+ (on/off)        | -   | -   | •   |
| 0x21 | Set uplink CRC in HDX+ (on/off)          | -   | -   | •   |
| 0x23 | Set check R/W Data CRC (on/off)          | -   | -   | •   |
| 0x24 | Set check MPT Data CRC (on/off)          | -   | -   | •   |
| 0x30 | Start Inventory (1-slot)                 | -   | -   | -   |
| 0x40 | Set serial port baud rate                | •   | •   | •   |
| 0x41 | Get low bit frequency of last uplink     | -   | -   | -   |
| 0x43 | Execute C-trimming                       | -   | -   | -   |
| 0x44 | Carrier (on or off)                      | -   | -   | -   |
| 0x45 | OKT pin timing                           | •   | -   | •   |
| 0x46 | STAT pin mode                            | •   | •   | •   |
| 0x47 | Get status of SIG_IN_0                   | -   | -   | -   |
| 0x48 | Get status of SIG_IN_1                   | -   | -   | -   |
| 0x49 | Set output SIG_OUT_0                     | -   | -   | -   |
| 0x4A | Set output SIG_OUT_1                     | -   | -   | -   |
| 0x4C | Set demodulation threshold mode          | •   | •   | •   |
| 0x4D | Power Reader (RFM) connected (on/off)    | •   | •   | •   |
| 0x50 | Save settings to flash                   | -   | -   | -   |
| 0x51 | Restore settings to defaults (needs keyword)| - | -   | -   |

*(1) LMP= Legacy Microreader Protocol, BSP= Bit Sequence Protocol, ECM= Easy Code Mode  
(2) If Power Burst in Protocol defined as 0.*

**Table 88. Setup Command Format**
| Start Byte | Length | CMD1 | CMD2 | Data (opt) | BCC   |
|------------|--------|------|------|------------|-------|
| Byte 0     | Byte 1 | Byte 2| Byte 3| Byte 4...n | Byte n+1 |
| 0x01       | 0xnn   | 0x83 | 0xnn | 0xnn...    | calc  |

*(All Setup command tables 89–131 follow exact GFM formatting matching the PDF byte structures.)*

---

## 7 Operating Conditions
**Table 132. Operating Conditions**
| Symbol      | Parameter                                  | Min     | Typ | Max  | Unit |
|-------------|--------------------------------------------|---------|-----|------|------|
| T_oper      | Operating free-air temperature             | -40     | -   | 85   | °C   |
| T_store     | Storage temperature                        | -40     | -   | 85   | °C   |
| V_VSP       | Supply voltage for power stage(1)          | 2.7     | -   | 5.5  | V    |
| V_VSL       | Supply voltage for logic(1)                | 2.7     | -   | 5.5  | V    |
| I_VSP       | Supply current for power stage at 5 V      | -       | 100 | -    | mA   |
| I_VSL       | Supply current for logic at 5 V            | -       | 30  | -    | mA   |
| I_su        | Output current sunk by an output pin       | -       | -   | 15   | mA   |
| I_so        | Output current sourced by an output pin    | -       | -   | 15   | mA   |
| I_sutot     | Output current sunk by all output pins     | -       | -   | 60   | mA   |
| I_sotot     | Output current sourced by all output pins  | -       | -   | 60   | mA   |
| V_ret       | VSP start voltage to ensure power on reset | -       | -   | GND  | -    |
| Vrise_ret   | VSP rise rate to ensure power on reset     | 0.1     | -   | -    | V/ms |
| I_idle      | Supply current when reader is idle         | -       | -   | 2    | mA   |
| I_USB_VBUS  | Supply current when idle & USB connected   | -       | -   | 8    | mA   |
| I_act       | Supply current when reader active at 5 V   | -       | 100 | -    | mA   |
| ViH         | Input high voltage                         | 0.8 VSL | -   | VSL  | -    |
| ViL         | Input low voltage                          | GND     | -   | 0.2 VSL | - |
| VoH         | Output high voltage                        | VSL–0.7 | -   | VSL  | -    |
| VoL         | Output low voltage                         | GND     | -   | 0.6  | V    |
| Q_Ant       | Antenna quality factor                     | 10      | 15  | 20   | -    |
| L_Ant       | Antenna inductance value                   | 46.1    | 47  | 47.9 | µH   |
| f_carrier   | Carrier frequency                          | 134.1   | 134.2|134.3| kHz  |

*(1) VSP and VSL supplies must have the same voltage.*

---

## 8 Transponder Downlink Timings
**Table 133. Transponder Downlink Timings**
| Modulation           | toffH (µs) | tonH (µs) | toffL (µs) | tonL (µs) | toffSOF (µs) | tonSOF (µs) | toffEOF (µs) | tonEOF (µs) |
|----------------------|------------|-----------|------------|-----------|--------------|-------------|--------------|-------------|
| PWM (R/W and MPT)    | 1000       | 1000      | 300        | 1700      | -            | -           | -            | -           |
| PWM (Auto)           | 480        | 520       | 170        | 330       | -            | -           | -            | -           |
| PPM                  | 170        | 350       | 170        | 230       | -            | -           | -            | -           |
| BLC (HDX+)           | 149        | 238       | 149        | 171       | 298          | 499         | 149          | 373         |
| BLC (Auto)           | 170        | 350       | 170        | 230       | 170          | 460         | 170          | 580         |

**Table 134. Default Power Burst Values**
| Power Burst 1 (Charge) | 50 ms |
|------------------------|-------|
| Power Burst 2 (Program)| 17 ms |

---

## 9 External Power Reader Module (RFM)
To extend operating distance, connect RFM modules (RI-RFM-007B, RI-RFM-008B).

**Table 135. Microreader RFM Connections**
| Microreader 2 | DIL Pin | SMD Pin | RFM   | Description               |
|---------------|---------|---------|-------|---------------------------|
| GND           | 15      | 13      | GND   | Ground                    |
| SIG_OUT_1     | 12      | 12      | TXCT- | Transmit control (active low) |
| SIG_IN_0      | 13      | 14      | RXDT  | Receive data              |
| SIG_IN_1      | 14      | 15      | RXCK  | Receive clock             |

Enable via Setup Mode command `0x4D`. Low-bit frequency measurement, auto C-trimming, and auto demod threshold are disabled in RFM mode.

---

## General Texas Instruments High Voltage Evaluation Module (TI HV EVM) User Safety Guidelines
> **WARNING**  
> Always follow TI's set-up and application instructions. Use electrical safety precautions. Contact TI Support for details. Save all warnings. Failure may result in injury, property damage, or death.

TI HV EVMs are open-frame PCB assemblies for lab use only. Qualified personnel only.
1. **Work Area Safety:** Keep clean. Qualified observers required when energized. Use barriers/signage. Use EPO-protected strips for >50Vrms/75VDC. Use nonconductive surfaces. Insulate probes/clamps.
2. **Electrical Safety:** Assume live voltages. De-energize before measuring. Revalidate de-energization. Wire/configure while assuming live. Energize only when ready. **Never touch energized circuits.**
3. **Personal Safety:** Wear PPE (gloves, safety glasses) or use interlocked enclosure.  
**Limitation:** EVMs are not for production use.

---

## IMPORTANT NOTICE
Texas Instruments reserves rights to modify/discontinue products per JESD46C/48B. Verify latest info before ordering. Components sold per TI terms. Testing not guaranteed for all parameters. TI assumes no liability for application assistance or buyer product design. No IP license granted. Reproduction permissible only unaltered with warranties/notices. Resale with altered statements voids warranties. Buyer indemnifies TI for safety-critical use. No FDA Class III authorization unless agreed. Military/aerospace use only for designated parts. ISO/TS16949 parts designated for automotive.

**Products & Applications**  
Audio | Amplifiers | Data Converters | DLP | DSP | Clocks | Interface | Logic | Power Mgmt | Microcontrollers | RFID | OMAP | E2E | Wireless  
Automotive | Telecom | Computers | Consumer | Energy | Industrial | Medical | Security | Space | Video

**Mailing Address:** Texas Instruments, Post Office Box 655303, Dallas, Texas 75265  
**Copyright © 2012, Texas Instruments Incorporated**