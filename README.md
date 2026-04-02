# TI RI-STU-MRD2 PCB Antenna Design & Calculator

![Project Banner](https://img.shields.io/badge/Status-Active-brightgreen)
![Frequency](https://img.shields.io/badge/Frequency-134.2_kHz-blue)
![Architecture](https://img.shields.io/badge/Platform-Texas_Instruments-red)
![Deployment](https://img.shields.io/badge/Deployment-GitHub_Pages-blueviolet)

This repository contains the design parameters, calculations, and an interactive calculator for designing a custom 134.2 kHz PCB Antenna tailored for the **Texas Instruments RI-STU-MRD2 Microreader**. 

## 🎯 Project Overview

This project is geared toward designing an RFID antenna for a **cleanroom conveyor system**, where pods move at a speed of 0.5 m/s. The system relies on 32mm HDX glass tags to reliably identify the moving pods. To ensure reliable, continuous reading within strict spatial constraints, the antenna must be a **rectangular planar spiral** trace integrated directly onto a printed circuit board (PCB).

---

## 🔌 Hardware Selection & Replication

To replicate this specific RFID implementation for the cleanroom conveyor, or to understand the exact hardware driving this integration, use the following strictly specified components:

| Component | Part Number / Module | Description |
|-----------|--------------------|-------------|
| **RFID Reader** | `RI-STU-MRD2` | Texas Instruments 134.2 kHz Microreader. Handles HDX/FDX communication, antenna driving, and raw tag decoding. |
| **Microcontroller** | `STM32F407ZGT6` | Cortex-M4 MCU. Acts as the host system, receives decoded tag data from the MRD2 module via UART/SPI, processes business logic, and pipes data up to the factory backend. |
| **Ethernet PHY** | `LAN8710A-EZC` | Microchip 10/100 Ethernet Transceiver. Enables high-speed, reliable factory network integration for the STM32 to transmit pod tracking data. |

### Evaluation Environment
If you are rapidly prototyping this system, you do not need to build a custom MCU board from scratch. You can utilize the following commercial off-the-shelf Evaluation Board which natively supports the STM32 target and Ethernet PHY:
* **Board:** [Olimex STM32-E407 (Open Source Hardware)](https://www.olimex.com/Products/ARM/ST/STM32-E407/open-source-hardware)
* **Setup Instructions:** Once you have the Olimex board and the MRD2 reader module, connect the MRD2's TX/RX outputs directly to one of the STM32-E407's exposed UART or SPI peripheral headers. Tune the PCB antenna using the calculator below, connect it to the MRD2, and boot up the system.

---

## ⚙️ Strict Hardware Requirements

The TI RI-STU-MRD2 is a precision microreader. Operating an incorrectly tuned antenna can cause poor read range or permanent damage to the reader hardware. The electrical requirements must strictly fall within the following parameters:

1. **Target Frequency**: 134.2 kHz
2. **Target Inductance (L)**: 47.0 µH 
   - *Strict Operating Range*: 46.0 µH to 47.9 µH
3. **Quality Factor (Q)**: Target ~12 to 16
   - *Strict Operating Range*: 10 to 20

---

## 🔬 Theory of Operation

### Why a PCB Antenna?
Standard wire-wound coils offer great inductance but are bulky and difficult to mass-produce with tight tolerances. A PCB antenna provides unparalleled repeatability, precision trace routing, and a low spatial footprint which is strictly necessary in a constrained robotic cleanroom environment. 

### Critical Parameters
- **Trace Resistance**: In a planar coil, a longer, thinner trace increases DC and AC resistance. Too much resistance severely attenuates the reader's TX signal and ruins the antenna Q-factor.
- **Copper Weight**: We typically use 1 oz (35 µm) or 2 oz (70 µm) copper on PCBs. Heavier copper reduces resistance, offering a massive boost to the Quality Factor without expanding the antenna's X-Y footprint.
- **Quality Factor (Q)**: The Q-factor is the ratio of Inductive Reactance to Resistance. A Q-factor that is too low means the signal is lost to heat (resistance), drastically reducing read range. A Q-factor that is too high causes bandwidth narrowing, preventing the HDX signal from successfully transmitting.

---

## 🧮 Mathematical Models

Our calculator relies on the following proven models:

### 1. Resistance (R)
Calculates the physical DC resistance based on copper resistivity.
```
R = ρ * (Length / Area)
```
- **ρ (Copper resistivity)**: `1.68 × 10^-8 Ω·m`
- **Area**: `Trace Width × Copper Thickness` 

### 2. Inductance (L) - Modified Wheeler Formula
For rectangular planar spirals, the Modified Wheeler formula predicts Inductance highly accurately.
```
L_est = (μ0 * N² * d_avg * c1 / 2) * [ln(c2 / fill_ratio) + c3 * fill_ratio + c4 * fill_ratio²]
```
Where:
- **`μ0`**: Magnetic Constant (`4π × 10^-7`)
- **`N`**: Number of Turns
- **`d_avg`**: Average diameter (meters)
- **`fill_ratio`**: `(d_out - d_in) / (d_out + d_in)`
- **Constants**: `c1=1.27`, `c2=2.07`, `c3=0.18`, `c4=0.13`

### 3. Quality Factor (Q)
```
XL (Inductive Reactance) = 2 * π * f * L
Q = XL / R
```

---

## 💻 Web Calculator Usage

This repository hosts a standalone interactive web calculator deployed via GitHub Pages to quickly iterate through PCB variables and find the perfect geometry. 

### How to Use the Calculator:
1. Navigate to the **[Interactive Web Calculator](https://karthick-stratus.github.io/RFID-134.2-Reader/)**.
2. **Input Physical Constraints**: Enter your maximal Outer Length and Outer Width dictated by your enclosure.
3. **Tune Traces**: Adjust the Trace Width, Spacing, and Number of Turns.
4. **Optimize**: Select your Corner Routing type and Copper Weight. Focus on maintaining your **Inductance** between 46-47.9 µH and your **Q-Factor** between 10-20. The UI will output GREEN (Pass) or RED (Fail) iteratively as you tweak.