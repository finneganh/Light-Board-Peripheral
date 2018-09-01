# CircuitPython demo - NeoPixel

import time

import board
import neopixel
import busio
import digitalio

NEOPIXEL_PIN = board.D5

PIXELS_PER_STRIP = 8
STRIP_COUNT = 2

COMMAND_PREFIX = 0xF0
COMMAND_GET_STATUS = 0x10
COMMAND_SET_LIGHT = 0x20
COMMAND_SET_ALL = 0x21
COMMAND_RUN_PRESET = 0x30
COMMAND_SET_PRESET = 0x31

STATE_DISCONNECTED = 0
STATE_CONNECTED = 1
STATE_UNINITIALIZED = 2

strip = neopixel.NeoPixel(
    NEOPIXEL_PIN, PIXELS_PER_STRIP * STRIP_COUNT, brightness=0.3, auto_write=False)
btle = busio.UART(board.TX, board.RX, baudrate=9600, timeout=100)

strip.fill((0, 255, 0))
strip.show()

statusLed = digitalio.DigitalInOut(board.D13)
statusLed.direction = digitalio.Direction.OUTPUT
statusLed.value = False

statusPin = digitalio.DigitalInOut(board.D7)
statusPin.direction = digitalio.Direction.INPUT
statusPin.pull = digitalio.Pull.DOWN

def bufToString(data):
    if data is None:
        return ''
    else:
        return ''.join([chr(b) for b in data])

def sendAtCommand(cmd = False):
    gotResponse = False
    lastCommandTime = 0

    while True:
        if time.time() > lastCommandTime + 2:
            if cmd:
                str = 'AT+' + cmd
            else:
                str = 'AT'

            print(str)
            btle.write(str + '\r\n')

            lastCommandTime = time.time()

        data = btle.read(32)

        if data is None or len(data) is 0:
            if gotResponse:
                return
        else:
            response = bufToString(data)
            print(response, end='')

            if response.startswith('ERR'):
                lastCommandTime = 0
            else:
                gotResponse = True

def initBtle():
    print("Waiting for module ready")
    sendAtCommand()

    print("Getting firmware version")
    sendAtCommand('VERSION')

    print("Setting peripheral mode")
    sendAtCommand('ROLE0')

    print("Getting MAC address")
    sendAtCommand('LADDR')

def readCommandFromBtle():
    data = btle.read(1)
    if data is None or len(data) is 0:
        return (False, data)

    command = data[0]

    if command is COMMAND_SET_LIGHT:
        data = btle.read(4)
        if data is None or len(data) < 4:
            return (False, data)

        s = data[0]
        r = data[1]
        g = data[2]
        b = data[3]
        for i in range(s * PIXELS_PER_STRIP, (s + 1) * PIXELS_PER_STRIP):
            strip[i] = (r, g, b)
        strip.show()

    elif command is COMMAND_SET_ALL:
        data = btle.read(3)
        if data is None or len(data) < 3:
            return (False, data)

        r = data[1]
        g = data[2]
        b = data[3]

        for i in range(STRIP_COUNT * PIXELS_PER_STRIP):
            strip[i] = (r, g, b)
        strip.show()

    return (True, [ord('O'), ord('K')])

def readFromBlte():
    data = btle.read(1)

    if data is not None and len(data) is 1 and data[0] is COMMAND_PREFIX:
        (success, output) = readCommandFromBtle()
        if success:
            # Pad out to 20 bytes to keep the receiving side from waiting
            output += [0] * (20 - len(output))
            btle.write(bytes(output))
        else:
            print(bufToString(output), end="")

    else:
        print(bufToString(data), end="")

def main():
    print("Peripheral started")

    if statusPin.value:
        print("Bluetooth already connected")
        state = STATE_CONNECTED
    else:
        state = STATE_UNINITIALIZED

    while True:
        if statusPin.value:
            if state is not STATE_CONNECTED:
                print("State change: CONNECTED")
                state = STATE_CONNECTED
        else:
            if state is STATE_CONNECTED:
                print("State change: DISCONNECTED")
                state = STATE_DISCONNECTED

        statusLed.value = state is STATE_CONNECTED

        if state is STATE_CONNECTED:
            readFromBlte()
        elif state is STATE_UNINITIALIZED:
            print("Initializing Bluetooth module:")
            initBtle()
            print("Waiting for connection")
            state = STATE_DISCONNECTED


main()
