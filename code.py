import board
import busio
import displayio
import digitalio
import adafruit_mcp2515
import time
import gc9a01
import terminalio
from adafruit_display_text import label
import gc
import microcontroller

# Release any resources currently in use for the displays
displayio.release_displays()

# Constants for CAN and display configuration
DATA_RATE = 1000000  # CAN bus data rate in Hz (1Mbps)
UPDATE_INTERVALS = {
    "MAP": 0.02,  # Update interval for MAP value in seconds
    "TPS": 0.02,  # Update interval for TPS value in seconds
    "Lambda": 0.5,  # Update interval for Lambda value in seconds
}
DISPLAY_WIDTH = 240  # Display width in pixels
DISPLAY_HEIGHT = 240  # Display height in pixels
TEXT_SCALE = 3  # Scale factor for text on the display
ATMOS_KPA = 97

def setup_display():
    """Initialize and configure the display."""
    tft_clk = board.GP10
    tft_mosi = board.GP11
    tft_rst = board.GP12
    tft_dc = board.GP13
    tft_cs = board.GP14
    tft_bl = board.GP15

    spi_display = busio.SPI(clock=tft_clk, MOSI=tft_mosi)
    display_bus = displayio.FourWire(
        spi_display, command=tft_dc, chip_select=tft_cs, reset=tft_rst
    )
    display = gc9a01.GC9A01(
        display_bus, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, backlight_pin=tft_bl
    )
    return display

def show_startup_screen(display, duration=5):
    """Show the startup screen with 'PicoGauge' text and 'Looking for Haltech' on the second line."""
    splash = displayio.Group()

    # Set the background color to black
    color_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
    color_palette = displayio.Palette(1)
    color_palette[0] = 0x000000  # Black

    bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
    splash.append(bg_sprite)

    # Add 'PicoGauge' text
    text1 = "PicoGauge"
    text_area1 = label.Label(
        terminalio.FONT,
        text=text1,
        color=0xFFFFFF,  # White
        anchor_point=(0.5, 0.5),
        anchored_position=(DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2 - 10),  # Position adjusted for spacing
        scale=TEXT_SCALE,
    )
    splash.append(text_area1)

    # Add 'Looking for Haltech' text
    text2 = "Looking for Haltech..."
    text_area2 = label.Label(
        terminalio.FONT,
        text=text2,
        color=0xFFFF00,  # Yellow
        anchor_point=(0.5, 0.5),
        anchored_position=(DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2 + 20),  # Positioned below the first line
        scale=1,
    )
    splash.append(text_area2)

    # Set the root group to display the splash screen
    display.root_group = splash

    # Show the startup screen for the specified duration
    start_time = time.monotonic()
    while (time.monotonic() - start_time) < duration:
        time.sleep(1)

def create_labels(display):
    """Create and return display labels for showing CAN data."""
    colors = [0xFF0000, 0x00FF00, 0x0000FF]
    numeric_positions = [(80, 60), (180, 60), (110, 160)]
    label_positions = [(80, 100), (180, 100), (110, 200)]
    text_label_strings = ["MAP", "TPS", "Lambda"]

    main = displayio.Group()
    display.root_group = main

    numeric_labels = []
    for i in range(3):
        numeric_label = label.Label(
            terminalio.FONT,
            text="0",
            color=colors[i],
            anchor_point=(0.5, 0.5),
            anchored_position=numeric_positions[i],
            scale=TEXT_SCALE,
        )
        numeric_labels.append(numeric_label)
        main.append(numeric_label)

    text_labels = []
    for i in range(3):
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

    return numeric_labels, text_labels

def initialize_can():
    """Initialize and configure the CAN bus with filters."""
    print("Initializing CAN")
    cs_pin = board.GP21
    cs = digitalio.DigitalInOut(cs_pin)
    cs.switch_to_output()

    spi_mcp = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP20)
    try:
        mcp = adafruit_mcp2515.MCP2515(
            spi_mcp, cs, baudrate=DATA_RATE, crystal_freq=16000000
        )
        mcp.initialize()  # Ensure the MCP2515 is initialized with default settings
        print("MCP2515 initialized successfully")
    except Exception as e:
        print(f"Error initializing MCP2515: {e}")
        return None, None, None, cs, spi_mcp

    # Clear existing filters
    try:
        mcp.deinit_filtering_registers()
    except Exception as e:
        print(f"Error clearing filters: {e}")

    # Create match filters for each CAN ID
    try:
        match_360 = adafruit_mcp2515.canio.Match(0x360)
        match_368 = adafruit_mcp2515.canio.Match(0x368)
        listener_360 = mcp.listen([match_360], timeout=0.5)
        listener_368 = mcp.listen([match_368], timeout=0.5)
        print("CAN filters and listeners initialized successfully")
    except Exception as e:
        print(f"Error setting up CAN filters/listeners: {e}")
        return mcp, None, None, cs, spi_mcp

    return mcp, listener_360, listener_368, cs, spi_mcp

