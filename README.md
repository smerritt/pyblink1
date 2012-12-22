pyblink1
========

pyblink1 is a Python binding for the
[blink(1)](http://blink1.thingm.com) USB RGB LED.

Example
=======
```python
import blink1

devices = blink1.find()
led = devices[0]

led.set_rgb(100, 0, 100)         # set to purple
led.fade_rgb(2.5, 200, 100, 0)   # fade to yellow over 2.5 seconds
```


Requirements
============
 - pyusb >= 1.0.0
 - probably has to run with root privileges on Linux in order to send raw USB messages