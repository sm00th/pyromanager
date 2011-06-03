import os
import re
import struct
import binascii
import pyNDSrom
import zipfile

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
            self.gameTitle  = byteToString( nds.read( 12 ) )
            self.gameCode   = byteToString( nds.read( 4 ) )
            self.makerCode  = byteToString( nds.read( 2 ) )
            self.unitCode   = byteToInt( nds.read( 1 ) )
            self.encryption = byteToInt( nds.read( 1 ) )
            self.capacity   = capsize( byteToInt( nds.read( 2 ) ) )

            nds.seek( 0 )
            self.crc32 = binascii.crc32( nds.read() ) & 0xFFFFFFFF

            nds.close()
        except IOError:
            raise Exception( 'Failed to parse file' )

class DirScanner:
    def __init__( self, dbPath ):
        self.db = pyNDSrom.db.SQLdb( dbPath )

    def processNDSFile( self, ndsPath ):
        gameInfo = None
        game = NDSFile( ndsPath )
        if game.isValid():
            gameInfo = self.db.searchByCRC( game.crc32 )
            if not gameInfo:
                ( releaseNumber, gameName ) = pyNDSrom.db.parseFileName( ndsPath )
                gameInfo = self.db.searchByReleaseNumber( releaseNumber )
                if not gameInfo:
                    gameInfo = self.db.searchByName( gameName )
        else:
            gameInfo = 0

        return gameInfo

    def scanIntoDB( self, path, quiet=0, interactive=0 ):
        dirList = os.listdir( path )
        for fileName in dirList:
            fullPath = path + "/" + fileName
            if os.path.isdir( fullPath ):
                self.scanIntoDB( fullPath )
            # FIXME: ugly nesting
            else:
                gameInfo = None
                if re.search( "\.nds$", fullPath, flags = re.IGNORECASE ):
                    gameInfo = self.processNDSFile( fullPath )
                    if gameInfo != 0:
                        self.db.addLocalRom( os.path.abspath( fullPath ), gameInfo )
                elif re.search( "\.zip$", fullPath, flags = re.IGNORECASE ):
                    try:
                        zipFile = zipfile.ZipFile( fullPath, "r" )
                        for archiveFile in zipFile.namelist():
                            if re.search( "\.nds$", archiveFile, flags = re.IGNORECASE ):
                                # TODO: maybe we can use zipfile.read instead of actually unzipping stuff
                                # NB: hardcoding /tmp/ is probably an awfull idea
                                zipFile.extract( archiveFile, '/tmp/' )
                                gameInfo = self.processNDSFile( '/tmp/' + archiveFile )

                                if gameInfo != 0:
                                    self.db.addLocalRom( os.path.abspath( fullPath ) + ":" + archiveFile, gameInfo )
                                os.unlink( '/tmp/' + archiveFile )
                        zipFile.close()
                    except Exception as e:
                        print "Failed parsing zip-archive %s: %s" % ( fullPath, e )

        return 1
