#!/usr/bin/env python
# Copyright 2012 Samuel N. Merritt <spam@andcheese.org>
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import struct
import usb.core
import usb.util

BLINK1_VENDOR_ID = 10168
BLINK1_PRODUCT_ID = 493
BLINK1_REPORT_ID = 1


def find():
    """
    Locate all attached blink(1) devices and return a Blink1 object
    for each one.
    """

    return [Blink1(usbdev) for usbdev in
            usb.core.find(idVendor=BLINK1_VENDOR_ID,
                          idProduct=BLINK1_PRODUCT_ID,
                          find_all=True)]


class Blink1(object):
    def __init__(self, usbdev):
        self.usbdev = usbdev

    def setrgb(self, r, g, b):
        """
        Set this blink(1) to a specific RGB value.

        :param r: red value: an integer between 0 and 255, inclusive.
        :param g: green value: an integer between 0 and 255, inclusive.
        :param b: blue value: an integer between 0 and 255, inclusive.

        """
        message = struct.pack(
            'BBBBBBBBB',
            BLINK1_REPORT_ID,
            ord('n'),          # command code: 'set rgb now'
            r, g, b,           # the actual color
            0, 0, 0, 0)        # padding?

        self._send_message(message)

    def fadergb(self, duration, r, g, b):
        """
        Fade this blink(1) to a specific RGB value.

        :param duration: how long the fade lasts, in seconds. Maximum
                         value is 655.35.
        :param r: red value: an integer between 0 and 255, inclusive.
        :param g: green value: an integer between 0 and 255, inclusive.
        :param b: blue value: an integer between 0 and 255, inclusive.

        Note that this method just sends a message to the device; it
        does not wait for the fade to complete.

        """
        if duration <= 0:
            return self.setrgb(r, g, b)

        # Apparently the device wants centiseconds, and it wants them
        # in a 16-bit unsigned integer.
        duration = min(duration, 655.35)
        duration_cs = int(duration * 100)

        message = struct.pack(
            'BBBBBBBBB',
            BLINK1_REPORT_ID,
            ord('c'),            # command code: 'fade to rgb'
            r, g, b,             # the color
            duration_cs // 256,  # how long to take (high byte)
            duration_cs % 256,   # how long to take (low byte)
            0, 0)                # padding

        self._send_message(message)

    def _send_message(self, message):
        try:
            # On Linux, you can't send USB control messages to a
            # device that's got a kernel driver attached to it. When
            # you plug in the blink(1), the kernel notices that it's a
            # HID of a type it doesn't know about, and so it attaches
            # its hidraw driver to the blink(1). Thus, in order to
            # send control messages to it, we have to tell the kernel
            # to take its driver and shove it.
            self.usbdev.detach_kernel_driver(0)
        except usb.core.USBError:
            # Detaching the driver has to happen exactly once after
            # the device is plugged in. Subsequent attempts raise
            # errors, which we ignore.
            #
            # Also, on non-Linux OSes, trying to detach at all may
            # raise an error, which we also ignore.
            pass

        try:
            # On Linux, you have to attach to the interface after you
            # detach the kernel driver.
            self.usbdev._ctx.managed_claim_interface(self.usbdev, 0)
        except usb.core.USBError:
            # On non-Linux, this just raises an error.
            pass

            

        self.usbdev.ctrl_transfer(
            # TYPE_CLASS: class-specific request. That is, we're
            # making a request that is specific to the class of the
            # device (for us, HID), not a standard
            # all-devices-must-support-it request.
            #
            # RECIP_INTERFACE: send it to, uh, the recipient's, um...
            # interface? maybe?
            #
            # ENDPOINT_OUT: this is the standard endpoint that control
            # messages go to.
            usb.TYPE_CLASS | usb.RECIP_INTERFACE | usb.ENDPOINT_OUT,

            # (3 << 8) == HID setreport (send data to device)
            # not sure why the report ID ends up in here twice, though
            (3 << 8) | BLINK1_REPORT_ID,

            # wValue, wIndex: "Use varies according to request",
            # according to <http://www.usbmadesimple.co.uk/ums_4.htm>.
            #
            # Evidently, this request wants zeros.
            0, 0,

            # The 9-byte message.
            message)

        # wave a dead chicken over it
        usb.util.dispose_resources(self.usbdev)


if __name__ == '__main__':
    dev = find()[0]
    dev.setrgb(200,0,0)
    dev.fadergb(2.0, 0, 200, 0)
