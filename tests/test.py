import unittest
import os
import pyromanager.cfg
import pyromanager.db
import pyromanager.rom

class cfg_test( unittest.TestCase ):
    def test_defaults( self ):
        config = pyromanager.cfg.Config()
        self.assertEqual( config.rc_file, os.path.expanduser(
            '~/.pyromgr.rc' ) )
        self.assertEqual( config.db_file, os.path.expanduser(
            '~/.pyromgr/pyromgr.db' ) )
        self.assertEqual( config.xml_file, os.path.expanduser(
            '~/.pyromgr/advanscene.xml' ) )
        self.assertEqual( config.flashcart, os.path.expanduser(
            '/mnt/ds' ) )
        self.assertEqual( config.tmp_dir, os.path.expanduser(
            '/tmp' ) )
        self.assertEqual( config.saves_dir, os.path.expanduser(
            '~/.pyromgr/saves' ) )
        self.assertEqual( config.save_ext, os.path.expanduser(
            'sav' ) )
        self.assertTrue( 'nds' in config.extensions )

    def test_bin( self ):
        self.assertTrue( pyromanager.cfg.is_bin_available( 'ls' ) )
        self.assertFalse( pyromanager.cfg.is_bin_available(
            'there_is_no_way_this_is_in_your_path' ) )

    def test_regions( self ):
        config = pyromanager.cfg.Config()
        self.assertEqual( config.region_name( 0 ), 'EUR' )
        self.assertEqual( config.region_name( 0, 0 ), 'Europe' )
        self.assertEqual( config.region_name( 0, 1 ), 'EUR' )
        self.assertEqual( config.region_name( 0, 2 ), 'E' )
        self.assertEqual( config.region_name( 0, 9 ), 'EUR' )
        self.assertEqual( config.region_name( 999 ), 'Unknown: 999' )

        self.assertEqual( config.region_code( 'Japan' ), 7 )
        self.assertEqual( config.region_code( 'JPN' ), 7 )
        self.assertEqual( config.region_code( 'J' ), 7 )
        self.assertEqual( config.region_code( 'Zimbabwe' ), None )

    def test_rc( self ):
        config = pyromanager.cfg.Config( 'tests/test.rc' )
        config.read_config()
        self.assertEqual( config.rc_file, 'tests/test.rc' )
        self.assertEqual( config.db_file, os.path.expanduser(
            '~/.pyromgr/sql.db' ) )
        self.assertEqual( config.xml_file, os.path.expanduser(
            '~/.pyromgr/adv.xml' ) )
        self.assertEqual( config.flashcart, '/home/someuser/flash' )
        self.assertEqual( config.tmp_dir, '/tmp' )
        self.assertEqual( config.saves_dir, os.path.expanduser(
            '~/.pyromgr/saves' ) )
        self.assertEqual( config.save_ext, os.path.expanduser(
            '0' ) )

