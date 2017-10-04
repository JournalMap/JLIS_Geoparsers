# -*- coding: utf-8 -*-

"""
name: jmap_geoparser_re.py
author: J.W. Karl
date: 5/12/2016
purpose: parses each XML file in the input directory for geographic coordinates that match the nasty-looking regular expression below. Coordinates that are found are then converted to standardized decimal degree format. The regular expression is a modification (and simplification) of the GeoLucidate code. Outputs a csv file that can then be run through the loc_intersects.py script to create the locations.csv file for JournalMap
arguments: none, but paths and file variables need to be modified below
"""

import os, re, sys
from decimal import Decimal, setcontext, ExtendedContext

parserVersion = "Regular Expression GeoParser 2.0 beta, 05/25/2016"

def GeoCleanup(parts):
    """
    Normalize up the parts matched by :obj:`parser.parser_re` to
    degrees, minutes, and seconds.

    >>> _cleanup({'latdir': 'south', 'longdir': 'west',
    ...          'latdeg':'60','latmin':'30',
    ...          'longdeg':'50','longmin':'40'})
    ['S', '60', '30', '00', 'W', '50', '40', '00']

    >>> _cleanup({'latdir': 'south', 'longdir': 'west',
    ...          'latdeg':'60','latmin':'30', 'latdecsec':'.50',
    ...          'longdeg':'50','longmin':'40','longdecsec':'.90'})
    ['S', '60', '30.50', '00', 'W', '50', '40.90', '00']

    """

    # trap for no hemisphere given
    if (parts['dir11'] or parts ['dir12']):
        dir1 = (parts['dir11'] or parts['dir12']).upper()[0]
    if (parts['dir21'] or parts ['dir22']):
        dir2 = (parts['dir21'] or parts['dir22']).upper()[0]
    if not 'dir1' in locals():
        dir1 = 'N'
    if not 'dir2' in locals():
        dir2 = 'E'
        
    #if not (parts['dir11'] or parts ['dir12']):
    #    dir1 = "N"
    #elif not (parts['dir21'] or parts ['dir22']):    
    #    dir2 = "E"
    #else:
    #    dir1 = (parts['dir11'] or parts['dir12']).upper()[0]
    #    dir2 = (parts['dir21'] or parts['dir22']).upper()[0]

    #bail if they're the same - indicating bounding box
    if dir1[0] == dir2[0]: return

    latdeg = parts.get('latdeg')
    longdeg = parts.get('longdeg')

    # Check for negative signs with the degrees. If exists, prepend it to the degrees (still unicode chars at this point, so can't multiply)
    if (parts['latsign']):
        latdeg = u'-'+latdeg
    if (parts['longsign']):
        longdeg = u'-'+longdeg

    latdecdeg = parts.get('latdecdeg', '') or ''
    longdecdeg = parts.get('longdecdeg', '') or ''

    latmin = parts.get('latmin', '') or '00'
    longmin = parts.get('longmin', '') or '00'
    
    latdecmin = parts.get('latdecmin','') or ''
    longdecmin = parts.get('longdecmin','') or ''

    latsec = parts.get('latsec','00') or '00'
    longsec = parts.get('longsec','00') or '00'

    latdecsec = parts.get('latdecsec','') or ''
    longdecsec = parts.get('longdecsec','') or ''

    if (latdecdeg or longdecdeg):
        latdeg += latdecdeg
        longdeg += longdecdeg
        latmin = '00'
        longmin = '00'
        latsec = '00'
        longsec = '00'
    elif (latdecmin or longdecmin):
        latmin += latdecmin
        longmin += longdecmin
        latsec = '00'
        longsec = '00'
    elif (latdecsec or longdecsec):
        latsec += latdecsec
        longsec += longdecsec
    else:
        latsec = parts.get('latsec', '') or '00'
        longsec = parts.get('longsec', '') or '00'

    # Assign hemisphere directions (latdir and longdir)
    # Do this last because if coordinate is reported as longitude first, need to flip the lat/long coordinate assignments
    if dir1:
        if (dir1[0]=="N" or dir1[0]=="S"):
            latdir = dir1
            longdir = dir2
        else:
            latdir = dir2
            longdir = dir1
            holddeg = latdeg
            holdmin = latmin
            holdsec = latsec
            latdeg = longdeg
            latmin = longmin
            latsec = longsec
            longdeg = holddeg
            longmin = holdmin
            longsec = holdsec
    else:
        latdir = ''
        longdir = ''

    return [latdir, latdeg, latmin, latsec, longdir, longdeg, longmin, longsec]


def GeoConvert(latdir, latdeg, latmin, latsec, longdir, longdeg, longmin, longsec):
    """
    Convert normalized degrees, minutes, and seconds to decimal degrees.
    Quantize the converted value based on the input precision and
    return a 2-tuple of strings.

    >>> _convert('S','50','30','30','W','50','30','30')
    ('-50.508333', '-50.508333')

    """
    precision = Decimal('0.00001')

    latitude = Decimal(latdeg)
    if latitude<0:
        latitude = abs(latitude)
        latdir = "S"
    latmin = Decimal(latmin)
    latsec = Decimal(latsec)

    longitude = Decimal(longdeg)
    if longitude<0:
        longitude = abs(longitude)
        longdir = "W"
    longmin = Decimal(longmin)
    longsec = Decimal(longsec)

    #Assume that 'seconds' greater than 59 are actually a decimal
    #fraction of minutes
    if latsec > 59 or longsec > 59:
        latitude += (latmin +
                     (latsec / Decimal('100'))) / Decimal('60')
        longitude += (longmin +
                  (longsec / Decimal('100'))) / Decimal('60')
    else:
        latitude += (latmin +
                     (latsec / Decimal('60'))) / Decimal('60')
        longitude += (longmin +
                      (longsec / Decimal('60'))) / Decimal('60')


    # Apply the hemisphere designation to the degrees
    # Assume if both a negative degree value and a W or S hemisphere designation are given that
    #   the hemisphere designation is redundant.
    if (latdir == 'S' and latitude > 0):
        latitude *= Decimal('-1')

    if (longdir == 'W' and longitude > 0):
        longitude *= Decimal('-1')

    lat_str = unicode(latitude.quantize(precision))
    long_str = unicode(longitude.quantize(precision))

    return (lat_str, long_str)


