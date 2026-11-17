"""Find and test a USB relay board — run this on your laptop before wiring pumps.

  python -m drinkbot.relaytest            # list serial ports
  python -m drinkbot.relaytest COM3       # click relays 1-8 one at a time (1 s each)
  python -m drinkbot.relaytest COM3 3 5   # run relay 3 for 5 seconds (prime / test a pump)
"""
import sys
import time

from .hardware import UsbRelayBoard


def main():
    if len(sys.argv) < 2:
        from serial.tools import list_ports
        ports = list(list_ports.comports())
        if not ports:
            print("No serial ports found. Plug in the relay board (and install the CH340 driver on Windows/Mac).")
        for p in ports:
            hint = "  <- probably the relay board" if "CH340" in (p.description or "") or p.vid == 0x1A86 else ""
            print(f"{p.device:<28} {p.description}{hint}")
        print("\nThen: python -m drinkbot.relaytest <port>")
        return
    board = UsbRelayBoard(sys.argv[1])
    try:
        if len(sys.argv) >= 3:
            ch, secs = int(sys.argv[2]), float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
            print(f"Relay {ch} ON for {secs:g}s")
            board.set(ch, True)
            time.sleep(secs)
        else:
            for ch in range(1, 9):
                print(f"Relay {ch}: click")
                board.set(ch, True)
                time.sleep(1)
                board.set(ch, False)
                time.sleep(0.3)
    finally:
        for ch in range(1, 9):
            board.set(ch, False)
        board.close()
        print("All relays off.")


if __name__ == "__main__":
    main()
