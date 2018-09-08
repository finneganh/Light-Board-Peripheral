
class Preset:
  def __init__(self, num, canWrite = False):
    self.num = num
    self.values = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

  def setValues(self, v):
    self.values = v

  def getValues(self):
    return self.values
