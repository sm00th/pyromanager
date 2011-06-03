''' Classes to import data from various xml databases '''
import sqlite3
from xml.dom import minidom
import re

def stripGameName( gameName ):
    gameName = re.sub( r"(\(|\[)[^\(\)\[\]]*(\)|\])", '', gameName )
    gameName = re.sub( r"the", '', gameName )
    gameName = re.sub( r"[^\w\d\s]", '', gameName )
    gameName = re.sub( r"\s+", ' ', gameName )
    gameName = gameName.strip()

    return gameName

def parseFileName( fileName ):
    releaseNum = None

    fileName = re.sub( r"^.*/", '', fileName )
    fileName = fileName.lower()
    fileName = re.sub( "\.nds$", '', fileName )
    fileName = re.sub( "_", ' ', fileName )

    releaseNum_pattern = re.compile( r"(\[|\()?(\d+)(\]|\))?\s*-?(.*)" )
    matchReleaseNum = releaseNum_pattern.match( fileName )
    if matchReleaseNum:
        releaseNum = int( matchReleaseNum.group( 2 ) )
        fileName = matchReleaseNum.group( 4 )

    fileName = stripGameName( fileName )

    return [ releaseNum, fileName ]

def getText( nodeList ):
    rc = []
    for node in nodeList:
        if node.nodeType == node.TEXT_NODE:
            rc.append( node.data )
    return ''.join( rc )

def searchByCRC( gameList, crc32 ):
    # TODO: sick and gay, scratch that, creating bintree during parsing might
    # improve things, othervise - better do nothing
    for game in gameList:
        if game[2] == crc32:
            return [ game[0], game[1], game[2] ]
    return None

def searchByReleaseNumber( gameList, releaseNumber ):
    # TODO: same as crc32
    for game in gameList:
        if game[0] == releaseNumber:
            return [ game[0], game[1], game[2] ]
    return None


def searchByName( gameList, gameName ):
    for game in gameList:
        # TODO: Levenshtein distance is good enough, probably
        # also something to strip or process non-name info like release number
        # and regioncode in filename    
        if re.search( gameName, stripGameName( game[1] ), re.IGNORECASE ):
            return [ game[0], game[1], game[2] ]
    return None

class SQLdb():
    def __init__( self, dbFile ):
        # TODO: check if dbFile specified and read from config?
        self.db = sqlite3.connect( dbFile )

    def __del__( self ):
        self.db.close()

    def _createTables( self ):
        cursor = self.db.cursor()
        cursor.execute( 'CREATE TABLE IF NOT EXISTS known_roms (release_id INTEGER PRIMARY KEY, name TEXT, crc32 NUMERIC, publisher TEXT, released_by TEXT);' )
        cursor.execute( 'CREATE TABLE IF NOT EXISTS local_roms (id INTEGER PRIMARY KEY, release_id TEXT, UNIQUE( path_to_file TEXT ) ON CONFLICT REPLACE);' )
        self.db.commit()
        cursor.close()

    def importKnownFrom( self, provider ):
        self._createTables()

        try:
            cursor = self.db.cursor()
            dataList = provider.getDBData()
            for dataSet in dataList:
                cursor.execute( 'INSERT OR REPLACE INTO known_roms VALUES(?,?,?,?,?)', dataSet )
            self.db.commit()
            cursor.close()
        except Exception as e:
            print "Failed to import from xml: %s" % e
        return 1

    def searchByCRC( self, crc32 ):
        releaseNumber = None
        try:
            cursor = self.db.cursor()
            retVal = cursor.execute( 'SELECT release_id FROM known_roms WHERE crc32=?', ( crc32, ) ).fetchone()
            if retVal:
                releaseNumber = retVal[0]
            cursor.close()
        except Exception as e:
            print "Failed to query db by crc32: %s" % e

        return releaseNumber

    def searchByReleaseNumber( self, relNum ):
        releaseNumber = None
        try:
            cursor = self.db.cursor()
            retVal = cursor.execute( 'SELECT release_id FROM known_roms WHERE release_id=?', ( relNum, ) ).fetchone()
            if retVal:
                releaseNumber = retVal[0]
            cursor.close()
        except Exception as e:
            print "Failed to query db by release number: %s" % e

        return releaseNumber

    def searchByName( self, name ):
        releaseNumber = None
        try:
            cursor = self.db.cursor()
            retVal = cursor.execute( 'SELECT release_id FROM known_roms WHERE name LIKE ?', ( name, ) ).fetchone()
            if retVal:
                releaseNumber = retVal[0]
            cursor.close()
        except Exception as e:
            print "Failed to query db by release number: %s" % e

        return releaseNumber

    def addLocalRom( self, filePath, releaseNumber ):
        try:
            cursor = self.db.cursor()
            cursor.execute( 'INSERT OR REPLACE INTO local_roms ( release_id, path_to_file ) values ( ?, ? )', ( releaseNumber, filePath ) )
            self.db.commit()
        except Exception as e:
            print "Failed to add (%s,%s) to local roms: %s" % ( filePath, releaseNumber, e )

class AdvansceneXML():
    def __init__( self, filePath ):
        self.filePath = filePath
        self.gameList = []

        self.parseFile()

    def parseFile( self ):
        try:
            db = minidom.parse( self.filePath )
            for gameNode in db.getElementsByTagName( 'game' ):
                self.gameList.append( self.parseGame( gameNode ) )
        except IOError:
            raise Exception( 'Can not open or parse file %s' % self.filePath )

    def getDBData( self ):
        return self.gameList

    def parseGame( self, gameNode ):
        title = getText( gameNode.getElementsByTagName( 'title' )[0].childNodes )
        publisher = getText( gameNode.getElementsByTagName( 'publisher' )[0].childNodes )
        releasedBy = getText( gameNode.getElementsByTagName( 'sourceRom' )[0].childNodes )
        relNum = int( getText( gameNode.getElementsByTagName( 'releaseNumber' )[0].childNodes ) )
        crc32 = self.getCRC( gameNode )
        #return [ title, relNum, crc32 ]
        return ( relNum, title, crc32, publisher, releasedBy )

    def searchByCRC( self, crc32 ):
        return searchByCRC( self.gameList, crc32 )

    def searchByName( self, name ):
        return searchByName( self.gameList, name )

    def searchByReleaseNumber( self, releaseNumber ):
        # TODO: check if the names are relatively the same or let the user choose if found release is ok
        return searchByReleaseNumber( self.gameList, releaseNumber )

    def getCRC( self, gameNode ):
        for crc in gameNode.getElementsByTagName( 'romCRC' ):
            if crc.getAttribute( 'extension' ) != '.nds':
                continue
            else:
                return int( getText( crc.childNodes ), 16 )
        return None
