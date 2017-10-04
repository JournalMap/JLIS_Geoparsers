#####################################################################################
## jmapParseXML.py
## Parse a directory of publisher XML files to grab the citation information and 
## locations needed for JournalMap. Creates a set of CSV import files for JournalMap
## Includes a log file of results.
##
## This importer works with the following XML formats:
## "-//NLM//DTD Journal Publishing DTD v2.3 20070202//EN" "journalpublishing.dtd"
## "-//NLM/DTD Journal Archiving and interchange DTD v2.2 20060430//EN
## "-//NLM//DTD Journal Publishing DTD v3.0 20080202//EN"
#####################################################################################

import os, sys, re, StringIO
import fnmatch
import unicodecsv, csv

from decimal import Decimal, setcontext, ExtendedContext
from datetime import datetime
from bs4 import BeautifulSoup
from bs4 import UnicodeDammit
sys.path.append('C:/Users/jasokarl/Dropbox/JournalMap/scripts/GeoParsers')

startDir = 'C:/Users/jasokarl/Google Drive/JournalMap/Elsevier/RSE'
#startDir = '/Volumes/XML Storage/TandF/journal_of_natural_history/processed'
articlesFile = startDir + '/articles.csv'
locationsFile = startDir + '/locations.csv'
logFile = startDir + '/jmap_parse.log'
collectionKeyword = "" # Add special keyword for organizing into a collection
allArticles = False  # Include all articles (True) or only articles that have parsed locations in the output (False)?
geoparser = "re" # Which geoparser to use: "re" (Regular Expression) or "pyparsing"

if geoparser == "re":
    from jmap_geoparser_re import *  # Regular Expression Parser Version
else:
    from jmap_geoparser import *  # PyParsing version    

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


class ParseLog(object):
    def __init__(self):
        self.messages = []
        self.countArticles = 0
        self.countGeoTagged = 0
        self.locations = 0
        self.countErrors = 0
        self.countNoAuthors = 0
        self.countArticlesWritten = 0
    
    def add_msg(self, msg):
        self.messages.append(msg)


class Location(object):
    def __init__(self, coordinates, latitude, longitude):
        self.coordinates = coordinates
        self.latitude = latitude
        self.longitude = longitude
        
        # Set remaining attributes to blank
        self.place = ''
        self.no_recorded_place = True
        self.coordinate_type = 'Geographic Coordinate System (GCS)'
        self.no_recorded_coordinate = False
        self.location_type = ''
        self.location_scale = ''
        self.location_reliability = '2'
        self.location_conformance = ''
        self.error_type = ''
        self.error_description = ''    
        

class Article(object):
    
    def __init__(self, doi, title, year):
        self.doi = doi
        self.title = title
        self.year = year
        
        # Set the remaining attributes to blank
        self.no_keywords = False
        self.no_abstract = False
        self.url = ''
        self.publisher_abbreviation = ''
        self.publisher_name = ''
        self.citation = ''
        self.first_author = ''
        self.volume_issue_pages = ''
        self.volume = ''
        self.issue = ''
        self.start_page = ''
        self.end_page = ''
        self.abstract = ''
        self.authors = []
        self.keywords = []        
        
    def add_author(self, author):
        if not author in self.authors:
            self.authors.append(author)
    
    def add_keyword(self, keyword):
        if not keyword in self.keywords:
            self.keywords.append(keyword)

    def format_authors(self):
        author_string = ''
        for author in self.authors:
            author_string = author_string + ', ' + author
        return author_string[2:]

    def format_keywords(self):
        kw_string = ''
        for kw in self.keywords:
            kw_string = kw_string + ', ' + kw
        return kw_string[2:]

    def format_volisspg(self):
        #Must have a volume     
        # check for issue
        if self.issue: istring = "(" + str(self.issue) + ")"
        else: istring = ''
        # Check for pages
        if self.end_page: pgstring = "-"+str(self.end_page)
        else: pgstring = ""
        if self.start_page: pgstring = ":" + str(self.start_page) + pgstring
        vip = str(self.volume) + istring + pgstring
        return vip

    def build_citation(self):
        citation = self.format_authors() + ". " + str(self.year) +". " + self.title + ". " + self.publisher_name + ". "
        self.citation = citation
        return citation


