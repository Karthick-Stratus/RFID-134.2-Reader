# AI Project Instructions: STM32F407ZGT6 Development Environment

# Context & Role
Act as an Expert Embedded Firmware Engineer. I am building a custom firmware project for an STM32F407ZGT6 (144-pin) microcontroller. I am using an ST-Link V3 programmer connected via SWD. 

# The Goal
I have zero knowledge of how to configure this IDE to compile code and flash it to the physical hardware. I need you to set up my workspace completely from scratch.

# Your Tasks
1. **Toolchain & Build System**: Generate the foundational `CMakeLists.txt` or `Makefile` required to compile code for the ARM Cortex-M4 (STM32F407ZG) using the standard `arm-none-eabi-gcc` toolchain.
2. **Hardware Debugger Interface**: Generate the OpenOCD configuration file required to interface with an ST-Link V3 and an STM32F4 target.
3. **IDE Integration**: Create the necessary IDE launch/debug configurations (e.g., `/.vscode/launch.json` and `/.vscode/tasks.json`) so I can simply click a "Run/Debug" button in this IDE to compile, flash, and debug the chip.
4. **Validation Firmware**: Provide a simple `main.c` file with a basic "Blink" or "Hello World" loop just so I can test that the flashing process works on the STM32F407ZGT6.
5. **Tutorial**: Provide a brief, step-by-step tutorial on what buttons to click or commands to run in this IDE to actually push the code to the board.

# Technical Specification
* **Microcontroller**: STM32F407ZGT6 (ARM Cortex-M4)
* **Programmer**: ST-Link V3
* **Connection**: Serial Wire Debug (SWD)
* **Build System**: CMake (Preferred) or Makefile
* **Flash Software**: OpenOCD (via ST-Link)
