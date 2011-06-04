import sqlite3
from xml.dom import minidom
import re
from cfg import config

def encodeLocation( locationName ):
    for ( locationId, locationAliases ) in config['location'].iteritems():
        if locationName.lower() in [ x.lower() for x in locationAliases ]:
            return locationId

    return None

def decodeLocation( locationId, returnType=1 ):
    result = 'Unknown: %d' % locationId
    if returnType not in range(3):
        returnType = 1
    try:
        result = config['location'][locationId][returnType]
    except:
        pass

    return result

def stripGameName( gameName ):
    gameName = re.sub( r"(\(|\[)[^\(\)\[\]]*(\)|\])" , ''  , gameName )
    gameName = re.sub( r"(the|and)"                  , ''  , gameName )
    gameName = re.sub( r"[^\w\d\s]"                  , ''  , gameName )
    gameName = re.sub( r"\s+"                        , ' ' , gameName )
    gameName = gameName.strip()

    return gameName

def parseFileName( fileName ):
    releaseNum = None

    fileName = fileName.lower()
    fileName = re.sub( r"^.*(/|:)" , ''  , fileName )
    fileName = re.sub( "\.nds$"    , ''  , fileName )
    fileName = re.sub( "_"         , ' ' , fileName )

    releaseNum_pattern = re.compile( r"((\[|\()?(\d+)(\]|\))|(\d+)\s*-\s*)\s*(.*)" )
    matchReleaseNum    = releaseNum_pattern.match( fileName )

    if matchReleaseNum:
        if matchReleaseNum.group( 3 ):
            releaseNum = int( matchReleaseNum.group( 3 ) )
            fileName   = matchReleaseNum.group( 6 )
        elif matchReleaseNum.group( 5 ):
            releaseNum = int( matchReleaseNum.group( 5 ) )
            fileName   = matchReleaseNum.group( 6 )

    location = None
    for tag in re.findall( r"(\(|\[)(\w+)(\)|\])", fileName ):
        if not location:
            location = encodeLocation( tag[1] )

    fileName = stripGameName( fileName )

    return [ releaseNum, fileName, location ]

def getText( nodeList ):
    rc = []
    for node in nodeList:
        if node.nodeType == node.TEXT_NODE:
            rc.append( node.data )
    return ''.join( rc )

class SQLdb():
    def __init__( self, dbFile ):
        # TODO: check if dbFile specified and read from config?
        self.db = sqlite3.connect( dbFile )

    def __del__( self ):
        self.db.close()

    def _createTables( self ):
        cursor = self.db.cursor()
        cursor.execute( 'CREATE TABLE IF NOT EXISTS known_roms (release_id INTEGER PRIMARY KEY, name TEXT, crc32 NUMERIC, publisher TEXT, released_by TEXT, location NUMERIC, normalized_name TEXT);' )
        cursor.execute( 'CREATE TABLE IF NOT EXISTS local_roms (id INTEGER PRIMARY KEY, release_id TEXT, path_to_file TEXT, normalized_name TEXT, UNIQUE( path_to_file ) ON CONFLICT REPLACE);' )
        self.db.commit()
        cursor.close()

    def importKnownFrom( self, provider ):
        self._createTables()

        try:
            cursor = self.db.cursor()
            dataList = provider.getDBData()
            for dataSet in dataList:
                normalizedName = stripGameName( dataSet[1] )
                cursor.execute( 'INSERT OR REPLACE INTO known_roms VALUES(?,?,?,?,?,?,?)', dataSet + ( normalizedName.lower(), ) )
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
            print "Failed to query db by crc32 %s: %s" % ( crc32, e )

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
            print "Failed to query db by release number %s: %s" % ( relNum, e )

        return releaseNumber

    def searchByName( self, name, location=None ):
        relNumList = []
        try:
            retVal     = None
            cursor     = self.db.cursor()
            searchName = '%' + re.sub( r"\s", '%', name ) + '%'
            if location != None:
                retVal = cursor.execute( 'SELECT release_id FROM known_roms WHERE normalized_name LIKE ? and location=?', ( searchName, location ) ).fetchall()
            else:
                retVal = cursor.execute( 'SELECT release_id FROM known_roms WHERE normalized_name LIKE ?', ( searchName, ) ).fetchall()
            if retVal:
                relNumList = [ x[0] for x in retVal ]
            cursor.close()
        except Exception as e:
            print "Failed to query db by name %s: %s" % ( name, e )

        return relNumList

    def getGameInfo( self, releaseNumber ):
        gameInfo = None
        try:
            cursor = self.db.cursor()
            retVal = cursor.execute( 'SELECT release_id, name, publisher, released_by, location FROM known_roms WHERE release_id=?', ( releaseNumber, ) ).fetchone()
            if retVal:
                gameInfo = retVal
            cursor.close()
        except Exception as e:
            print "Failed to get game info by release number %s: %s" % ( releaseNumber, e )

        return gameInfo


    def addLocalRom( self, filePath, releaseNumber ):
        normalizedName = parseFileName( filePath )[1]
        try:
            cursor = self.db.cursor()
            cursor.execute( 'INSERT OR REPLACE INTO local_roms ( release_id, path_to_file, normalized_name ) values ( ?, ?, ? )', ( releaseNumber, filePath, normalizedName ) )
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
        title      = getText( gameNode.getElementsByTagName( 'title' )[0].childNodes )
        publisher  = getText( gameNode.getElementsByTagName( 'publisher' )[0].childNodes )
        releasedBy = getText( gameNode.getElementsByTagName( 'sourceRom' )[0].childNodes )
        location   = getText( gameNode.getElementsByTagName( 'location' )[0].childNodes )
        relNum     = int( getText( gameNode.getElementsByTagName( 'releaseNumber' )[0].childNodes ) )
        crc32      = self.getCRC( gameNode )
        return ( relNum, title, crc32, publisher, releasedBy, location )

    def getCRC( self, gameNode ):
        for crc in gameNode.getElementsByTagName( 'romCRC' ):
            if crc.getAttribute( 'extension' ) != '.nds':
                continue
            else:
                return int( getText( crc.childNodes ), 16 )
        return None
