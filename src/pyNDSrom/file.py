'''File operations'''
import os, re, zipfile, subprocess
import struct, binascii
import db, ui, cfg, rom
from sqlite3 import OperationalError

def mkdir( path ):
    '''Create dir if not exists'''
    if not os.path.exists( path ):
        os.mkdir( path )

def extension( file_name ):
    '''Returns the extension of specified file'''
    result = ''
    match  = re.match( r".*\.([^.]+)$", file_name )
    if match:
        result = match.group( 1 ).lower()

    return result

def search( path, config ):
    '''Returns list of acceptable files'''
    result = []
    try:
        path = os.path.abspath( path )
        for file_name in os.listdir( path ):
            file_path = '%s/%s' % ( path, file_name )
            if os.path.isdir( file_path ):
                result += search( file_path, config )
            else:
                ext = extension( file_path )
                if ext in config.extensions:
                    result.append( ( file_path, ext ) )
    except OSError as exc:
        print "Can't scan path %s: %s" % ( path, exc )
    return result

def byte_to_string( byte_string ):
    '''Decodes bytestring as string'''
    string = ''
    try:
        string = byte_string.decode( 'utf-8' ).rstrip( '\x00' )
    except UnicodeDecodeError as exc:
        print 'Failed to decode string: %s' % ( exc )
    return string

def byte_to_int( byte_string ):
    '''Decodes bytestring as int'''
    return struct.unpack( 
        'i',
        byte_string +
        ( '\x00' * ( 4 - len( byte_string ) ) )
    )[0]

def capsize( cap ):
    '''Returns capacity size of original cartridge'''
    return pow( 2, 20 + cap ) / 8388608

def scan( path, opts ):
    '''Scan path for roms'''
    config = cfg.Config()
    config.read_config()
    database = db.SQLdb( config.db_file )
    for file_info in search( path, config ):
        # TODO: think about factory
        if opts.full_rescan or not database.already_in_local( file_info[0], 0 ):
            try:
                if file_info[1] == 'nds':
                    rom_file = NDS( file_info[0], database )
                elif file_info[1] == 'zip':
                    rom_file = ZIP( file_info[0], database )
                    rom_file.scan_files()
                elif file_info[1] == '7z':
                    rom_file = ZIP7( file_info[0], database )
                    rom_file.scan_files()
                elif file_info[1] == 'rar':
                    rom_file = RAR( file_info[0], database )
                    rom_file.scan_files()

                if rom_file.is_valid():
                    rom_file.add_to_db()
            except zipfile.BadZipfile as exc:
                print "Failed to process zip archive %s: %s" % ( file_info[0],
                        exc )

class NDS:
    ''' Reads and(maybe) writes the contents of .nds files '''
    def __init__( self, file_path, database = None, in_archive = None ):
        self.file_path = os.path.abspath( file_path )
        self.database  = database
        self.rom       = {}
        self.hardware  = {}

        if in_archive:
            self.real_path = '%s:%s' % ( in_archive,
                    os.path.basename( file_path ) )
        else:
            self.real_path = self.file_path


        self.rom_info = None

        self.parse_file()

    def is_valid( self ):
        '''Checks validity of rom'''
        valid = 1
        if self.hardware['capacity'] > 4096:
            valid = 0
        return valid

    def parse_file( self ):
        '''Read data from file'''
        try:
            file_handler = open( self.file_path, 'rb' )

            file_handler.seek( 0 )
            self.rom['title'] = byte_to_string( file_handler.read( 12 ) )
            self.rom['code']  = byte_to_string( file_handler.read( 4 ) )
            self.rom['maker'] = byte_to_string( file_handler.read( 2 ) )

            self.hardware['unit_code']  = byte_to_int( file_handler.read( 1 ) )
            self.hardware['encryption'] = byte_to_int( file_handler.read( 1 ) )
            self.hardware['capacity']   = capsize(
                byte_to_int( file_handler.read( 2 ) )
            )

            file_handler.seek( 0 )
            self.rom['crc32'] = binascii.crc32( file_handler.read() ) & \
                    0xFFFFFFFF
            self.rom['size']  = os.path.getsize( self.file_path )

            file_handler.close()
        except IOError as exc:
            print 'Failed to read file %s: %s' % ( self.file_path, exc )

    def add_to_db( self ):
        '''Add current nds file to database'''
        try:
            self.database.add_local( self.db_data() )
        except OperationalError as exc:
            print "Failed to add %s: %s" % ( self.rom_info, exc )

        return 1

    def query_db( self ):
        '''Get info about nds file from database'''
        db_releaseid = None
        # TODO: refactor this godawful puppy
        if not self.rom_info:
            db_releaseid = self.database.search_known_crc( self.rom['crc32'] )
            if not db_releaseid:
                ( release_number, rom_name, location ) = parse_filename(
                        self.file_path )
                r_releaseid      = self.database.search_known_relnum(
                        release_number )
                n_releaseid_list = self.database.search_known_name( rom_name,
                        location )
                if r_releaseid in n_releaseid_list:
                    db_releaseid = r_releaseid
                else:
                    if r_releaseid and self.confirm_file( r_releaseid ):
                        db_releaseid = r_releaseid
                    else:
                        if n_releaseid_list:
                            if len( n_releaseid_list ) == 1 and \
                                    self.confirm_file( n_releaseid_list[0] ):
                                db_releaseid = n_releaseid_list[0]
                            else:
                                answer = self.confirm_file( n_releaseid_list )
                                if answer != None:
                                    db_releaseid = n_releaseid_list[answer]
                        else:
                            print "Wasn't able to automatically identify %s" % (
                                    self.real_path )
                            if ui.question_yn(
                                "Want to manually search by name?" ):
                                print "Enter name: ",
                                search_name = raw_input().lower()
                                id_list = self.database.search_known_name(
                                        search_name )
                                if len( id_list ) == 1 and \
                                        self.confirm_file( id_list[0] ):
                                    db_releaseid = id_list[0]
                                else:
                                    answer = self.confirm_file( id_list )
                                    if answer != None:
                                        db_releaseid = id_list[answer]

        if db_releaseid:
            self.rom_info = self.database.rom_info( db_releaseid )
            self.rom_info.set_file_info( ( self.real_path, self.rom['size'],
                self.rom['crc32'] ) )
        else:
            self.rom_info = rom.Rom( file_data = ( self.real_path,
                self.rom['size'], self.rom['crc32'] ) )

            print "Wasn't able to identify %s" % ( self.real_path )
            print
        return 1

    def confirm_file( self, db_releaseid ):
        '''Confirm that file was detected right'''
        result = 0
        if type( db_releaseid ) == int:
            rom_obj = self.database.rom_info( db_releaseid )
            print "File '%s' was identified as %s" % (
                    os.path.basename( self.file_path ),
                    rom_obj
            )
            result = ui.question_yn( "Is this correct?" )
        elif type( db_releaseid ) == list:
            print "File '%s' can be one of the following:" % ( 
                    os.path.basename( self.file_path ) )
            index = 0
            for release_id in db_releaseid:
                rom_obj = self.database.rom_info( release_id )
                print " %d. %s" % ( index, rom_obj )
                index += 1
            result = ui.list_question( "Which one?",
                    range(index) + [None] )
        print

        return result

    def db_data( self ):
        '''Data accepted by db.add_local method'''
        self.query_db()
        return self.rom_info

