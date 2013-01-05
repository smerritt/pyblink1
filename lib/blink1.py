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


# from https://github.com/todbot/blink1/blob/master/commandline/blink1-lib.c
# a simple logarithmic -> linear mapping as a sort of gamma correction
# maps from 0-255 to 0-255
def _degamma(n):
    return (((1<<(n/32))-1) + ((1<<(n/32))*((n%32)+1)+15)/32)


class Blink1(object):
    def __init__(self, usbdev):
        self.usbdev = usbdev

    def off(self):
        """
        Turn the light off.
        """
        self.set_rgb((0,0,0))

    def set_rgb(self, rgb_color):
        """
        Set this blink(1) to a specific RGB value.

        :param rgb_color: 3-tuple (R, G, B), where R, G, and B are between
                          0 and 255, inclusive.
        """

        r, g, b = (_degamma(x) for x in rgb_color)

        message = struct.pack(
            'BBBBBBBBB',
            BLINK1_REPORT_ID,
            ord('n'),          # command code: 'set rgb now'
            r, g, b,           # the actual color
            0, 0, 0, 0)        # padding

        self._send_message(message)

    def fade_rgb(self, rgb_color, duration=2):
        """
        Fade this blink(1) to a specific RGB value.

        :param rgb_color: 3-tuple (R, G, B), where R, G, and B are between
                          0 and 255, inclusive.
        :param duration: how long the fade lasts, in seconds. Maximum
                         value is 655.35.

        Note that this method just sends a message to the device; it
        does not wait for the fade to complete.

        """
        if duration <= 0:
            return self.set_rgb(rgb_color)

        r, g, b = (_degamma(x) for x in rgb_color)

        duration = self._normalize_duration(duration)

        message = struct.pack(
            'BBBBBBBBB',
            BLINK1_REPORT_ID,
            ord('c'),            # command code: 'fade to rgb'
            r, g, b,             # the color
            duration // 256,     # how long to take (high byte)
            duration % 256,      # how long to take (low byte)
            0, 0)                # padding

        self._send_message(message)

    def play(self, play=True):
        """
        Begin playback of the blink(1)'s internal pattern buffer.

        Playback continues until .stop() is called.

        """
        message = struct.pack(
            'BBBBBBBBB',
            BLINK1_REPORT_ID,
            ord('p'),            # command code: 'play'
            1 if play else 0,    # whether to start or stop playback
            0, 0, 0, 0, 0, 0)    # padding
        self._send_message(message)

    def stop(self):
        """
        Stop playback of the blink(1)'s internal pattern buffer.

        """
        self.play(False)

    def write_pattern_line(self, pos, rgb_color, duration=2, degamma=True):
        """
        Write a pattern line to the blink(1)'s internal pattern buffer.

        The pattern buffer has 12 positions, each containing:
          - an RGB color
          - a duration

        When .play() is called, the blink(1) will cycle through its
        pattern buffer, taking <duration> to fade to <color> at each
        step.

        :param pos: position to write, between 0 and 11 inclusive.
        :param rgb_color: 3-tuple (R, G, B), where R, G, and B are between
                          0 and 255, inclusive.
        :param duration: how long the fade lasts, in seconds. Maximum
                         value is 655.35.
        """
        duration = self._normalize_duration(duration)
        r, g, b = rgb_color
        if degamma:
            r, g, b = _degamma(r), _degamma(g), _degamma(b)

        message = struct.pack(
            'BBBBBBBBB',
            BLINK1_REPORT_ID,
            ord('P'),            # command code: 'write pattern line'
            r, g, b,             # the color
            duration // 256,     # how long to take (high byte)
            duration % 256,      # how long to take (low byte)
            pos,                 # position to write
            0)                   # padding
        self._send_message(message)

    def set_pattern(self, pattern):
        """
        Write a repeating pattern to the blink(1)'s internal pattern buffer.

        The pattern is a sequence of between 2 and 12 (inclusive)
        pattern specifiers that make up a pattern that will repeat.

        Each specifier is a 2-tuple (time, (r, g, b)). <time> is how
        long, in seconds, to take when fading to the color (r, g, b).

        The pattern buffer has 12 positions, each containing:
          - an RGB color
          - a duration

        This method simply sets the pattern; it does not play it. Call
        .play() to begin playback.

        """
        if len(pattern) < 2 or len(pattern) > 12:
            raise ValueError(
                "Pattern length must be between 2 and 12; was %d"
                % len(pattern))

        pattern = [(tp[0], tuple(_degamma(c) for c in tp[1]))
                    for tp in pattern]

        interpolated = []
        if len(pattern) < 12:
            npoints = 12 - len(pattern) + 2
            duration = float(pattern[-1][0]) / npoints

            left_color = pattern[-2][1]
            right_color = pattern[-1][1]

            for i in xrange(1, npoints):
                color = []
                for j in xrange(len(left_color)):
                    left = float(left_color[j])
                    right = float(right_color[j])
                    # assume the points are x-distance 1 apart; it
                    # comes out in the wash
                    color.append(int(left + (right - left)*i/npoints))
                interpolated.append((duration, tuple(color)))

            pattern = list(pattern[0:-1])
            pattern.append(interpolated.pop(0))

        for i, pattern_specifier in enumerate(pattern + interpolated):
            duration, color = pattern_specifier
            self.write_pattern_line(i, color, duration, degamma=False)

    def _normalize_duration(self, raw_duration):
        """
        Convert duration to centiseconds. Durations in excess of
        655.35 seconds will be silently reduced to 655.35.

        """
        # Apparently the device wants centiseconds, and it wants them
        # in a 16-bit unsigned integer.
        return int(min(raw_duration, 655.35) * 100)

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


if __name__ == '__main__':
    dev = find()[0]
    dev.set_pattern([(1, (0xff,   0,   0)),
                     (1, (0xff, 0xa5,  0)),
                     (1, (0xff, 0xff,  0)),
                     (1, (0,    0x80,  0)),
                     (1, (0,    0,     0xff)),
                     (1, (0x4b, 0,     0x82)),
                     (1, (0xee, 0x82,  0xee)),
                     (1, (0,    0,     0)),
                     (1, (0,    0,     0))])
    dev.play()
