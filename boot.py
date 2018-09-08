import board
import digitalio
import storage
 
allowWriteIo = digitalio.DigitalInOut(board.D2)
allowWriteIo.direction = digitalio.Direction.INPUT
allowWriteIo.pull = digitalio.Pull.UP
 
# If the D0 is connected to ground with a wire
# CircuitPython can write to the drive
storage.remount("/", allowWriteIo.value)
