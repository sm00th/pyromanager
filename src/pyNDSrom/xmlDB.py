''' Classes to import data from various xml databases '''
from xml.dom import minidom
import re

def parseFileName( fileName ):
    releaseNum = None

    fileName = fileName.lower()
    fileName = re.sub( "\.nds$", '', fileName )
    fileName = re.sub( "_", ' ', fileName )

    releaseNum_pattern = re.compile( r"(\[|\()?(\d+)(\]|\))?\s*-?(.*)" )
    matchReleaseNum = releaseNum_pattern.match( fileName )
    if matchReleaseNum:
        releaseNum = int( matchReleaseNum.group( 2 ) )
        fileName = matchReleaseNum.group( 4 )

    fileName = re.sub( r"(\(|\[)[^\(\)\[\]]*(\)|\])", '', fileName )
    fileName = re.sub( r"the", '', fileName )
    fileName = re.sub( r"[^\w\d\s]", '', fileName )
    fileName = re.sub( r"\s+", ' ', fileName )
    fileName = fileName.strip()
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
            return game
    return None

def searchByName( gameList, gameName ):
    for game in gameList:
        # TODO: Levenshtein distance is good enough, probably
        # also something to strip or process non-name info like release number
        # and regioncode in filename    
        if game[0] == gameName:
            return game
    return None

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

    def parseGame( self, gameNode ):
        title = getText( gameNode.getElementsByTagName( 'title' )[0].childNodes )
        relNum = int( getText( gameNode.getElementsByTagName( 'releaseNumber' )[0].childNodes ) )
        crc32 = self.getCRC( gameNode )
        return [ title, relNum, crc32 ]

    def searchByCRC( self, crc32 ):
        return searchByCRC( self.gameList, crc32 )

    def searchByName( self, name ):
        return searchByName( self.gameList, name )

    def getCRC( self, gameNode ):
        for crc in gameNode.getElementsByTagName( 'romCRC' ):
            if crc.getAttribute( 'extension' ) != '.nds':
                continue
            else:
                return int( getText( crc.childNodes ), 16 )
        return None