class db_test( unittest.TestCase ):
    def setUp( self ):
        self.config = pyromanager.cfg.Config( 'tests/test.rc' )
        self.config._paths['assets_dir'] = 'tests'
        self.config.read_config()
        self.db = pyromanager.db.SQLdb( self.config.db_file, self.config )

    def tearDown( self ):
        del( self.db )
        os.unlink( self.config.db_file )

    def test_db( self ):
        xmldb = pyromanager.db.AdvansceneXML( 'tests/nds.xml', self.config )
        xmldb.parse()
        self.assertEqual( len( xmldb )    , 7 )
        self.assertTupleEqual( xmldb[0], (4710, u'Coropata', 3076538459L,
            u'LukPlus', u'BAHAMUT', 7, u'coropata') )

        self.db.import_known( xmldb )

        self.assertListEqual( self.db.search_crc( 3076538459L ), [ 4710 ] )
        self.assertListEqual( self.db.search_crc( 3976938459L ), [] )

        self.assertListEqual( self.db.search_name( 'Coropata' ), [ 4710 ],
                'Full name' )
        self.assertListEqual( self.db.search_name( 'ropat' ), [ 4710 ],
                'Partial name' )
        self.assertListEqual( self.db.search_name( 'ropat', 7 ), [ 4710 ],
                'Partial name with region' )
        self.assertListEqual( self.db.search_name( 'No its not' ), [] )

        self.assertTupleEqual( self.db.rom_info( 4710 ), (4710, u'Coropata',
            u'LukPlus', u'BAHAMUT', 7, u'coropata') )

        self.db.add_local( ( 4999, '/some/path/to/file.nds', 'something', 1231,
            9812312 ) )
        self.assertListEqual( self.db.search_local( 'release_id', 'size', 1231 ), [
            4999 ] )
        self.assertTupleEqual( self.db.file_info( 1 ), ( 4999,
            '/some/path/to/file.nds', 1231, 9812312 ) )

        self.db.add_local( ( 9821, '/some/path/to/other_file.nds',
            'something_else', 1231, 234987123 ) )
        self.assertListEqual( self.db.search_local( 'release_id', 'size', 1231 ), [
            4999, 9821 ] )
        self.db.add_local( ( 9823, '/some/path/to/yet_another_file.nds',
            'dupe', 1231, 9812312 ) )
        self.assertListEqual( self.db.find_dupes(), [ (2, 9812312) ] )

        self.db.remove_local( '/some/path/to/yet_another_file.nds' )
        self.assertListEqual( self.db.find_dupes(), [] )
        self.db.save()

        self.assertListEqual( self.db.path_list(), [u'/some/path/to/file.nds',
            u'/some/path/to/other_file.nds'] )

        self.assertTrue( self.db.already_in_local( '/some/path/to/file.nds' ) )
        self.assertFalse( self.db.already_in_local( '/wrong/path/to/file.nds' ) )

