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

    def qustionableFile( self, dbRelNum, ndsPath ):
        result = 0
        if type( dbRelNum ) == int:
            gameInfo = self.db.getGameInfo( dbRelNum )
            print "File '%s' was identified as %d - %s (%s) Released by: %s" % (
                    re.sub( r"^.*(/|:)", '', ndsPath ),
                    gameInfo[0],
                    gameInfo[1],
                    pyNDSrom.db.decodeLocation( gameInfo[4] ),
                    gameInfo[3],
                )
            result = pyNDSrom.ui.question_yn( "Is this correct?" )
        elif type( dbRelNum ) == list:
            print "File '%s' can be one of the following:" % ( re.sub( r"^.*(/|:)", '', ndsPath ) )
            index = 0
            for relNum in dbRelNum:
                gameInfo = self.db.getGameInfo( relNum )
                # FIXME: reeeeeeealy need lang here
                print " %d. %d - %s (%s) Released by: %s" % ( index, gameInfo[0],
                        gameInfo[1], pyNDSrom.db.decodeLocation( gameInfo[4] ), gameInfo[3] )
                index += 1
            result = pyNDSrom.ui.listQuestion( "Which one?", range(index) + [None] )

        return result

    def processNDSFile( self, ndsPath, interactive=1 ):
        dbRelNum = None
        game = NDSFile( ndsPath )
        if game.isValid():
            dbRelNum = self.db.searchByCRC( game.crc32 )
            if not dbRelNum:
                ( releaseNumber, gameName ) = pyNDSrom.db.parseFileName( ndsPath )
                foundByRelNum   = self.db.searchByReleaseNumber( releaseNumber )
                foundByNameList = self.db.searchByName( gameName )
                if foundByRelNum in foundByNameList:
                    dbRelNum = foundByRelNum
                else:
                    if foundByRelNum and self.qustionableFile( foundByRelNum, ndsPath ):
                        dbRelNum = foundByRelNum
                    else:
                        if foundByNameList:
                            answer = self.qustionableFile( foundByNameList, ndsPath )
                            if answer:
                                dbRelNum = foundByNameList[answer]
        else:
            dbRelNum = 0

        return dbRelNum

    def scanIntoDB( self, path, quiet=0, interactive=1 ):
        dirList = os.listdir( path )
        for fileName in dirList:
            fullPath = path + "/" + fileName
            if os.path.isdir( fullPath ):
                self.scanIntoDB( fullPath )
            # FIXME: ugly nesting
            else:
                gameInfo = None
                if re.search( "\.nds$", fullPath, flags = re.IGNORECASE ):
                    gameInfo = self.processNDSFile( fullPath, interactive )
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
                                gameInfo = self.processNDSFile( '/tmp/' + archiveFile, interactive )

                                if gameInfo != 0:
                                    self.db.addLocalRom( os.path.abspath( fullPath ) + ":" + archiveFile, gameInfo )
                                os.unlink( '/tmp/' + archiveFile )
                        zipFile.close()
                    except Exception as e:
                        print "Failed parsing zip-archive %s: %s" % ( fullPath, e )

        return 1
