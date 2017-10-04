#!/usr/bin/env python
# -*- coding: utf-8 -*-

### Call with:
### test = "45º 23' 12'', 123º 23' 56''"  
### assert coordinate(coordinateParser.parseString(test)).calcDD() == {'latitude': 45.38667, 'longitude': 123.39889}

from pyparsing import *
ParserElement.enablePackrat()

parserVersion = "PyParsing GeoParser 2.0 beta, 05/25/2016"

## Parsing validation functions
def validateLatDeg(nums):
    if abs(float(nums[0])) >= 180:   ## This was relaxed to allow for reversed coordinate pairs (i.e., long/lat). Will impose this validation in the calcDD method
        raise ParseException("Invalid Latitude Degrees: %s" % nums[0])

def validateLonDeg(nums):
    if abs(float(nums[0])) >= 180:
        raise ParseException("Invalid Longitude Degrees: %s" % nums[0])

def validateMinSec(nums):
    if float(nums[0]) >= 60:
        raise ParseException("Invalid minute or seconds: %s" % nums[0])

def formatHemi(hemi):
    if hemi[0].lower()=='north': return 'n'
    if hemi[0].lower()=='south': return 's'
    if hemi[0].lower()=='east': return 'e'
    if hemi[0].lower()=='west': return 'w'


## Establish coordinate object class
class coordinate(object):
    latDeg = 0
    latMin = 0
    latSec = 0
    latHemi = 'N'
    lonDeg = 0
    lonMin = 0
    lonSec = 0
    lonHemi = 'E'
    latSign = 1
    lonSign = 1    
    
    def __init__(self, parseDict):
        self.parseDict = parseDict
        
        # first figure out the hemisphere designations if any and decide if coordinate
        # is lat/long (most common) or long/lat. If no hemisphere designations,
        # assume lat/long
        hemi11 = ''
        hemi12 = ''
        hemi21 = ''
        hemi22 = ''
        if 'hemi11' in parseDict: hemi11 = parseDict.hemi11[0] 
        if 'hemi12' in parseDict: hemi12 = parseDict.hemi12[0] 
        if 'hemi21' in parseDict: hemi21 = parseDict.hemi21[0] 
        if 'hemi22' in parseDict: hemi22 = parseDict.hemi22[0] 
        
        if hemi11 or hemi12: self.latHemi = (hemi11 or hemi12) # only one of hemi11 or hemi12 is provided
        if hemi11 and hemi12: # both exist, need to check if they are different
            self.latHemi = hemi11
            if hemi11 != hemi12:
                # This means that the parser caught two hemisphere designations for latHemi, and they're
                # probably different. Most likely the second one comes from the second part
                # of the coordinate pair and there was no separator character (e.g., comma).                            
                self.lonHemi = hemi12
        
        if hemi21 or hemi22:
            self.lonHemi = (hemi21 or hemi22)
        
        # Get the rest of the coordinate parts from the parseDict
        self.latDeg = float(parseDict.latDeg[0])
        if 'latMin' in parseDict: self.latMin = float(parseDict.latMin[0])
        if 'latSec' in parseDict: self.latSec = float(parseDict.latSec[0])
        if 'latNeg' in parseDict: self.latSign = -1
        #if 'latHemi' in parseDict: self.latHemi = parseDict.latHemi[0]
        
        self.lonDeg = float(parseDict.lonDeg[0])
        if 'lonMin' in parseDict: self.lonMin = float(parseDict.lonMin[0])
        if 'lonSec' in parseDict: self.lonSec = float(parseDict.lonSec[0])
        if 'lonNeg' in parseDict: self.lonSign = -1
        #if 'lonHemi' in parseDict: self.lonHemi = parseDict.lonHemi[0]
    
    def calcDD(self):
        # Check if the coordinate pair is actually Long/Lat
        if self.latHemi.upper() in ['E','W']:
            #switch things around
            holdDeg = self.latDeg
            holdMin = self.latMin
            holdSec = self.latSec
            holdHemi = self.latHemi
            holdSign = self.latSign
            self.latDeg = self.lonDeg
            self.latMin = self.lonMin
            self.latSec = self.lonSec
            self.latHemi = self.lonHemi
            self.latSign = self.lonSign
            self.lonDeg = holdDeg
            self.lonMin = holdMin
            self.lonSec = holdSec
            self.lonHemi = holdHemi
            self.latSign = holdSign
        
        # Check for latitude values greater than 90º
        if self.latDeg > 90:
            print "Invalid Latitude Degrees: " +str(self.latDeg)
            return {"latitude":-999, "longitude":-999}
        

        if self.latHemi.upper() == 'S': self.latSign = -1
        if self.lonHemi.upper() == 'W': self.lonSign = -1
        lat = self.latSign*(self.latDeg + self.latMin/60 + self.latSec/3600)
        lon = self.lonSign*(self.lonDeg + self.lonMin/60 + self.lonSec/3600)
        return {"latitude":round(lat,5), "longitude":round(lon,5)}
    



