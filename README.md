pyblink1
========

pyblink1 is a Python library for the
[blink(1)](http://blink1.thingm.com) USB RGB LED.

Example
=======
```python
import blink1

devices = blink1.find()
led = devices[0]

led.set_rgb((100, 0, 100))         # set to purple
led.fade_rgb((200, 100, 0), 2.5)   # fade to yellow over 2.5 seconds

led.write_pattern_line(0, (255, 0, 0), 1.5)  # set pattern 0 to fade to red over 1.5s
led.write_pattern_line(1, (255, 0, 0))       # set pattern 1 to fade to green over 2s

led.play()      # play internal pattern
led.stop()      # stop playing internal pattern
```


Requirements
============
 - pyusb >= 1.0.0
 - a pyusb backend such as libusb or openusb
 - probably has to run with root privileges on Linux in order to send raw USB messages

License
=======
[Apache 2.0](http://www.apache.org/licenses/LICENSE-2.0)