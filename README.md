# JournalMap Geoparsers for JLIS Article
The respository contains the Python scripts for the geoparsers used in the paper "Mining location information from life- and earth-sciences studies to facilitate knowledge discovery" published in the Journal of Librarianship and Information Science (JLIS). Geoparsers are scripts that search for location information (geogrpahic coordinates in this case) using pattern matching algorithms. The JLIS paper considered two different approaches to geoparsing: regular expressions and lexical parsing. This repo also contains the script and input files used for testing the geoparsers against known coordinate values, and the script that parsed location information from full-text articles in the National Library of Medicine's JATS XML format. The full-text XML documents evaluated for the JLIS paper cannot be redistributed.

### Requirements and External Dependencies
 * The parser scripts in this repository were written in Python version 2.7. 
 * The lexical parser requires the PyParsing library - (http://pyparsing.wikispaces.com/)
 * Ingest and parsing of the full-text XML files uses BeautifulSoup4 - (https://www.crummy.com/software/BeautifulSoup/)
  
### File Descriptions
 * jmap_geoparser.py - Lexical geoparser written with PyParsing
 * jmap_geoparser_re.py - Regular Expression geoparser
 * geoparser_testing.py - Test script that imports the test set CSV file, runs each geoparser version and outputs the results as a CSV file.
 * jmapParseXML.py - Script for importing full-text article XML documents, extracting citation information, and parsing the article body text for coordinates.
 * README.md - This description document.
 
 