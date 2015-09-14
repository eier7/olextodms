# * - * coding: utf-8 * - *
#!/usr/bin/env python

import re
import sys
import math

f = open(sys.argv[1], "r")
o = open(sys.argv[1]+".csv", "w")

for line in f:
    m = re.match("^(\d*\.\d*) (\d*\.\d*)", line)
    if(m):

        lat = float(m.group(1)) / 60
        lon = float(m.group(2)) / 60
        if(lat > 0):
            latd = 'N'
        else:
            latd = 'S'
        if(lon > 0):
            lond = 'E'
        else:
            lond = 'W'

        Dlat = str(math.floor(lat))
        Mlat = str(math.floor(abs(lat) * 60) % 60)
        Slat = (abs(lat) * 3600) % 60
        Slat = str("%.4f" % Slat)

        Dlon = str(math.floor(lon))
        Mlon = str(math.floor(abs(lon) * 60) % 60)
        Slon = (abs(lon) * 3600) % 60
        Slon = str("%.4f" % Slon)

        o.write(Dlat+ "\u00b0" +Mlat + "\'" + Slat +"\"" + latd + "," +  Dlon + "\u00b0" +Mlon + "\'" + Slon +"\"" + lond + "\r\n")


