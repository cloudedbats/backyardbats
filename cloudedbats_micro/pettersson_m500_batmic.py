#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Project: http://cloudedbats.org
# Copyright (c) 2016 Arnold Andreasson 
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).
from __future__ import unicode_literals

import datetime
import wave
import usb.core

class PetterssonM500BatMic(object):
    """ Class used for control of the Pettersson M500 USB Ultrasound Microphone. 
        More info at http://batsound.com/
        
        Normally the M500 should be accessed from Windows systems, but this class 
        makes it possible to call it from Linux.
        
        Installation instructions for pyusb: https://github.com/walac/pyusb
        
        Since pyusb access hardware directly 'udev rules' must be created. 
        During test it is possible to run it as a 'sudo' user. Example for
        execution of the test case at the end of this file:
        > sudo python pettersson_m500_batmic.py 
        
        More info about adding 'udev rules':
        http://stackoverflow.com/questions/3738173/why-does-pyusb-libusb-require-root-sudo-permissions-on-linux 
    """
    def __init__(self):
        """ """
        self._device = None
        self._endpoint_out = None
        self._endpoint_in = None
        #
        self._init_sound_card()

    def start_stream(self):
        """ """
        self._send_command('01')

    def stop_stream(self):
        """ """
        self._send_command('04')

    def read_stream(self):
        """ """
        return self._endpoint_in.read(0x10000, 2000) # Size = 65536, timeout = 2 sec.

    def led_on(self):
        """ """
        self._send_command('03')

    def led_flash(self):
        """ """
        self._send_command('02')
        
    # --- Internal methods. --- 

    def _init_sound_card(self):
        """ """
        # Vendor and product number for Pettersson M500.
        self._device = usb.core.find(idVendor=0x287d, idProduct=0x0146)
        # Use first configuration.
        self._device.set_configuration()
        configuration = self._device.get_active_configuration()
        interface = configuration[(0,0)]
        # List all endpoints.
#         decriptors = usb.util.find_descriptor(interface, find_all=True)
#         for descr in decriptors:
#             print(unicode(descr))
        # Find endpoint-OUT. For commands.
        self._endpoint_out = usb.util.find_descriptor(interface,
            custom_match = lambda e: 
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        # Find endpoint-IN. For sound stream.
        self._endpoint_in = usb.util.find_descriptor(interface,
            custom_match = lambda e: 
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

    def _send_command(self, command):
        """ Commands: '01': Stream on, '02': LED flash, '03': LED on, '04': Stream off. """
        # Build command string.
        cmd_string =  '4261744d6963'# Signature: ASCII for 'BatMic'.
        cmd_string += command
        cmd_string += '20a10700' # Sfreq. 500000 Hz = x07a120, reversed byte order.
        cmd_string += '00400000' # Ssize, reversed byte order.
        cmd_string += '00000000' # Filter.
        cmd_string += '00' # Stereo.
        cmd_string += '00' # Trig.
        cmd_string += 'ff' if command in ['02', '03'] else '00' # Infinite.
        cmd_string += '00000000000000000000' # Fill, 10 bytes.
        # Send command to M500.
        self._endpoint_out.write(cmd_string.decode('hex'), 1000) # Timeout = 1 sec.


### FOR TEST. ###
if __name__ == "__main__":
    """ """
    # Set record length for this test.
    rec_length_in_minutes = 0.5
    try:
        batmic = PetterssonM500BatMic()
        # Create wave outfile.
        wave_file = wave.open('pettersson-m500.wav', 'w')
        wave_file.setnchannels(1) # 1 = Mono.
        wave_file.setsampwidth(2) # 2 = 16 bits.
        wave_file.setframerate(50000) # TE, Time Expansion 10x (sampling freq. 50kHz instead of 500kHz).
        try:
            # Start M500 stream and LED.
            batmic.start_stream()
            batmic.led_on() # Alternative: batmic.led_flash()
            # Calculate end time.
            end_time = datetime.datetime.now() + datetime.timedelta(minutes = rec_length_in_minutes)
            print('M500 rec. started at: ' + unicode(datetime.datetime.now()) + 
                  ', end time: ' + unicode(end_time))
            # Write to wave file.
            while datetime.datetime.now() < end_time: 
                data = batmic.read_stream()
                wave_file.writeframes(data.tostring())
            # Stop M500 and wave file.
            batmic.stop_stream()
            wave_file.close()
            print('M500 rec. finished.')
        finally:
            batmic.stop_stream()
    except Exception as e:
        print('M500 test failed: ' + unicode(e))
        raise # Raise exception again to show traceback.

