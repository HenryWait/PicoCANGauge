import os
import microcontroller
import toml
from time import sleep
import board
import busio
import gc9a01
import displayio
import terminalio
from adafruit_display_text import label
from displayio_dial import Dial
from digitalio import DigitalInOut
from adafruit_mcp2515 import MCP2515 as CAN
from adafruit_mcp2515.canio import Match

# Overclock for better performance
microcontroller.cpu.frequency = 270000000

TEXT_SCALE = os.getenv("TEXT_SCALE")
BRIGHTNESS = os.getenv("BRIGHTNESS")

# Load TOML protocol once during initialization
with open("haltech_can_protocol.toml") as channel:
    protocol = toml.load(channel)

# Load environment variables once during initialization
GAUGE_CHANNELS = [os.getenv(f"GAUGE{i}_CHANNEL") for i in range(1, 5)]
GAUGE_MIN = [os.getenv(f"GAUGE{i}_MIN") for i in range(1, 5)]
GAUGE_MAX = [os.getenv(f"GAUGE{i}_MAX") for i in range(1, 5)]

# MCP2515 pin setup
cs = DigitalInOut(board.GP20)
cs.switch_to_output()
spi = busio.SPI(board.GP18, board.GP19, board.GP16)

# Release any resources currently in use for the displays
displayio.release_displays()

# Raspberry Pi Pico pinout
tft_clk = board.GP10   # must be a SPI CLK
tft_mosi = board.GP11  # must be a SPI TX
tft_rst = board.GP8
tft_dc = board.GP14
tft_cs = board.GP9
tft_bl = board.GP15
tft_spi = busio.SPI(clock=tft_clk, MOSI=tft_mosi)

# Make the displayio SPI bus and the GC9A01 display
display_bus = displayio.FourWire(tft_spi, command=tft_dc, chip_select=tft_cs, reset=tft_rst)
display = gc9a01.GC9A01(display_bus, width=240, height=240, backlight_pin=tft_bl)
display.brightness = BRIGHTNESS

# Define common settings for the dials
tick_font = terminalio.FONT
width = 100
height = 100
gauge_padding = 15

# Create four Dial widgets with different positions
dials = [
    Dial(x=20, y=20, width=width, height=height, padding=gauge_padding, start_angle=-120, sweep_angle=240, min_value=(GAUGE_MIN[0]), max_value=(GAUGE_MAX[0]), tick_label_font=tick_font, tick_label_scale=1.5,),
    Dial(x=120, y=20, width=width, height=height, padding=gauge_padding, start_angle=-120, sweep_angle=240, min_value=(GAUGE_MIN[1]), max_value=(GAUGE_MAX[1]), tick_label_font=tick_font, tick_label_scale=0,),
    Dial(x=20, y=120, width=width, height=height,padding=gauge_padding, start_angle=-120, sweep_angle=240, min_value=(GAUGE_MIN[2]), max_value=(GAUGE_MAX[2]), tick_label_font=tick_font, tick_label_scale=0,),
    Dial(x=120, y=120, width=width, height=height, padding=gauge_padding, start_angle=-120, sweep_angle=240, min_value=(GAUGE_MIN[3]), max_value=(GAUGE_MAX[3]), tick_label_font=tick_font, tick_label_scale=0,)
    ]

# Define main display group
main = displayio.Group()
display.root_group = main

for dial in dials:
    main.append(dial)

def create_labels(display):
    colors = [0xFF0000, 0x00FF00, 0x0000FF, 0xFFFF00]
    label_positions = [(80, 100), (180, 100), (80, 180), (180, 180)]
    text_label_strings = ["MAP", "TPS", "AFR", "RPM"]

    text_labels = []
    for i in range(4):
        text_label = label.Label(
            terminalio.FONT,
            text=text_label_strings[i],
            color=colors[i],
            anchor_point=(0.5, 0.5),
            anchored_position=label_positions[i],
            scale=TEXT_SCALE,
        )
        text_labels.append(text_label)
        main.append(text_label)

    return text_labels

def update_dials(values):
    # create_labels(display)
    for i, value in enumerate(values):
        dials[i].value = value
    display.refresh()  # force the display to refresh

# Dictionary for conversion formulas should replace with eval
conversion_functions = {
    "y = x": lambda x: x,
    "y = x / 10": lambda x: x / 10,
    "y = (x / 10) - 101.3": lambda x: (x / 10) - 101.3,
    "y = x / 1000": lambda x: x / 1000,
    "y = x - 101.3": lambda x: x - 101.3,
    "y = x * 11 / 50 - 101.3": lambda x: (x * 11 / 50) - 101.3
}

def get_can_data(can_id):
    can_bus = CAN(spi, cs, loopback=False, silent=False, baudrate=1000000)
    can_bus.initialize()
    while True:  # Loop until a matching message is received
        with can_bus.listen(matches=[Match(can_id)], timeout=0.5) as listener:
            msg = listener.receive()
            if msg is not None and msg.id == can_id:
                can_data = msg.data
                listener.deinit
                return can_data

def get_can_frames(can_data, channel):
    if can_data is not None:
        frames = protocol[channel]["message_position"]
        can_frames = ((can_data[frames[0]] << 8) | can_data[frames[1]])
        return can_frames
    return None

def calculate_value(can_frames, channel):
    if can_frames is not None:
        conversion = protocol[channel]["conversion"]
        conversion_func = conversion_functions.get(conversion)
        if conversion_func:
            return conversion_func(can_frames)
    return None

def format_value_with_units(value, channel):
    if value is not None:
        units = protocol[channel]["units"]
        return f"{value:.2f} {units}"
    return None

def get_formatted_value(can_id, channel):
    can_data = get_can_data(can_id)
    can_frames = get_can_frames(can_data, channel)
    value = calculate_value(can_frames, channel)
    # return format_value_with_units(value, channel)
    return value

# Main function
def main():
    new_values = [0] * 4  # Initialize list
    while True:
        for i, channel in enumerate(GAUGE_CHANNELS):
            if channel:
                can_id = protocol[channel]["can_id"]
                formatted_value = get_formatted_value(can_id, channel)
                if formatted_value is not None:
                    new_values[i] = formatted_value
                    print(formatted_value)
        update_dials(new_values)
        sleep(0.1)

# Run the main function
if __name__ == "__main__":
    main()
