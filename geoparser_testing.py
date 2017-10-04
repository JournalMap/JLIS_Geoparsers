#parser_testing.py
import os, sys, re, StringIO
import unicodecsv, csv
sys.path.append('/Users/Jason/Dropbox/JournalMap/scripts/GeoParsers')

class UnicodeWriter(object):
    """
    Like UnicodeDictWriter, but takes lists rather than dictionaries.
    
    Usage example:
    
    fp = open('my-file.csv', 'wb')
    writer = UnicodeWriter(fp)
    writer.writerows([
        [u'Bob', 22, 7],
        [u'Sue', 28, 6],
        [u'Ben', 31, 8],
        # \xc3\x80 is LATIN CAPITAL LETTER A WITH MACRON
        ['\xc4\x80dam'.decode('utf8'), 11, 4],
    ])
    fp.close()
    """
    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoding = encoding
    
    def writerow(self, row):
        # Modified from original: now using unicode(s) to deal with e.g. ints
        self.writer.writerow([unicode(s).encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = data.encode(self.encoding)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)
    
    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


##########################################################################################
###### Parse the test file using the Pyparsing GeoParser
##########################################################################################

from jmap_geoparser import *

## Set up the output file
outDir = '/Users/Jason/Dropbox/JournalMap/scripts/GeoParsers'
resultsFile = outDir + '/pyparsing_results.csv'
of = open(resultsFile, 'wb')
writer=UnicodeWriter(of)
writer.writerow([u'inLat',u'inLong','outLat','outLong','coord_string',u'parse_error'])

## Load the CSV file of the manually-entered coordinates from JournalMap
notParsed = 0
badParse = 0
total = 0
with open('test_set_full.csv', 'rb') as f:
#with open('test_set4.csv', 'rb') as f:
    reader = csv.reader(f)
    for row in reader:
        total+=1
        latitude = row[0]
        longitude = row[1]
        coord_string = row[2]
        print coord_string
        coords = coordinateParser.searchString(coord_string)
        if coords: print "test"
        try:
            assert coords
        except:
            #print "Coordinate not captured: " + coord_string
            writer.writerow([latitude,longitude,'','',coord_string.decode('utf-8'),"Coordinate not parsed"])
            notParsed+=1
        for coord in coords:        
            coordDD = coordinate(coord).calcDD
            try:
                assert (round(coordDD()['latitude'],2)==round(float(latitude),2) and round(coordDD()['longitude'],2)==round(float(longitude),2))
            except:
                #print "Error parsing coordinate " + coord_string
                writer.writerow([latitude,longitude,coordDD()['latitude'],coordDD()['longitude'],coord_string.decode('utf-8'),"Parsed coordinates do not match original"])
                badParse+=1
            #print str(coordDD()) + ";  " + "{'latitude': "+latitude+", 'longitude': "+longitude+"}"
    
of.close()
print ""
print "PyParsing GeoParser Results"
print "Total number of locations tested: "+str(total)
print "Number of locations not parsed: "+str(notParsed)+" ("+str((100.0*notParsed)/total)+"%)"
print "Number of locations where parsed coords do not match input: "+str(badParse)+" ("+str((100.0*badParse)/total)+"%)"


##########################################################################################
###### Repeat parsing of text file using the RegEx GeoParser
##########################################################################################

from jmap_geoparser_re import *

## Set up the output file
outDir = '/Users/Jason/Dropbox/JournalMap/scripts/GeoParsers'
resultsFile = outDir + '/RegExParsing_results.csv'
of = open(resultsFile, 'wb')
writer=UnicodeWriter(of)
writer.writerow([u'inLat',u'inLong','outLat','outLong','coord_string',u'parse_error'])

## Load the CSV file of the manually-entered coordinates from JournalMap
notParsed = 0
badParse = 0
total = 0
with open('test_set_full.csv', 'rb') as f:
#with open('test_set4.csv', 'rb') as f:
    reader = csv.reader(f)
    for row in reader:
        total+=1
        latitude = row[0]
        longitude = row[1]
        coord_string = row[2]
        print coord_string
        matches = parser_re.finditer(coord_string.decode('utf-8'))
        coords = len(parser_re.findall(coord_string.decode('utf-8')))
        try:
            assert coords > 0
        except:
            #print "Coordinate not captured: " + coord_string
            writer.writerow([latitude,longitude,'','',coord_string.decode('utf-8'),"Coordinate not parsed"])
            notParsed+=1
        for match in matches:        
            t = match.group()
            t2 = GeoCleanup(match.groupdict())
            if not t2: break
            coordDD = GeoConvert(t2[0], t2[1], t2[2], t2[3], t2[4], t2[5], t2[6], t2[7])
            try:
                #assert (round(coordDD()['latitude'],2)==round(float(latitude),2) and round(coordDD()['longitude'],2)==round(float(longitude),2))
                assert (round(float(coordDD[0]),2)==round(float(latitude),2) and round(float(coordDD[1]),2)==round(float(longitude),2))
            except:
                #print "Error parsing coordinate " + coord_string
                writer.writerow([latitude,longitude,coordDD[0],coordDD[1],coord_string.decode('utf-8'),"Parsed coordinates do not match original"])
                badParse+=1
    
of.close()
print ""
print "RegEx Geoparser Results"
print "Total number of locations tested: "+str(total)
print "Number of locations not parsed: "+str(notParsed)+" ("+str((100.0*notParsed)/total)+"%)"
print "Number of locations where parsed coords do not match input: "+str(badParse)+" ("+str((100.0*badParse)/total)+"%)"