class Archive:
    '''Generic archive handler'''
    def __init__( self, file_path, database = None ):
        self.file_path = os.path.abspath( file_path )
        self.database  = database
        self.tmp_dir   = '/tmp/'
        self.file_list = []

    def is_valid( self ):
        '''Check if archive contains any nds files'''
        result = 0
        if len( self.file_list ):
            result = 1
        return result

    def process_nds( self, nds_path ):
        '''Add nds file to database'''
        nds = NDS( nds_path, self.database, in_archive =
                self.file_path )
        if nds.is_valid():
            nds.add_to_db()
        return 1

    def extract( self, archive_file, path ):
        '''Extract specified file to path'''
        return "%s/%s" % ( path, archive_file )

    def add_to_db( self ):
        '''Add nds files from archive to database'''

        for nds_filename in self.file_list:
            nds_path = self.extract( nds_filename, self.tmp_dir )
            self.process_nds( nds_path )
            os.unlink( nds_path )

        return 1

class ZIP( Archive ):
    '''Zip archive handler'''
    def scan_files( self, ext = 'nds' ):
        '''Scan archive'''
        archive = zipfile.ZipFile( self.file_path, 'r' )
        for compressed in archive.namelist():
            if re.search( "\.%s$" % ext, compressed, flags = re.IGNORECASE ):
                self.file_list.append( compressed )
        archive.close()

        return 1

    def extract( self, archive_file, path ):
        '''Extract specified file to path'''
        archive = zipfile.ZipFile( self.file_path, 'r' )
        archive.extract( archive_file, path )
        archive.close()
        return "%s/%s" % ( path, archive_file )

class ZIP7( Archive ):
    '''7zip archive handler'''
    def scan_files( self, ext = 'nds' ):
        '''Scan archive'''
        list_archive = subprocess.Popen( [ '7z', 'l', self.file_path ],
                stdout = subprocess.PIPE, stderr = subprocess.PIPE )

        list_started   = 0
        filename_start = 0
        for line in list_archive.stdout.readlines():
            line = line.rstrip()
            if re.match( '-----', line ):
                list_started ^= 1
                filename_start = len( line.split( '  ' )[0] ) + 2
            elif list_started:
                filename = line[filename_start:]
                if re.search( "\.%s$" % ext, filename, flags = re.IGNORECASE ):
                    self.file_list.append( filename )
        list_archive.wait()

        return 1

    def extract( self, archive_file, path ):
        '''Extract specified file to path'''
        decompress = subprocess.Popen( [ '7z', 'e', '-y', '-o%s' % path,
            self.file_path, archive_file ], stdout = subprocess.PIPE,
            stderr = subprocess.PIPE )
        decompress.wait()
        return "%s/%s" % ( path, archive_file )

class RAR( Archive ):
    '''Rar archive handler'''
    def scan_files( self, ext = 'nds' ):
        '''Scan archive'''
        list_archive = subprocess.Popen( [ 'unrar', 'lb', self.file_path ],
                stdout = subprocess.PIPE, stderr = subprocess.PIPE )

        for filename in list_archive.stdout.readlines():
            filename = filename.rstrip()
            if re.search( "\.%s$" % ext, filename, flags = re.IGNORECASE ):
                self.file_list.append( filename )
        list_archive.wait()

        return 1

    def extract( self, archive_file, path ):
        '''Extract specified file to path'''
        decompress = subprocess.Popen( [ 'unrar', 'x', '-y', self.file_path, 
            archive_file, path ], stdout = subprocess.PIPE,
            stderr = subprocess.PIPE )
        decompress.wait()
        return "%s/%s" % ( path, archive_file )