## Parsing elements
digits = Word(nums)

degSign = Literal("º") | Literal('°') | Literal(' ͦ') | Literal('˚') | Literal('º') | Literal('ø') | CaselessLiteral("degrees") | CaselessLiteral("deg") | CaselessLiteral("&deg;") # º|°|˚|°|degrees|&deg;
minSign = Literal("’") | Literal("′") | Literal("'") | Literal("‛") | Literal("‘") | Literal('ʹ') | Literal('ʼ')  | CaselessLiteral("minutes") | CaselessLiteral("min") # ″|"|′|'|’|minutes|′′|''
secSign = Literal('″') | Literal('"') | Literal("′′") | Literal("''") | Literal("’’") | Literal("‛‛") | Literal("‘‘") | Literal("ʹʹ") | Literal("ʼʼ") | Literal('“') | Literal('”') | Literal('‟') | Literal('〞') | Literal('＂') | Literal('ʺ') | Literal('˝')| CaselessLiteral("seconds") | CaselessLiteral("sec")
negSign = Literal('-') | Literal('−') | Literal('–') | Literal('—') | Literal('―') | Literal('‒')
decPoint = Literal(".") | Literal(".") | Literal("·")

coordPart = Combine(digits + Optional(decPoint + digits))

hemi = oneOf("north south east west N S E W", caseless=True)
hemi.setParseAction(formatHemi)

latDeg = coordPart + Suppress(degSign)
#latDeg = coordPart + Suppress(Optional(degSign))
latDeg.setParseAction(validateLatDeg)

lonDeg = coordPart + Suppress(degSign)
#lonDeg = coordPart + Suppress(Optional(degSign))
lonDeg.setParseAction(validateLonDeg)

mins = coordPart + Suppress(Optional(minSign))
mins.setParseAction(validateMinSec)
secs = coordPart + Suppress(Optional(secSign))
secs.setParseAction(validateMinSec)

separator = Suppress(Optional(Literal(',') | Literal(";") | Literal("") | oneOf("by and", caseless=True))  )
fluff = Suppress(Optional(Literal("") | CaselessLiteral("latitude of") | CaselessLiteral("longitude of") | oneOf("latitude latitude: lat lat. lat: longitude longitude: long long. lon lon. lon:", caseless=True) ))

# Option that includes provision for commas between degrees, minutes, and seconds (pretty uncommon, but prevents other simpler versions from parsing
#latPart = fluff + Optional(latHemi.setResultsName('latHemi')) + Optional(negSign.setResultsName('latNeg')) + latDeg.setResultsName('latDeg') + Optional(Literal(",")) + Optional(mins.setResultsName('latMin')) + Optional(Literal(",")) + Optional(secs.setResultsName('latSec')) + Optional(latHemi.setResultsName('latHemi')) + fluff
#lonPart = fluff + Optional(lonHemi.setResultsName('lonHemi')) + Optional(negSign.setResultsName('latNeg')) + lonDeg.setResultsName('lonDeg') + Optional(Literal(",")) + Optional(mins.setResultsName('lonMin')) + Optional(Literal(",")) + Optional(secs.setResultsName('lonSec')) + Optional(lonHemi.setResultsName('lonHemi')) + fluff

# Standard version (no commas between degrees, minutes, and seconds.
latPart = fluff + Optional(hemi.setResultsName('hemi11')) + Optional(negSign.setResultsName('latNeg')) + latDeg.setResultsName('latDeg') + Optional(mins.setResultsName('latMin')) + Optional(secs.setResultsName('latSec')) + Optional(hemi.setResultsName('hemi12')) + Optional(fluff)
lonPart = Optional(fluff) + Optional(hemi.setResultsName('hemi21')) + Optional(negSign.setResultsName('lonNeg')) + lonDeg.setResultsName('lonDeg') + Optional(mins.setResultsName('lonMin')) + Optional(secs.setResultsName('lonSec')) + Optional(hemi.setResultsName('hemi22')) + fluff

coordinateParser = latPart + separator.setResultsName('sep') + lonPart