import unittest
import pyNDSrom.db
import pyNDSrom.file

class file_test( unittest.TestCase ):
    def test_extension( self ):
        self.assertEqual( pyNDSrom.file.extension( '../path/to/somefile.wtf' ),
                'wtf' )

    def test_fileList( self ):
        self.assertEqual( len( pyNDSrom.file.search( '../' ) ), 3 )

    def test_nds( self ):
        testFile = pyNDSrom.file.NDS( '../tests/TinyFB.nds' )
        self.assertEqual( testFile.file_path   , '../tests/TinyFB.nds' )

        self.assertEqual( testFile.rom['title'] , 'NDS.TinyFB' )
        self.assertEqual( testFile.rom['code']  , '####' )
        self.assertEqual( testFile.rom['maker'] , 'N0' )
        self.assertEqual( testFile.rom['crc32'] , 0x1ece1d01 )

        self.assertEqual( testFile.hardware['unit_code']  , 0 )
        self.assertEqual( testFile.hardware['encryption'] , 0 )
        self.assertEqual( testFile.hardware['capacity']   , 16 )


class db_test( unittest.TestCase ):
    def testParse( self ):
        db = pyNDSrom.db.AdvansceneXML( '../tests/nds.xml' )
        self.assertEqual( db.filePath           , '../tests/nds.xml' )
        self.assertEqual( len( db.gameList )    , 7 )
        self.assertEqual( len( db.gameList[0] ) , 6 )

    def testFileNameParser( self ):
        testNames = {
            "games/0028 - Kirby - Canvas Curse (EUR).NDS"                                                  : [ 28, "kirby canvas curse", 0 ],
            "../more/depth/(3686) - Zubo (USA) (En,Fr,Es).nds"                                             : [ 3686, "zubo", 1 ],
            "[3686] Zubo.nds"                                                                              : [ 3686, "zubo", None ],
            "Shin Megami Tensei - Strange Journey.nds"                                                     : [ None, "shin megami tensei strange journey", None ],
            "1514_-_The_Legend_of_Zelda_Phantom_Hourglass.nds"                                             : [ 1514, "legend of zelda phantom hourglass", None ],
            "9 Hours 9 Persons 9 Doors.nds"                                                                : [ None, "9 hours 9 persons 9 doors", None ],
            "123 - 9 Hours, 9 Persons, 9 Doors.nds"                                                        : [ 123, "9 hours 9 persons 9 doors", None ],
            "3776 - Broken Sword - Shadow of the Templars - The Director's Cut [USA] (En,Fr,De,Es,It).nds" : [ 3776, "broken sword shadow of templars directors cut", 1 ],
        }
        for( fileName, expectedResult ) in testNames.iteritems():
            self.assertListEqual( pyNDSrom.db.parse_filename( fileName ), expectedResult )

    #TODO: actually test something here
    def testSQLImport( self ):
        db    = pyNDSrom.db.SQLdb( '../tests/sql' )
        xmlDB = pyNDSrom.db.AdvansceneXML( '../tests/nds.xml' )
        db.import_known( xmlDB )

if __name__ == '__main__':
    unittest.main()
