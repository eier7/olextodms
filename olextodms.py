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
import datetime
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

def SOSI(coords, filnavn, timestamp):
    sosiut = open("/mnt/usb/sosi/%s" % os.path.splitext(filnavn)[0] + ".sos", "w+", encoding='iso8859-10')
    sosiut.write(".HODE\n")
    sosiut.write("..TEGNSETT ISO8859-10\n")
    sosiut.write("..TRANSPAR\n")
    sosiut.write("...KOORDSYS 23\n")
    sosiut.write("...ORIGO-N\xd8 0 0\n")
    sosiut.write("...ENHET 0.01\n") #centimeter)
    sosiut.write("..SOSI-VERSJON 4.0\n")
    sosiut.write("..SOSI-NIV\xc5 4\n")
    sosiut.write("..OMR\xc5DE\n")
    xmin = coords[0][0]
    ymin = coords[0][1]
    xmax = 0
    ymax = 0
    for c in coords:
        xmin = min(xmin, c[0])
        ymin = min(ymin, c[1])
        xmax = max(xmax, c[0])
        ymax = max(ymax, c[1])
    xmin = (xmin/100)-100
    ymin = (ymin/100)-100
    xmax = (xmax/100)+100
    ymax = (ymax/100)+100
    sosiut.write("...MIN-N\xd8 "+ str(xmin)+" "+ str(ymin)+"\n")
    sosiut.write("...MAX-N\xd8 "+ str(xmax)+" "+ str(ymax)+"\n")
    sosiut.write("..INNHOLD\n")
    sosiut.write("...PRODUKTSPEK\n")
    sosiut.write(".KURVE 1:\n")
    sosiut.write("..OBJTYPE Kabel\n")
    try:
        tid = datetime.datetime.fromtimestamp(int(timestamp)).strftime("%Y%m%d")
    except:
        tid = "00000000"
    sosiut.write("..DATAFANGSTDATO "+tid+"\n")
    sosiut.write("..N\xd8\n")
    for p in coords:
        sosiut.write(str(p[0])+" "+str(p[1])+"\n")

    sosiut.write(".SLUTT\n")
    sosiut.close()

def csvtilsosi(filnavn, timestamp):
    coords = []
    with open("/mnt/usb/utm/%s" % filnavn, "r", errors="ignore") as infile:
        for line in infile:
            m = re.search("(-?\d*\.\d*),(-?\d*\.\d*),(\d*),(\D)", line)
            if m:
              coords.append([int(float(m.group(2))*100), int(float(m.group(1))*100), m.group(3), m.group(4)])
    SOSI(coords, filnavn, timestamp)


while(True):
    try:
        partitionsFile = open("/proc/partitions")
        lines = partitionsFile.readlines()[2:]
        if len(devices) > 0 and not found:
            devices.pop()
            print("\nUSB-ENHET FRAKOBLET\n")
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
                            print("\nFANT USB-ENHET\n")
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
                            if not os.path.exists("/mnt/usb/sosi"):
                                os.makedirs("/mnt/usb/sosi")
                            for rutefil in os.listdir("/mnt/usb"):
                                timestamp = 0
                                if(rutefil.endswith(".gz")): #fra OLEX til CSV og DP
                                    try:
                                        f = gzip.open("/mnt/usb/%s" % rutefil) 
                                        o = open("/mnt/usb/utm/%s" % os.path.splitext(rutefil)[0] + ".csv", "w+", encoding="latin-1")
                                        odp = open("/mnt/usb/%s" % os.path.splitext(rutefil)[0] + ".tmp", "w+", encoding="latin-1")
                                        for line in f:
                                            line = line.decode("utf-8", errors="ignore")
                                            odp.write(line)
                                            timesearch = re.match("^\d*\.\d* \d*\.\d* (\d*)", line)
                                            if(timesearch):
                                                timestamp = timesearch.group(1)
                                            m = re.match("^(\d*\.\d*) (\d*\.\d*)", line)
                                            if(m):
                                                lat = float(m.group(1)) / 60
                                                lon = float(m.group(2)) / 60
                                                utmd = utm.from_latlon(lat,lon, force_zone_number=33)
                                                o.write("%0.2f" % utmd[0] + "," + "%0.2f" % utmd[1] + ","  + str(utmd[2]) + "," + utmd[3] + "\r\n")
                                                libc.sync()
                                        odp.close()         
                                        proc = subprocess.Popen([os.getcwd()+"/Ruter2SDP.pl", "/mnt/usb/%s" % os.path.splitext(rutefil)[0] + ".tmp"], stdout=subprocess.PIPE)
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
                                        csvtilsosi(os.path.splitext(rutefil)[0] + ".csv", timestamp)
                                        f.close()
                                    except:
                                        for e in sys.exc_info():
                                            print(e)
                                elif(rutefil.endswith(".csvd")): #CSV dybdefil til OLEX
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
                            print("\nKONVERTERING FERDIG\n")
                            GPIO.output(busyled, 0)
                            GPIO.output(powerled, 1)

    except:
        print("\nERROR\n")
        for e in sys.exc_info():
            print(e)
        GPIO.output(powerled, 1)
        GPIO.output(busyled, 0)
    time.sleep(1)