class rom_test( unittest.TestCase ):
    def setUp( self ):
        self.config = pyromanager.cfg.Config( 'tests/test.rc' )
        self.config._paths['assets_dir'] = 'tests'
        self.config.read_config()
        self.db = pyromanager.db.SQLdb( self.config.db_file, self.config )

        xmldb = pyromanager.db.AdvansceneXML( 'tests/nds.xml', self.config )
        xmldb.parse()
        self.db.import_known( xmldb )

    def tearDown( self ):
        del( self.db )
        os.unlink( self.config.db_file )

    def test_RomInfo( self ):
        rominfo = pyromanager.rom.RomInfo( 4710, self.db, self.config )
        self.assertEqual( rominfo.filename, '4710 - Coropata (JPN).nds' )
        self.assertEqual( rominfo.__str__(), '4710 - Coropata (JPN) [BAHAMUT]' )

    def test_FileInfo_file( self ):
        finfo = pyromanager.rom.FileInfo( 'tests/TinyFB.nds', self.db, self.config )
        self.assertFalse( finfo.is_initialized() )
        finfo.init()
        self.assertTrue( finfo.is_initialized() )
        self.assertFalse( finfo.is_archived() )
        self.assertTrue( finfo.is_valid() )
        self.assertEqual( finfo.normalized_name, 'tinyfb' )
        self.assertEqual( finfo.size, 352 )
        self.assertEqual( finfo.size_mb, '0.00M' )
        self.assertEqual( finfo.crc, 516824321L )

        rinf = finfo.get_rom_info()
        self.assertIsInstance( rinf, pyromanager.rom.RomInfo )

        self.assertEqual( finfo.__str__(), "tinyfb (tests/TinyFB.nds)" )

    def test_FileInfo_invalid( self ):
        finfo = pyromanager.rom.FileInfo( 'tests/fake.nds', self.db, self.config )
        self.assertFalse( finfo.is_valid() )

    def test_FileInfo_archive( self ):
        finfo = pyromanager.rom.FileInfo( 'tests/TinyFB.zip:TinyFB.nds', self.db, self.config )
        self.assertFalse( finfo.is_initialized() )
        finfo.init()
        self.assertTrue( finfo.is_initialized() )
        self.assertTrue( finfo.is_archived() )
        self.assertTrue( finfo.is_valid() )
        self.assertEqual( finfo.normalized_name, 'tinyfb' )

    def test_FileInfo_lid( self ):
        self.db.add_local( ( 4999, '/some/path/to/file.nds', 'something',
            123187123, 9812312 ) )
        finfo = pyromanager.rom.FileInfo( None, self.db, self.config, 1 )
        self.assertTrue( finfo.is_initialized() )
        self.assertEqual( finfo.normalized_name, 'file' )
        self.assertEqual( finfo.size, 123187123 )
        self.assertEqual( finfo.size_mb, '117.48M' )
        self.assertEqual( finfo.crc, 9812312 )
        rinf = finfo.get_rom_info()
        self.assertIsInstance( rinf, pyromanager.rom.RomInfo )

    def test_Rom( self ):
        romobj = pyromanager.rom.Rom( 'tests/TinyFB.nds', self.db, self.config )
        self.assertTrue( romobj.is_valid() )
        self.assertTrue( romobj.is_initialized() )
        self.assertFalse( romobj.is_in_db() )
        romobj.add_to_db()
        self.assertTrue( romobj.is_in_db() )
        self.assertTrue( 'tests/TinyFB.nds' in romobj.path )
        self.assertEqual( romobj.normalized_name, 'tinyfb testrom' )
        save = romobj.get_saves()[0]
        self.assertIsInstance( save, pyromanager.rom.SaveFile )
        self.assertTrue( save.stored() )
        self.assertEqual( romobj.__str__(), '999999 - TinyFB - TestRom ' + \
                '(USA) [Independent] 0.00M' )

    def test_Nds( self ):
        testFile = pyromanager.rom.Nds( 'tests/TinyFB.nds' )
        testFile.parse()

        self.assertEqual( testFile.rom['title'] , 'NDS.TinyFB' )
        self.assertEqual( testFile.rom['code']  , '####' )
        self.assertEqual( testFile.rom['maker'] , 'N0' )
        self.assertEqual( testFile.rom['crc32'] , 0x1ece1d01 )

        self.assertEqual( testFile.hardware['unit_code']  , 0 )
        self.assertEqual( testFile.hardware['encryption'] , 0 )
        self.assertEqual( testFile.hardware['capacity']   , 16 )

    def test_parse_filename( self ):
        testNames = {
            "games/0028 - Kirby - Canvas Curse (EUR).NDS"      : ( 28, "kirby canvas curse", 0 ),
            "more/depth/(3686) - Zubo (USA) (En,Fr,Es).nds"    : ( 3686, "zubo", 1 ),
            "(3686) Zubo.nds"                                  : ( 3686, "zubo", None ),
            "Shin Megami Tensei - Strange Journey.nds"         : ( None, "shin megami tensei strange journey", None ),
            "1514_-_The_Legend_of_Zelda_Phantom_Hourglass.nds" : ( 1514, "legend of zelda phantom hourglass", None ),
            "9 Hours 9 Persons 9 Doors.nds"                    : ( None, "9 hours 9 persons 9 doors", None ),
            "123 - 9 Hours, 9 Persons, 9 Doors.nds"            : ( 123, "9 hours 9 persons 9 doors", None ),
            "3776 - Broken Sword - Shadow of the Templars - The Director's Cut (USA) (En,Fr,De,Es,It).nds" : 
                ( 3776, "broken sword shadow of templars directors cut", 1 ),
        }
        config = pyromanager.cfg.Config( 'tests/test.rc' )
        for( fileName, expectedResult ) in testNames.iteritems():
            self.assertTupleEqual( pyromanager.rom.parse_filename( fileName,
                config ), expectedResult )

    def test_extension( self ):
        self.assertEqual( pyromanager.rom.extension( 'path/to/somefile.wTf' ),
                'wtf' )

    def test_search( self ):
        config = pyromanager.cfg.Config()
        self.assertEqual( len( pyromanager.rom.search( '', config ) ), 3 )

if __name__ == '__main__':
    unittest.main()