def process_can_messages(mcp, listener_360, listener_368):
    """Process messages from CAN listeners and return the raw data."""
#    print("Processing messages")
    raw_data = {"MAP": None, "TPS": None, "Lambda": None}

    for listener, can_id in zip([listener_360, listener_368], [0x360, 0x368]):
        message_count = listener.in_waiting()
#        print(f"Message count for ID {can_id}: {message_count}")

        for _ in range(message_count):
            msg = listener.receive()
            if msg is None:
                continue
#            print(f"Received message ID: {msg.id}, Data: {msg.data}")

            if msg.id == can_id:
                if can_id == 0x360:
                    if len(msg.data) >= 6:
                        raw_data["MAP"] = (msg.data[2] << 8) | msg.data[3]
                        raw_data["TPS"] = (msg.data[4] << 8) | msg.data[5]
                elif can_id == 0x368:
                    if len(msg.data) >= 2:
                        raw_data["Lambda"] = (msg.data[0] << 8) | msg.data[1]

#    print(f"Raw data: {raw_data}")
    return raw_data

def convert_raw_data(raw_data):
    """Convert raw data to human-readable format."""
#    print("Converting data")
    converted_values = {}

    if raw_data["MAP"] is not None:
        converted_values["MAP"] = (raw_data["MAP"] / 10) - ATMOS_KPA # Convert raw value to kPa
    if raw_data["TPS"] is not None:
        converted_values["TPS"] = raw_data["TPS"] / 10  # Convert raw value to %
    if raw_data["Lambda"] is not None:
        converted_values["Lambda"] = raw_data["Lambda"] / 1000  # Convert raw value to λ

#    print(f"Converted values: {converted_values}")
    return converted_values

def update_display(numeric_labels, can_values):
    """Update display labels with the latest CAN data."""
#    print(f"Updating display with values: {can_values}")
    if "MAP" in can_values:
        numeric_labels[0].text = f"{can_values['MAP']:.0f}kPa"
    if "TPS" in can_values:
        numeric_labels[1].text = f"{can_values['TPS']:.0f}%"
    if "Lambda" in can_values:
        numeric_labels[2].text = f"{can_values['Lambda']:.2f}"

# Main program execution

def main():
    while True:
        try:
            display = setup_display()
            show_startup_screen(display)

            mcp, listener_360, listener_368, cs, spi_mcp = initialize_can()
            if mcp is None:
                raise RuntimeError("CAN initialization failed")

            last_update = {"MAP": 0, "TPS": 0, "Lambda": 0}
            numeric_labels, text_labels = create_labels(display)

            while True:
                raw_data = process_can_messages(mcp, listener_360, listener_368)
                can_values = convert_raw_data(raw_data)

                current_time = time.monotonic()
                if raw_data["MAP"] is not None and (current_time - last_update["MAP"]) >= UPDATE_INTERVALS["MAP"]:
                    last_update["MAP"] = current_time
                    update_display(numeric_labels, can_values)

                if raw_data["TPS"] is not None and (current_time - last_update["TPS"]) >= UPDATE_INTERVALS["TPS"]:
                    last_update["TPS"] = current_time
                    update_display(numeric_labels, can_values)

                if raw_data["Lambda"] is not None and (current_time - last_update["Lambda"]) >= UPDATE_INTERVALS["Lambda"]:
                    last_update["Lambda"] = current_time
                    update_display(numeric_labels, can_values)

                gc.collect()  # Trigger garbage collection
                time.sleep(0.02)

        except Exception as e:
            print(f"An error occurred: {e}")
            # Optionally, perform a reset
            microcontroller.reset()  # This will reset the Pico
# Run the main program
main()

