import os
import re
import struct
import binascii
import pyNDSrom

def byteToString( byteString ):
    string = ''
    try:
        string = byteString.decode( 'utf-8' ).rstrip( '\x00' )
    except Exception as e:
        print 'Failed to decode string: %s' % ( e )
    return string

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

    def isValid( self ):
        valid = 1
        if self.capacity > 4096:
            valid = 0
        return valid

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

    def getGameList( self, path ):
        gameList = []
        dirList = os.listdir( path )
        for fileName in dirList:
            fullPath = path + "/" + fileName
            if os.path.isdir( fullPath ):
                self.getGameList( fullPath )
            # FIXME: ugly nesting
            else:
                if re.search( "\.nds$", fullPath, flags = re.IGNORECASE ):
                    game = NDSFile( fullPath )
                    if game.isValid():
                        gameInfo = self.db.searchByCRC( game.crc32 )
                        if gameInfo:
                            gameInfo.insert( 0, fullPath )
                            gameList.append( gameInfo )
                        else:
                            ( releaseNumber, gameName ) = pyNDSrom.xmlDB.parseFileName( fullPath )
                            gameInfo = self.db.searchByReleaseNumber( releaseNumber )
                            if gameInfo:
                                gameInfo.insert( 0, fullPath )
                                gameList.append( gameInfo )
                            else:
                                gameInfo = self.db.searchByName( gameName )
                                if gameInfo:
                                    gameInfo.insert( 0, fullPath )
                                    gameList.append( gameInfo )



        return gameList
