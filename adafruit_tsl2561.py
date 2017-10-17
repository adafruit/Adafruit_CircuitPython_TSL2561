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
`adafruit_tsl2561`
====================================================

CircuitPython driver for TSL2561 Light Sensor.

* Author(s): Carter Nelson
"""
from adafruit_bus_device.i2c_device import I2CDevice

TSL2561_DEFAULT_ADDRESS     = 0x39
TSL2561_COMMAND_BIT         = 0x80
TSL2561_WORD_BIT            = 0x20

TSL2561_CONTROL_POWERON     = 0x03
TSL2561_CONTROL_POWEROFF    = 0x00

TSL2561_REGISTER_CONTROL    = 0x00
TSL2561_REGISTER_TIMING     = 0x01
TSL2561_REGISTER_CHAN0_LOW  = 0x0C
TSL2561_REGISTER_CHAN1_LOW  = 0x0E
TSL2561_REGISTER_ID         = 0x0A

TSL2561_GAIN_SCALE = (16, 1)
TSL2561_TIME_SCALE = (1 / 0.034, 1 / 0.252, 1)
TSL2561_CLIP_THRESHOLD = (4900, 37000, 65000)

class TSL2561():
    """Class which provides interface to TSL2561 light sensor."""

    def __init__(self, i2c=None, address=TSL2561_DEFAULT_ADDRESS, **kwargs):
        self.buf = bytearray(3)
        if i2c is None:
            import board
            import busio
            i2c = busio.I2C(board.SCL, board.SDA)
        self.i2c_device = I2CDevice(i2c, address)
        self.enabled = True

    @property
    def id(self):
        """A tuple containing the part number and the revision number."""
        id = self._read_register(TSL2561_REGISTER_ID)
        partno = (id >> 4 ) & 0x0f
        revno = id & 0x0f
        return (partno, revno)

    @property
    def enabled(self):
        """The state of the sensor."""
        return (self._read_register(TSL2561_REGISTER_CONTROL) & 0x03) != 0

    @enabled.setter
    def enabled(self, enable):
        """Enable or disable the sensor."""
        if enable:
            self._enable()
        else:
            self._disable()

    @property
    def light(self):
        """The computed lux value."""
        return self._compute_lux()

    @property
    def broadband(self):
        """The broadband channel value."""
        return self._read_broadband()

    @property
    def infrared(self):
        """The infrared channel value."""
        return self._read_infrared()

    @property
    def luminosity(self):
        """The overall luminosity as a tuple containing the broadband
        channel and the infrared channel value."""
        return (self.broadband, self.infrared)

    @property
    def gain(self):
        """The gain. 0:1x, 1:16x."""
        return self._read_register(TSL2561_REGISTER_TIMING) >> 4 & 0x01

    @gain.setter
    def gain(self, value):
        """Set the gain. 0:1x, 1:16x."""
        value &= 0x01
        value <<= 4
        current = self._read_register(TSL2561_REGISTER_TIMING)
        self.buf[0] = TSL2561_COMMAND_BIT | TSL2561_REGISTER_TIMING
        self.buf[1] = (current & 0xef) | value
        with self.i2c_device as i2c:
            i2c.write(self.buf, end=2)

    @property
    def integration_time(self):
        """The integration time. 0:13.7ms, 1:101ms, 2:402ms, or 3:manual"""
        current = self._read_register(TSL2561_REGISTER_TIMING)
        return current & 0x03

    @integration_time.setter
    def integration_time(self, time):
        """Set the integration time. 0:13.7ms, 1:101ms, 2:402ms, or 3:manual."""
        time &= 0x03
        current = self._read_register(TSL2561_REGISTER_TIMING)
        self.buf[0] = TSL2561_COMMAND_BIT | TSL2561_REGISTER_TIMING
        self.buf[1] = (current & 0xfc) | time
        with self.i2c_device as i2c:
            i2c.write(self.buf, end=2)

    def _compute_lux(self):
        """Based on datasheet for FN package."""
        ch0, ch1 = self.luminosity
        if ch0 == 0: return None
        if ch0 > TSL2561_CLIP_THRESHOLD[self.integration_time]: return None
        if ch1 > TSL2561_CLIP_THRESHOLD[self.integration_time]: return None
        ratio = ch1 / ch0
        if ratio > 0 and ratio <= 0.50:
            lux = 0.0304 * ch0 - 0.062 * ch0 * ratio**1.4
        elif ratio > 0.50 and ratio <= 0.61:
            lux = 0.0224 * ch0 - 0.031 * ch1
        elif ratio > 0.61 and ratio <= 0.80:
            lux = 0.0128 * ch0 - 0.0153 * ch1
        elif ratio > 0.80 and ratio <= 1.30:
            lux = 0.00146 * ch0 - 0.00112 * ch1
        elif ratio > 1.30:
            lux = 0
        # Pretty sure the floating point math formula on pg. 23 of datasheet
        # is based on 16x gain and 402ms integration time. Need to scale
        # result for other settings.
        # Scale for gain.
        lux *= TSL2561_GAIN_SCALE[self.gain]
        # Scale for integration time.
        lux *= TSL2561_TIME_SCALE[self.integration_time]
        return lux

    def _enable(self):
        self._write_control_register(TSL2561_CONTROL_POWERON)

    def _disable(self):
        self._write_control_register(TSL2561_CONTROL_POWEROFF)

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

    def _read_broadband(self):
        low, high = self._read_register(TSL2561_REGISTER_CHAN0_LOW, 2)
        return high << 8 | low

    def _read_infrared(self):
        low, high = self._read_register(TSL2561_REGISTER_CHAN1_LOW, 2)
        return high << 8 | low
