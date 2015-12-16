#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import utm
import math
import time
import gzip
import ctypes
import subprocess
import RPi.GPIO as GPIO

libc = ctypes.CDLL("libc.so.6")

powerled = 17
busyled = 27

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(powerled, GPIO.OUT)
GPIO.setup(busyled, GPIO.OUT)
GPIO.output(powerled, 1)

found = True
devices = []

while(True):
    try:
        partitionsFile = open("/proc/partitions")
        lines = partitionsFile.readlines()[2:]
        if len(devices) > 0 and not found:
            devices.pop()
            print("USB-ENHET FRAKOBLET")
        found = False
        for line in lines:
            words = [x.strip() for x in line.split()]
            minorNumber = int(words[1])
            deviceName = words[3]
            if len(devices) > 0:
                for d in devices:
                    if d + "1" == deviceName:
                        found = True
            if minorNumber % 16 == 0:
                path = "/sys/class/block/" + deviceName
                if os.path.islink(path):
                    if os.path.realpath(path).find("/usb") > 0:
                        if not len(devices) > 0:
                            GPIO.output(busyled, 1)
                            GPIO.output(powerled, 0)
                            print("FANT USB-ENHET")
                            devices.append(deviceName)
                            p = subprocess.Popen(["mount", "-t", "auto", "/dev/%s" % deviceName + "1", "/mnt/usb"])
                            p.communicate()
                            libc.sync()
                            if not os.path.exists("/mnt/usb/utm"):
                                os.makedirs("/mnt/usb/utm")
                            if not os.path.exists("/mnt/usb/dp"):
                                os.makedirs("/mnt/usb/dp")
                            if not os.path.exists("/mnt/usb/dpt"):
                                os.makedirs("/mnt/usb/dpt")
                            for rutefil in os.listdir("/mnt/usb"):
                                if(rutefil.endswith(".gz")):
                                    try:
                                        f = gzip.open("/mnt/usb/%s" % rutefil) 
                                        o = open("/mnt/usb/utm/%s" % os.path.splitext(rutefil)[0] + ".csv", "w+", encoding="latin-1")
                                        odp = open("/mnt/usb/%s" % os.path.splitext(rutefil)[0] + ".tmp", "w+", encoding="latin-1")
                                        for line in f:
                                            line = line.decode("utf-8")
                                            odp.write(line)
                                            m = re.match("^(\d*\.\d*) (\d*\.\d*)", line)
                                            if(m):
                                                lat = float(m.group(1)) / 60
                                                lon = float(m.group(2)) / 60
                                                utmd = utm.from_latlon(lat,lon)
                                                o.write("%0.2f" % utmd[0] + "," + "%0.2f" % utmd[1] + ","  + str(utmd[2]) + "," + utmd[3] + "\r\n")
                                                libc.sync()
                                        odp.close()         
                                        proc = subprocess.Popen(["/home/pi/olextodms/Ruter2SDP.pl", "/mnt/usb/%s" % os.path.splitext(rutefil)[0] + ".tmp"], stdout=subprocess.PIPE)
                                        (out, err) = proc.communicate()
                                        fdp = open("/mnt/usb/dp/%s" % os.path.splitext(rutefil)[0] + ".txt", "w+")
                                        out = out.decode("latin-1")
                                        out = out.replace("\n", "\r\n")
                                        fdp.write(out)
                                        fdp.close()
                                        GPIO.output(powerled, 1)
                                        time.sleep(.1)
                                        GPIO.output(powerled, 0)
                                        o.close()
                                        f.close()
                                    except:
                                        print("FILE ERROR")
                                elif(rutefil.endswith(".csv")):
                                    try:
                                        tmpstring = ""
                                        with open("/mnt/usb/%s" % rutefil, "r", errors="ignore") as infile:
                                            for line in infile:
                                                m = re.search("(\d*\.\d*)([N|S]),(\d*\.\d*)([E|W]),(-?\d*)", line)
                                                if m:
                                                    lat = str(float(m.group(1)))
                                                    lon = str(float(m.group(3)))
                                                    dep = str(abs(float(m.group(5))))
                                                    if(m.group(2) == 'S'):
                                                        lat = -lat
                                                    if(m.group(4) == 'W'):
                                                        lon = -lon
                                                    tmpstring = tmpstring+lat+" "+lon+" "+dep+"\n"
                                                    if(len(tmpstring) > 100000):
                                                        outfile = open("/mnt/usb/dpt/%s" % os.path.splitext(rutefil)[0], "a")
                                                        outfile.write(tmpstring)
                                                        outfile.close()
                                                        tmpstring = ""
                                        outfile = open("/mnt/usb/dpt/%s" % os.path.splitext(rutefil)[0], "a")
                                        outfile.write(tmpstring)
                                        outfile.close()
                                        tmpstring = ""
                                    except:
                                        for e in sys.exc_info():
                                            print(e)
                            p = subprocess.Popen(["umount", "/mnt/usb"])
                            p.communicate()
                            print("KONVERTERING FERDIG")
                            GPIO.output(busyled, 0)
                            GPIO.output(powerled, 1)

    except:
        print("ERROR")
        for e in sys.exc_info():
            print(e)
        GPIO.output(powerled, 1)
        GPIO.output(busyled, 0)
    time.sleep(1)
