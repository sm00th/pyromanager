import unittest
import pyNDSrom

class NDSFile_test( unittest.TestCase ):
    def testRead( self ):
        testFile = pyNDSrom.NDSFile( '../tests/TinyFB.nds' )
        self.assertEqual( testFile.filePath   , '../tests/TinyFB.nds' )
        self.assertEqual( testFile.gameTitle  , 'NDS.TinyFB' )
        self.assertEqual( testFile.gameCode   , '####' )
        self.assertEqual( testFile.makerCode  , 'N0' )
        self.assertEqual( testFile.unitCode   , 0 )
        self.assertEqual( testFile.encryption , 0 )
        self.assertEqual( testFile.capacity   , 16 )
        self.assertEqual( testFile.crc32      , 0x1ece1d01 )


class db_test( unittest.TestCase ):
    def testParse( self ):
        db = pyNDSrom.AdvansceneXML( '../tests/nds.xml' )
        self.assertEqual( db.filePath           , '../tests/nds.xml' )
        self.assertEqual( len( db.gameList )    , 7 )
        self.assertEqual( len( db.gameList[0] ) , 6 )

    def testFileNameParser( self ):
        testNames = {
            "games/0028 - Kirby - Canvas Curse (USA).NDS"                                                  : [ 28, "kirby canvas curse" ],
            "../more/depth/(3686) - Zubo (USA) (En,Fr,Es).nds"                                             : [ 3686, "zubo" ],
            "[3686] Zubo.nds"                                                                              : [ 3686, "zubo" ],
            "Shin Megami Tensei - Strange Journey.nds"                                                     : [ None, "shin megami tensei strange journey" ],
            "1514_-_The_Legend_of_Zelda_Phantom_Hourglass.nds"                                               : [ 1514, "legend of zelda phantom hourglass" ],
            "9 Hours 9 Persons 9 Doors.nds"                                                                : [ None, "9 hours 9 persons 9 doors" ],
            "123 - 9 Hours, 9 Persons, 9 Doors.nds"                                                        : [ 123, "9 hours 9 persons 9 doors" ],
            "3776 - Broken Sword - Shadow of the Templars - The Director's Cut (USA) (En,Fr,De,Es,It).nds" : [ 3776, "broken sword shadow of templars directors cut" ],
        }
        for( fileName, expectedResult ) in testNames.iteritems():
            self.assertListEqual( pyNDSrom.parseFileName( fileName ), expectedResult )

    #TODO: actually test something here
    def testSQLImport( self ):
        db    = pyNDSrom.SQLdb( '../tests/sql' )
        xmlDB = pyNDSrom.AdvansceneXML( '../tests/nds.xml' )
        db.importKnownFrom( xmlDB )

if __name__ == '__main__':
    unittest.main()
