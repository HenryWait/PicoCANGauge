# PicoCANGauge
Inital version uses circuitpython as a proof of concept.
Car is running a Haltech Elite 1500 ECU, [CAN protocal] [https://www.ptmotorsport.com.au/wp-content/uploads/2022/09/Haltech-CAN-Broadcast-Protocol-V2.35.0-1.pdf]

Hardware:
- Raspberry Pi Pico
- Waveshare 1.28" Round Display Module
- Generic MCP2515  w/ TJA1050 reciever and 16mhz clock CANbus module
- 3D printed display housing that fits inside an MX5 NA/NB airvent

Issues:
- After a short time of listening for CAN messages and displaying them the Pico runs out of memory and crashes
- Attempting to listen for a wider range of messages and display upto four values causes messages to be missed and values get updated less frequently

TODO: 
- Rewrite code in C++ to compile for Pico
- Implement multiple Gauge faces for different vlaues and styles of gauges

