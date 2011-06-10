import os, re
import pyNDSrom

class rom:
    '''internal representation of roms'''

    def __init__( self ):
        self.release_number  = None
        self.name            = None
        self.normalized_name = None
        self.size            = None
        self.publisher       = None
        self.region          = None
        self.path            = None

    def __str__( self ):
        return "%d - %s (%s) Size: %s" % ( self.release_number, self.name, self.region, self.size )

class scanner:
    def __init__( self, dbPath ):
        self.db = pyNDSrom.db.SQLdb( dbPath )


    def scanIntoDB( self, path, scanSubDirs=1, interactive=1 ):
        dirList = os.listdir( path )
        for fileName in dirList:
            fullPath = path + "/" + fileName
            if os.path.isdir( fullPath ) and scanSubDirs:
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
                ( releaseNumber, gameName, locationId ) = pyNDSrom.db.parseFileName( ndsPath )
                foundByRelNum   = self.db.searchByReleaseNumber( releaseNumber )
                foundByNameList = self.db.searchByName( gameName, locationId )
                if foundByRelNum in foundByNameList:
                    dbRelNum = foundByRelNum
                else:
                    if foundByRelNum and self.qustionableFile( foundByRelNum, ndsPath ):
                        dbRelNum = foundByRelNum
                    else:
                        if foundByNameList:
                            if len( foundByNameList ) == 1 and self.qustionableFile( foundByNameList[0], ndsPath):
                                dbRelNum = foundByNameList[0]
                            else:
                                answer = self.qustionableFile( foundByNameList, ndsPath )
                                if answer:
                                    dbRelNum = foundByNameList[answer]
        else:
            dbRelNum = 0

        return dbRelNum
