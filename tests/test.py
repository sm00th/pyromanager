import unittest
import os
import pyNDSrom.db
import pyNDSrom.file
import pyNDSrom.rom
import pyNDSrom.cfg

class cfg_test( unittest.TestCase ):
    def test_default_paths( self ):
        config = pyNDSrom.cfg.Config()
        self.assertEqual( config.rc_file, os.path.expanduser(
            '~/.pyROManager.rc' ) )
        self.assertEqual( config.db_file, os.path.expanduser(
            '~/.pyROManager/pyro.db' ) )
        self.assertEqual( config.xml_file, os.path.expanduser(
            '~/.pyROManager/advanscene.xml' ) )
        self.assertEqual( config.flashcart, os.path.expanduser(
            '/mnt/ds' ) )

    def test_extensions( self ):
        config = pyNDSrom.cfg.Config()
        # FIXME: its not always like that
        self.assertListEqual( config.extensions, [ 'nds', 'zip', '7z', 'rar' ] )

    def test_regions( self ):
        config = pyNDSrom.cfg.Config()
        self.assertEqual( config.region_name( 0 ), 'EUR' )
        self.assertEqual( config.region_name( 0, 0 ), 'Europe' )
        self.assertEqual( config.region_name( 0, 1 ), 'EUR' )
        self.assertEqual( config.region_name( 0, 2 ), 'E' )

        self.assertEqual( config.region_code( 'Japan' ), 7 )
        self.assertEqual( config.region_code( 'JPN' ), 7 )
        self.assertEqual( config.region_code( 'J' ), 7 )

    def test_rc( self ):
        config = pyNDSrom.cfg.Config( 'tests/test.rc' )
        config.read_config()
        self.assertEqual( config.rc_file, os.path.expanduser(
            'tests/test.rc' ) )
        self.assertEqual( config.db_file, os.path.expanduser(
            '~/.pyROManager/sql.db' ) )
        self.assertEqual( config.xml_file, os.path.expanduser(
            '~/.pyROManager/adv.xml' ) )
        self.assertEqual( config.flashcart, os.path.expanduser(
            '/home/sm00th/flash' ) )

class rom_test( unittest.TestCase ):
    def test_norm_name( self ):
        rom = pyNDSrom.rom.Rom()
        self.assertEqual( rom.normalized_name, None )
        rom.set_file_info( ( '/path/to/Epic_File_-_OMG', 1235, 9432 ) )
        self.assertEqual( rom.normalized_name, 'epic file omg' )
        rom.rom_info['normalized_name'] = 'hey'
        self.assertEqual( rom.normalized_name, 'hey' )

class file_test( unittest.TestCase ):
    def test_extension( self ):
        self.assertEqual( pyNDSrom.file.extension( 'path/to/somefile.wTf' ),
                'wtf' )

    def test_search( self ):
        config = pyNDSrom.cfg.Config()
        self.assertEqual( len( pyNDSrom.file.search( '', config ) ), 3 )

    def test_nds( self ):
        testFile = pyNDSrom.file.NDS( 'tests/TinyFB.nds' )

        self.assertEqual( testFile.rom['title'] , 'NDS.TinyFB' )
        self.assertEqual( testFile.rom['code']  , '####' )
        self.assertEqual( testFile.rom['maker'] , 'N0' )
        self.assertEqual( testFile.rom['crc32'] , 0x1ece1d01 )

        self.assertEqual( testFile.hardware['unit_code']  , 0 )
        self.assertEqual( testFile.hardware['encryption'] , 0 )
        self.assertEqual( testFile.hardware['capacity']   , 16 )

    def test_parse_filename( self ):
        testNames = {
            "games/0028 - Kirby - Canvas Curse (EUR).NDS"      : [ 28, "kirby canvas curse", 0 ],
            "more/depth/(3686) - Zubo (USA) (En,Fr,Es).nds"    : [ 3686, "zubo", 1 ],
            "[3686] Zubo.nds"                                  : [ 3686, "zubo", None ],
            "Shin Megami Tensei - Strange Journey.nds"         : [ None, "shin megami tensei strange journey", None ],
            "1514_-_The_Legend_of_Zelda_Phantom_Hourglass.nds" : [ 1514, "legend of zelda phantom hourglass", None ],
            "9 Hours 9 Persons 9 Doors.nds"                    : [ None, "9 hours 9 persons 9 doors", None ],
            "123 - 9 Hours, 9 Persons, 9 Doors.nds"            : [ 123, "9 hours 9 persons 9 doors", None ],
            "3776 - Broken Sword - Shadow of the Templars - The Director's Cut [USA] (En,Fr,De,Es,It).nds" : 
                [ 3776, "broken sword shadow of templars directors cut", 1 ],
        }
        for( fileName, expectedResult ) in testNames.iteritems():
            self.assertListEqual( pyNDSrom.file.parse_filename( fileName ), expectedResult )

class db_test( unittest.TestCase ):
    def test_advanscene( self ):
        db = pyNDSrom.db.AdvansceneXML( 'tests/nds.xml' )
        db.parse()
        self.assertEqual( len( db.rom_list )    , 7 )
        self.assertEqual( len( db.rom_list[0] ) , 7 )


    #TODO: actually test something here
    def test_import_known( self ):
        db    = pyNDSrom.db.SQLdb( 'tests/sql' )
        xmlDB = pyNDSrom.db.AdvansceneXML( 'tests/nds.xml' )
        xmlDB.parse()
        db.import_known( xmlDB )

if __name__ == '__main__':
    unittest.main()
