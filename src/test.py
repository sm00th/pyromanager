import unittest
import pyNDSrom

class NDSFile_test( unittest.TestCase ):
    def testRead( self ):
        testFile = pyNDSrom.NDSFile( '../tests/TinyFB.nds' )
        self.assertEqual( testFile.filePath, '../tests/TinyFB.nds' )
        self.assertEqual( testFile.gameTitle, 'NDS.TinyFB' )
        self.assertEqual( testFile.gameCode, '####' )
        self.assertEqual( testFile.makerCode, 'N0' )
        self.assertEqual( testFile.unitCode, 0 )
        self.assertEqual( testFile.encryption, 0 )
        self.assertEqual( testFile.capacity, 16 )
        self.assertEqual( testFile.crc32, 0x1ece1d01 )

    def testScanDir( self ):
        scanner = pyNDSrom.DirScanner( '../tests/nds.xml' )
        self.assertListEqual( scanner.getGameList( '../tests' ), [ ['../tests/TinyFB.nds', 'TinyFB', 999999, 0x1ece1d01] ] )

class XMLdb_test( unittest.TestCase ):
    def testParse( self ):
        db = pyNDSrom.AdvansceneXML( '../tests/nds.xml' )
        self.assertEqual( db.filePath, '../tests/nds.xml' )
        self.assertEqual( len( db.gameList ), 7 )
        self.assertEqual( len( db.gameList[0] ), 3 )
        self.assertListEqual( db.searchByCRC( 0xB760405B ), [ 'Coropata', 4710, 0xB760405B ] )
        self.assertEqual( db.searchByCRC( 0xFFFFFFFF ), None )
        self.assertListEqual( db.searchByName( 'Coropata' ), [ 'Coropata', 4710, 0xB760405B ] )

if __name__ == '__main__':
    unittest.main()
