
class Preset:
  def __init__(self, num, canWrite = False):
    self.num = num
    self.values = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    if num is 0:
      self.values = [255, 0, 0, 0, 0, 255, 255, 0, 255, 0, 255, 0]
    elif num is 1:
      self.values = [27, 231, 0, 0, 121, 151, 95, 0, 135, 103, 151, 0]
    elif num is 2:
      self.values = [55, 0, 0, 71, 40, 0, 27, 55, 0, 254, 229, 153]

  def setValues(self, v):
    self.values = v

  def getValues(self):
    return self.values
