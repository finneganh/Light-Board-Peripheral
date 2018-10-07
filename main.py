# CircuitPython demo - NeoPixel

import time

import board
import neopixel
import busio
import digitalio

from preset import Preset

PROD_MODE = False
NEOPIXEL_PIN = board.D5

# Derived from: http://www.easyrgb.com/en/math.php#text2
#
# Input range: 0–1
# Output range: 0—255
def hsl2rgb(h, l):
    h = h % 1.0

    if l < 0.5:
        v2 = l * 2
    else:
        v2 = 1

    v1 = 2 * l - v2

    r = 255 * hue2rgb(v1, v2, h + 0.33333)
    g = 255 * hue2rgb(v1, v2, h)
    b = 255 * hue2rgb(v1, v2, h - 0.33333)

    return (int(r), int(g), int(b))

def hue2rgb(v1, v2, vh):
  if vh < 0:
    vh += 1

  if vh > 1:
    vh -= 1
  
  if vh * 6 < 1:
    return v1 + (v2 - v1) * 6 * vh

  if vh * 2 < 1:
    return v2
  
  if vh * 3 < 2:
    return v1 + (v2 - v1) * (0.666666 - vh) * 6

  return v1

COLORS = [
    (255, 0, 0),
    (255, 150, 0),
    (0, 255, 0),
    (0, 255, 255),
    (0, 0, 255),
    (180, 0, 255),
]

PIXELS_PER_STRIP = 8 if PROD_MODE else 2
STRIP_COUNT = 4

COMMAND_PREFIX = 0xF0
COMMAND_GET_STATUS = 0x10
COMMAND_SET_LIGHT = 0x20
COMMAND_RUN_PRESET = 0x30
COMMAND_SET_PRESET = 0x31

STATE_DISCONNECTED = 0
STATE_CONNECTED = 1
STATE_UNINITIALIZED = 2

STAR_MODE_COUNT = 2

BRIGHTNESS = 0.3 if PROD_MODE else 0.1

strip = neopixel.NeoPixel(
    NEOPIXEL_PIN, PIXELS_PER_STRIP * STRIP_COUNT, brightness=BRIGHTNESS, auto_write=False)
btle = busio.UART(board.TX, board.RX, baudrate=9600, timeout=3)

strip.fill((0, 0, 0))
strip.show()

statusInIo = digitalio.DigitalInOut(board.D7)
statusInIo.direction = digitalio.Direction.INPUT
statusInIo.pull = digitalio.Pull.DOWN

PRESETS = [
    Preset(0),
    Preset(1),
    Preset(2),
]

star_mode = None
star_step = 0


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
    # print("Waiting for module ready")
    sendAtCommand()

    # print("Getting firmware version")
    # sendAtCommand('VERSION')

    # print("Setting peripheral mode")
    sendAtCommand('ROLE0')

    # print("Getting MAC address")
    # sendAtCommand('LADDR')

animation_array = []

def readCommandFromBtle():
    global animation_array, star_mode, star_step

    data = btle.read(1)
    if data is None or len(data) is 0:
        return (False, data)

    command = data[0]

    if command is COMMAND_SET_LIGHT:
        data = btle.read(3)
        if data is None or len(data) < 3:
            return (False, data)

        s = data[0]
        hue = data[1] / 255
        brightness = data[2] / 255

        setStripValue(s, hsl2rgb(hue, brightness))
        animation_array = []
        star_mode = None

        strip.show()
    elif command is COMMAND_SET_PRESET:
        data = btle.read(1)
        if data is None or len(data) < 1:
            return (False, data)

        p = data[0]
        if not (0 <= p < 3):
            return (False, data)
        
        PRESETS[p].setValues(getStripValues())
        # print("Setting ", p, " to ", getStripValues())

    elif command is COMMAND_RUN_PRESET:
        data = btle.read(1)
        if data is None or len(data) < 1:
            return (False, data)

        p = data[0]
        animation_array = []

        if p == 4:
            star_step = 0
            if star_mode == None:
                star_mode = 0
            else:
                star_mode = (star_mode + 1) % STAR_MODE_COUNT
        elif 0 <= p < len(PRESETS):
            star_mode = None

            vals = PRESETS[p].getValues()
            cur_vals = getStripValues()

            for i in range(1, 11):
                mid_vals = []
                d_new = (11 - i) / 10.0
                d_old = (i - 1) / 10.0

                for j in range(len(cur_vals)):
                    mid_vals.append(int(cur_vals[j] * d_old + vals[j] * d_new))

                animation_array.append(mid_vals)
        else:
            return (False, data)

    return (True, [255])

def setStripValue(s, rgb):
    if s == 255:
        start = 0
        end = STRIP_COUNT - 1
    else:
        start = s
        end = s

    for i in range(start * PIXELS_PER_STRIP, (end + 1) * PIXELS_PER_STRIP):
        strip[i] = rgb

def setStripValues(vals):
    for i in range(STRIP_COUNT):
        offset = i * 3
        setStripValue(i, (vals[offset], vals[offset + 1], vals[offset + 2]))

def getStripValues():
    out = []
    for i in range(STRIP_COUNT):
        out.extend(strip[i * PIXELS_PER_STRIP])
    return out

def readFromBlte():
    data = btle.read(1)

    if data is not None and len(data) is 1 and data[0] is COMMAND_PREFIX:
        (success, output) = readCommandFromBtle()
        if success:
            # Pad out to 20 bytes to keep the receiving side from waiting
            output += [0] * (20 - len(output))
            btle.write(bytes(output))
            return True
    return False

last_animate = 0

def animate():
    global last_animate, animation_array, star_mode, star_step

    cur_t = time.monotonic()
    if last_animate + 0.03 > cur_t:
        return

    last_animate = cur_t

    if star_mode in [0, 1]:
        offset = 0.25 if star_mode == 1 else 0

        s = star_step / 1000.0

        setStripValue(0, hsl2rgb(s, 0.49))
        setStripValue(1, hsl2rgb((s + offset), 0.49))
        setStripValue(2, hsl2rgb((s + offset * 2), 0.49))
        setStripValue(3, hsl2rgb((s + 3 * offset), 0.49))

    elif len(animation_array) > 0:
        setStripValues(animation_array.pop())

    else:
        return

    strip.show()
    star_step = (star_step + 1) % 1000


def main():
    # print("Peripheral started")

    setStripValues(COLORS[0] + COLORS[2] + COLORS[5] + COLORS[3])
    strip.show()

    if statusInIo.value:
        # print("Bluetooth already connected")
        state = STATE_CONNECTED
    else:
        state = STATE_UNINITIALIZED

    while True:
        if statusInIo.value:
            if state is not STATE_CONNECTED:
                # print("State change: CONNECTED")
                state = STATE_CONNECTED
        else:
            if state is STATE_CONNECTED:
                # print("State change: DISCONNECTED")
                state = STATE_DISCONNECTED

        if state is STATE_CONNECTED:
            if not readFromBlte():
                animate()
        elif state is STATE_UNINITIALIZED:
            # print("Initializing Bluetooth module:")
            initBtle()
            # print("Waiting for connection")
            state = STATE_DISCONNECTED


main()