#start logging
log = ParseLog()
lf = open(logFile,"w")
lf.write("Starting processing of "+startDir+" on "+datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')+"\n")
lf.write("Parsing geolocations using "+parserVersion+"\n\n")

with open(articlesFile, 'wb') as articlesCSV:
    with open(locationsFile, 'wb') as locationsCSV:
        articleWriter = unicodecsv.writer(articlesCSV)
        articlelines = [['doi','publisher_name','publisher_abbreviation','citation','title','publish_year','first_author','authors_list','volume_issue_pages','volume','issue','start_page','end_page','keywords_list','no_keywords_list','abstract','no_abstract','url']]
        articleWriter.writerows(articlelines)    
    
        locationWriter = unicodecsv.writer(locationsCSV)
        locationlines = [['doi','title','longitude','latitude','place','no_recorded_place','coordinates','coordinate_type','no_recorded_coordinate','location_type','location_scale','location_reliability','location_conformance','error_type','error_description']]
        locationWriter.writerows(locationlines)
    
        ## Traverse the start directory structure
        for root, dirs, files in os.walk(startDir):
            for name in fnmatch.filter(files, '*.xml'):
                ###############################
                ## Grab the article XML file ##
                ############################### 
                xmlFile = os.path.join(root,name)
                print("Processing " + xmlFile)
                log.add_msg("Processing " + xmlFile)
                log.countArticles += 1
                
                ###############################
                ## Grab the article metadata ##
                ###############################        
    
                # Read the XML
                f = open(xmlFile)
                #xmlStr = UnicodeDammit(f.read())
                #tree = BeautifulSoup(xmlStr.unicode_markup,"lxml")
                rawtext = UnicodeDammit.detwingle(f.read())
                tree = BeautifulSoup(rawtext.decode('utf-8','ignore'),"xml")
                #tree = BeautifulSoup(f.read(),"lxml")
                f.close()
                #print tree.prettify()

                #############################################
                ## Process NLM or JATS-formatted XML files ##
                #############################################                
                if tree.find('front'):  # NLM or JATS formatted XML
                    fmt = "NLM"
                    # Read the first three elements and create the article object
                    try: doi = tree.front.find('article-id', {'pub-id-type':'doi'}).text 
                    except: doi=''
                    try: title = tree.front.find('article-title').text
                    except: title=''
                    try: year = tree.front.find('pub-date').year.text
                    except: year = ''
        
                    article = Article(doi, title, year)
        
                    # Add the other single item attributes
                    try: article.publisher_name = tree.front.find('journal-title').text
                    except: article.publisher_name = ''            
                    
                    try: article.volume = tree.front.find('volume').text
                    except: article.volume = ''
                    
                    try: article.issue = tree.front.find('issue').text
                    except: article.issue = ''
                    
                    try: article.start_page = tree.front.find('fpage').text
                    except:
                        try: article.start_page = tree.front.find('elocation-id').text
                        except: article.start_page = ''
                        
                    try: article.end_page = tree.front.find('lpage').text
                    except: article.end_page = ''
                    
                    try:
                        for a in tree.find_all('abstract'):
                            if not a.get('abstract-type')=='precis':
                                article.abstract = a.text
                            else:
                                article.abstract = ''
                        if not article.abstract: article.no_abstract = True
                    except: 
                        article.abstract = ''
                        article.no_abstract = True
                    
                    
                    ###############################
                    ## Build authors list        ##
                    ############################### 
                    try:
                        for author in tree.find_all('contrib'):
                            article.add_author(author.find('surname').text + ", " + author.find('given-names').text)
                        if len(article.authors)==0: raise
                    except:
                        print "No authors found for " + xmlFile + ". Skipping this article."
                        log.add_msg("No authors found for " + xmlFile + ". Skipping this article.")
                        log.countNoAuthors += 1
                        continue
                    
                    ###############################
                    ## Build keywords list       ##
                    ############################### 
                    if tree.find('kwd'):
                        for kw in tree.find_all('kwd'):
                            article.add_keyword(kw.text)
                    if collectionKeyword: article.add_keyword(collectionKeyword)    
                    if not article.keywords: no_keywords = True

                ########################################
                ## Process Elsevier XML files         ##
                ########################################                
                elif tree.find('coredata'):
                    fmt = "Elsevier"
                    meta = tree.find('coredata')
                    print 'Elsevier formatted XML for' + xmlFile
                    # Read the first three elements and create the article object
                    try: doi = tree.coredata.find('doi').text 
                    except: doi=''
                    try: title = tree.coredata.find('title').text
                    except: title=''
                    try: year = tree.coredata.find('coverDate').text[:4]
                    except: year = ''
        
                    article = Article(doi, title, year)
                    
                    # Add the other single item attributes
                    try: article.publisher_name = tree.coredata.find('publicationName').text
                    except: article.publisher_name = ''            
                    
                    try: article.volume = tree.coredata.find('volume').text
                    except: article.volume = ''
                    
                    try: article.issue = tree.coredata.find('issueIdentifier').text
                    except: article.issue = ''
                    
                    try: article.start_page = tree.coredata.find('startingPage').text
                    except: article.start_page = ''
                        
                    try: article.end_page = tree.coredata.find('endingPage').text
                    except: article.end_page = ''                    
                    
                    try: 
                        abs = tree.coredata.find('description').text
                        if abs[:8] == "Abstract":
                            article.abstract = abs[8:]
                        else: 
                            article.abstract = abs
                        if not article.abstract: article.no_abstract = True
                    except: 
                        article.abstract = ''
                        article.no_abstract = True                    

                    ###############################
                    ## Build keywords list       ##
                    ############################### 
                    if tree.coredata.find('subject'):
                        for kw in tree.coredata.find_all('subject'):
                            article.add_keyword(kw.text)
                    if collectionKeyword: article.add_keyword(collectionKeyword)    
                    if not article.keywords: no_keywords = True                    
                    
                    ###############################
                    ## Build authors list        ##
                    ############################### 
                    try:
                        for author in tree.coredata.find_all('creator'):
                            article.add_author(author.text)
                        if len(article.authors)==0: raise
                    except:
                        print "No authors found for " + xmlFile + ". Skipping this article."
                        log.add_msg("No authors found for " + xmlFile + ". Skipping this article.")
                        log.countNoAuthors += 1
                        continue
                    
                else:
                    fmt = "other"
                    print 'Unknown XML format...'
                    
                
                ###############################
                ## parse XML for locations   ##
                ## and write to CSV file     ##
                ###############################
                try:
                    if fmt=='NLM': #NLM/JATS Format
                        text = " ".join(tree.find('body').stripped_strings)
                    elif fmt=='Elsevier': #Elsevier Format
                        text = " ".join(tree.find('originalText').stripped_strings)
                    else: text = " "
                    #print text
                    initlocs = log.locations
                    if geoparser == "re":
                        matches = parser_re.finditer(text)
                        if len(parser_re.findall(text))>0: log.countGeoTagged += 1
                        for match in matches:
                            t=match.group()
                            t2 = GeoCleanup(match.groupdict())
                            if not t2: break
                            geodd = GeoConvert(t2[0], t2[1], t2[2], t2[3], t2[4], t2[5], t2[6], t2[7])
                            if geodd[0] == u'1.00000' and geodd[1] == u'1.00000': break
                            print "Found coordinate in " + article.doi + ": " + t.encode('ascii','ignore') + ", " + geodd[0] + ", " + geodd[1]
                            log.add_msg("Found coordinate in " + article.doi + ": " + t.encode('ascii','ignore') + ", " + geodd[0] + ", " + geodd[1])
                            loc = Location(t,geodd[0],geodd[1])                        
                            locationLine = [[article.doi,article.title,loc.longitude,loc.latitude,loc.place,loc.no_recorded_place,loc.coordinates,loc.coordinate_type,loc.no_recorded_coordinate,loc.location_type,loc.location_scale,loc.location_reliability,loc.location_conformance,loc.error_type,loc.error_description]]
                            locationWriter.writerows(locationLine)
                            log.locations += 1
                    else:
                        ## PyParsing geoparser
                        coords = coordinateParser.searchString(text.encode('utf-8'))
                        if coords: log.countGeoTagged += 1
                        for coord in coords:        
                            coordDD = coordinate(coord).calcDD
                            print "Found coordinate in " + article.doi + ": " + str(coordDD()) + ", " + str(coordDD()['latitude']) + ", " + str(coordDD()['longitude'])
                            log.add_msg("Found coordinate in " + article.doi + ": " + str(coordDD()) + ", " + str(coordDD()['latitude']) + ", " + str(coordDD()['longitude']))   
                            loc = Location(str(coordDD()),coordDD()['latitude'],coordDD()['longitude'])                        
                            locationLine = [[article.doi,article.title,loc.longitude,loc.latitude,loc.place,loc.no_recorded_place,loc.coordinates,loc.coordinate_type,loc.no_recorded_coordinate,loc.location_type,loc.location_scale,loc.location_reliability,loc.location_conformance,loc.error_type,loc.error_description]]
                            locationWriter.writerows(locationLine)
                            log.locations += 1
                            
                    articlelocs = log.locations-initlocs
                except Exception, e:
                    print(e)
                    print "No article text found to parse in " + xmlFile
                    log.add_msg("No article text found to parse in " + xmlFile)
                    continue
                
                
                ###############################
                ## Write article to output   ##
                ###############################
                if (allArticles or articlelocs>0):
                    try:
                        articleLine = [[article.doi,article.publisher_name,'',article.build_citation(),article.title,str(article.year),article.authors[0],article.format_authors(),article.format_volisspg(),article.volume,article.issue,article.start_page,article.end_page,article.format_keywords(),article.no_keywords,article.abstract,article.no_abstract,article.url]]
                        articleWriter.writerows(articleLine)            
                        log.countArticlesWritten += 1
                    except: 
                        print "Error writing record for " + xmlFile + " - " + article.title
                        log.add_msg("Error writing record for " + xmlFile + " - " + article.title)
                        log.countErrors += 1
                        continue                
                
        ###############################
        ## Clean up and log errors   ##
        ############################### 
        
        print ""
        print "Finished!!"
        print "Processed " + str(log.countArticles) + " articles."
        print "Errors encountered in " + str(log.countErrors) + " articles."
        print str(log.countNoAuthors) + " articles had no authors and were skipped."
        print str(log.countArticlesWritten) + " articles written to the CSV file"
        print str(log.countGeoTagged) + " articles had parsed coordinates."
        print str(log.locations) + " total locations found."
        for msg in log.messages:
            lf.write("\n"+msg.encode("UTF-8"))
        lf.write("\n".join(["","","Finished processing directory "+startDir+" at "+datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'),"Processed " + str(log.countArticles) + " articles.",
                           "Errors encountered in " + str(log.countErrors) + str(log.countNoAuthors) + " articles had no authors and were skipped." + str(log.countArticlesWritten) + " articles written to the CSV file" + " articles.", str(log.countGeoTagged) + " articles had parsed coordinates.",str(log.locations) + " total locations found.",
                           "Created output files:",articlesFile,locationsFile,logFile]))
        lf.close()  
        