lat_degrees = ur'(?:-?1(?:[0-7][0-9]|80)|(?:-?0?[0-9][0-9])|(?:-?[0-9]))'

parser_re = re.compile(ur"""\b
    # Optional word "latitude" or "longitude" offset by optional spaces 
    (\ ?(LATITUDE|LONGITUDE|LAT|LONG|LON)[.:]?\ ?)?
    # Latitude direction, first position: one of N, S, NORTH, SOUTH
    ((?P<dir11>NORTH|SOUTH|EAST|WEST|[NSEW])\ ?)?
    # Latitude degrees: two digits 0-90
    (?P<latsign>(?:-|−))?
    (?P<latdeg>(?:1(?:[0-7][0-9]|80)|(?:-?0?[0-9][0-9])|(?:-?[0-9])))
    (?P<latdecdeg>[\.|·|.]\d{1,8})?
    # Degree mark or word separating degrees and minutes
    (?P<degmark>\ ?(?:º|°|˚|°|˚| ͦ|˚|º|°|Â°|degrees|&deg;|deg))\ ?  
    (?P<latminsec>
    # Latitude minutes: two digits 0-59
    (?P<latmin>[0-5]?[0-9])
    (?P<latdecmin>[\.|·|.]\d{1,8})?
    # If there was a degree mark before, look for punctuation after the minutes
    (\ |(?(degmark)(″|"|′|'|’|minutes|′′|''|‘|‘‘|’|’’|‛|‛‛|‘|‘‘|ʹ|ʹʹ|ʼ|ʼʼ|“|”|‟|‟|〞|＂|ʺ|˝|â²)))?\ ?
    (
    # Latitude seconds: two digits
    ((?P<latsec>(\d{1,2}))
    # Decimal fraction of seconds
    (?P<latdecsec>[\.|·|.]\d{1,8})?)?)
    (?(degmark)(″|"|′|'|seconds|′′|''|‘|‘‘|’|’’|‛|‛‛|‘|‘‘|ʹ|ʹʹ|ʼ|ʼʼ|“|”|‟|‟|〞|＂|ʺ|˝)?)\ ?
    )? 
    # Latitude direction, second position, optionally preceded by a space
    (\ ?(?P<dir12>(?(dir11)|(NORTH|SOUTH|EAST|WEST|[NSEW]))))?
    # Optional word "latitude" or "longitude" offset by optional spaces
    (\ ?(LATITUDE|LONGITUDE|LAT|LONG|LON)[.:]?\ ?)?
    # Latitude/longitude delimiter: space, semicolon, comma, "by", or none
    (\ |\ BY\ |\ AND\ |,\ ?|;\ ?)?
    # Optional word "latitude" or "longitude" offset by optional spaces
    (\ ?(LATITUDE|LONGITUDE|LAT|LONG|LON)[.:]?\ ?)?    
    # Longitude direction, first position: one of E, W, EAST, WEST
    (?(dir11)((?P<dir21>NORTH|SOUTH|EAST|WEST|[NSEW])\ ?))?
    # Longitude degrees: two or three digits
    (?P<longsign>(?:-|−))? 
    (?P<longdeg>(?:1(?:[0-7][0-9]|80)|(?:-?0?[0-9][0-9])|(?:-?[0-9])))
    (?P<longdecdeg>[\.|·|.]\d{1,8})?   
    # If there was a degree mark before, look for another one here
    ((?(degmark)(\ ?(?:º|°|˚|°|˚| ͦ|˚|º|°|Â°|degrees|&deg;|deg))))\ ?
    (?(latminsec)   #Only look for minutes and seconds in the longitude
    (?P<longminsec> #if they were there in the latitude
    # Longitude minutes: two digits
    (?P<longmin>[0-5]?[0-9])
    (?P<longdecmin>[\.|·|.]\d{1,8})?
    # If there was a degree mark before, look for punctuation after the minutes
    (\ |(?(degmark)(″|"|′|'|’|minutes|′′|''|‘|‘‘|’|’’|‛|‛‛|‘|‘‘|ʹ|ʹʹ|ʼ|ʼʼ|“|”|‟|‟|〞|＂|ʺ|˝|â²)))?\ ?
    # Longitude seconds: two digits
    ((?P<longsec>(\d{1,2}))
    # Decimal fraction of minutes
    (?P<longdecsec>[\.|·|.]\d{1,8})?)?)
    (?(degmark)(″|"|′|'|seconds|′′|''|‘|‘‘|’|’’|‛|‛‛|‘|‘‘|ʹ|ʹʹ|ʼ|ʼʼ|“|”|‟|‟|〞|＂|ʺ|˝)?)\ ?
    )
    #Longitude direction, second position: optionally preceded by a space
    (?(dir21)|\ ?(?P<dir22>(NORTH|SOUTH|EAST|WEST|[NSEW])))?
    # Optional word "latitude" or "longitude" offset by optional spaces
    (\ ?(LATITUDE|LONGITUDE|LAT|LONG|LON)[.:]?\ ?)?    
    \b
    """, re.IGNORECASE | re.VERBOSE)


