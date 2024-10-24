# PicoCANGauge
Car is running a Haltech Elite 1500 ECU, [CAN protocal](https://www.ptmotorsport.com.au/wp-content/uploads/2022/09/Haltech-CAN-Broadcast-Protocol-V2.35.0-1.pdf)

Hardware:
==========================================================
- Raspberry Pi Pico 2 (should work on a RP2040 Pico as well)
- Waveshare 1.28" Round Display Module with touch (GC9A01 display driver)
- Adafruit PiCowBell MCP2515 CANbus module
- 3D printed display housing that fits inside an MX5 NA/NB airvent

Installing dependencies with Circup
==========================================================

Make sure that you have ``circup`` installed in your Python environment.
Install it with the following command if necessary:

    pip3 install circup

With ``circup`` installed and your CircuitPython device connected use the
following command to install all the dependencies:

    circup install gc9a01 toml displayio_dial adafruit_mcp2515

Or the following command to update an existing version:

    circup update


TODO: 
==========================================================
- Add labels below the gauges to tell which is which
- Change the Tic marks to match the range/scale of different channels being displayed
at the moment they will only display 0-100 so I have chosen to set the tick font size to 0 for channels this doesn't make sense for.
- Do an alternate version or mode where one dial occupies the full display
- Add touch, adafruit_cst8xx should work with the waveshare display, have the touch cycle through different sets of gauges/dials.
- Implement a menu that can modify the settings.toml

