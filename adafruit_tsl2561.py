# The MIT License (MIT)
#
# Copyright (c) 2017 Carter Nelson for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_CircuitPython_TSL2561`
====================================================

CircuitPython driver for TSL2561 Light Sensor.

* Author(s): Carter Nelson
"""
from adafruit_bus_device.i2c_device import I2CDevice

TSL2561_DEFAULT_ADDRESS = 0x39
TSL2561_COMMAND_BIT = 0x80
TSL2561_WORD_BIT = 0x20

TSL2561_CONTROL_POWERON = 0x03
TSL2561_CONTROL_POWEROFF = 0x00

TSL2561_REGISTER_CONTROL = 0x00
TSL2561_REGISTER_TIMING = 0x01
TSL2561_REGISTER_CHAN0_LOW = 0x0C
TSL2561_REGISTER_CHAN1_LOW = 0x0E
TSL2561_REGISTER_ID = 0x0A


class TSL2561():

    def __init__(self, address=TSL2561_DEFAULT_ADDRESS, i2c=None, **kwargs):
        self.buf = bytearray(3)
        self._enabled = False
        if i2c is None:
            import board
            import busio
            i2c = busio.I2C(board.SCL, board.SDA)
        self.i2c_device = I2CDevice(i2c, address)

    @property
    def id(self, ):
        """A tuple containing the part number and the revision number."""
        id = self._read_register(TSL2561_REGISTER_ID)
        partno = (id >> 4 ) & 0x0f
        revno = id & 0x0f
        return (partno, revno)

    @property
    def enabled(self, ):
        """The state of the sensor."""
        return self._enabled

    @enabled.setter
    def enabled(self, enable):
        """Enable or disable the sensor."""
        if enable:
            self._enable()
        else:
            self._disable()

    @property
    def lux(self, ):
        """The computed lux value."""
        return self._compute_lux()

    @property
    def broadband(self, ):
        """The broadband channel value."""
        return self._read_broadband()

    @property
    def infrared(self, ):
        """The infrared channel value."""
        return self._read_infrared()

    @property
    def luminosity(self, ):
        """The overall luminosity as a tuple containing the broadband
        channel and the infrared channel value."""
        return (self.broadband, self.infrared)

    @property
    def gain(self, ):
        return self._read_register(TSL2561_REGISTER_TIMING) >> 4 & 0x01

    @gain.setter
    def gain(self, value):
        value &= 0x01
        value <<= 4
        current = self._read_register(TSL2561_REGISTER_TIMING)
        self.buf[0] = TSL2561_COMMAND_BIT | TSL2561_REGISTER_TIMING
        self.buf[1] = (current & 0xef) | value
        with self.i2c_device as i2c:
            i2c.write(self.buf, end=2)

    @property
    def integration_time(self, ):
        current = self._read_register(TSL2561_REGISTER_TIMING)
        return current & 0x03

    @integration_time.setter
    def integration_time(self, time):
        time &= 0x03
        current = self._read_register(TSL2561_REGISTER_TIMING)
        self.buf[0] = TSL2561_COMMAND_BIT | TSL2561_REGISTER_TIMING
        self.buf[1] = (current & 0xfc) | time
        with self.i2c_device as i2c:
            i2c.write(self.buf, end=2)

    def _compute_lux(self, ):
        pass

    def _enable(self, ):
        self._write_control_register(TSL2561_CONTROL_POWERON)
        self._enabled = True

    def _disable(self, ):
        self._write_control_register(TSL2561_CONTROL_POWEROFF)
        self._enabled = False

    def _read_register(self, reg, count=1):
        self.buf[0] = TSL2561_COMMAND_BIT | reg
        if count == 2:
            self.buf[0] |= TSL2561_WORD_BIT
        with self.i2c_device as i2c:
            i2c.write(self.buf, end=1, stop=False)
            i2c.read_into(self.buf, start=1)
        if count == 1:
            return (self.buf[1])
        elif count == 2:
            return (self.buf[1], self.buf[2])

    def _write_control_register(self, reg):
        self.buf[0] = TSL2561_COMMAND_BIT | TSL2561_REGISTER_CONTROL
        self.buf[1] = reg
        with self.i2c_device as i2c:
            i2c.write(self.buf, end=2)


    def _read_broadband(self, ):
#  *broadband = read16(TSL2561_COMMAND_BIT | TSL2561_WORD_BIT | TSL2561_REGISTER_CHAN0_LOW);
        low, high = self._read_register(TSL2561_REGISTER_CHAN0_LOW, 2)
        return high << 8 | low

    def _read_infrared(self, ):
#  *ir = read16(TSL2561_COMMAND_BIT | TSL2561_WORD_BIT | TSL2561_REGISTER_CHAN1_LOW);
        low, high = self._read_register(TSL2561_REGISTER_CHAN1_LOW, 2)
        return high << 8 | low
