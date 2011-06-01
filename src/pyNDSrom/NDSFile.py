import os
import struct
import binascii
import pyNDSrom

def byteToString( byteString ):
    return byteString.decode( 'utf-8' ).rstrip( '\x00' )

def byteToInt( byteString ):
    return struct.unpack( 'i', byteString + ( '\x00' * ( 4 - len( byteString ) ) ) )[0]

def capsize( cap ):
    return pow( 2, 20 + cap ) / 8388608

class NDSFile:
    ''' Reads and(maybe) writes the contents of .nds files '''
    def __init__( self, filePath ):
        self.filePath = filePath
        self.gameTitle = None
        self.gameCode = None
        self.makerCode = None
        self.unitCode = None
        self.encryption = None
        self.capacity = None
        self.crc32 = None
        self.parseFile()

    def parseFile( self ):
        try:
            nds = open( self.filePath, 'rb' )

            nds.seek( 0 )
            self.gameTitle = byteToString( nds.read( 12 ) )
            self.gameCode = byteToString( nds.read( 4 ) )
            self.makerCode = byteToString( nds.read( 2 ) )
            self.unitCode = byteToInt( nds.read( 1 ) )
            self.encryption = byteToInt( nds.read( 1 ) )
            self.capacity = capsize( byteToInt( nds.read( 2 ) ) )

            nds.seek( 0 )
            self.crc32 = binascii.crc32( nds.read() ) & 0xFFFFFFFF

            nds.close()
        except IOError:
            raise Exception( 'Failed to parse file' )

class DirScanner:
    def __init__( self, dbPath ):
        self.db = pyNDSrom.xmlDB.AdvansceneXML( dbPath )
        import pprint
        pprint.pprint( self.db )

    def getGameList( self, path ):
        gameList = []
        dirList = os.listdir( path )
        for fileName in dirList:
            fullPath = path + "/" + fileName
            if os.path.isdir( fullPath ):
                self.getGameList( fullPath )
            else:
                game = NDSFile( fullPath )
                gameInfo = self.db.searchByCRC( game.crc32 ) # TODO: add search by name 
                if gameInfo:
                    gameInfo.insert( 0, fullPath )
                    gameList.append( gameInfo )

        return gameList