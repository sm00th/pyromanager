'''Rom info'''
import os, re, shutil
import os, re, zipfile, subprocess
import struct, binascii
import cfg

class RomInfo:
    '''Rom info'''
    def __init__( self, database, release_id = None ):
        self.database = database

    def __str__( self ):
        pass

class FileInfo:
    '''File info'''
    def __init__( self, path, database, config ):
        self.database  = database
        self.config    = config
        self.path      = path
        self.nds       = None

    def init( self ):
        nds = None
        if self.is_archived():
            ( archive_path, nds_name ) = self.split_path()
            archive = create_archive( archive_path, self.config )
            nds = archive.get_nds( nds_name )
        else:
            nds = Nds( self.path )
            nds.parse()

        self.nds = nds

    def split_path( self ):
        archive_path = self.path
        file_path    = None
        try:
            ( archive_path, file_path ) = self.path.split( ':' )
        except ValueError:
            pass
        return ( archive_path, file_path )

    def is_archived( self ):
        result = 0
        if re.search( ':', self.path ):
            result = 1
        return result

    def query_db( self ):
        if not self.nds:
            self.init()

        relid = self.database.search_known_crc( self.info['crc'] )

    @property
    def size_mb( self ):
        '''Returns size in MB'''
        result = 'Unknown'
        if self.nds.rom['size']:
            result = "%.2fM" % ( self.nds.rom['size'] / 1048576.0 )
        return result

    def __str__( self ):
        pass

class Rom:
    '''internal representation of roms'''

    def __init__( self, database, config, rom_data = None, file_data = None ):
        self.database  = database
        self.config    = config
        self.rom_info  = rom_data
        self.file_info = file_data

    def is_in_db( self ):
        '''Check if file is present in local table'''
        return 0

    def is_initialized( self ):
        '''Checks if there is any information in this object'''
        result = 0
        if self.file_info or self.rom_info:
            result = 1
        return result

    @property
    def normalized_name( self ):
        '''Normalized name property'''
        norm_name = None
        if self.rom_info['normalized_name']:
            norm_name = self.rom_info['normalized_name']
        elif self.file_info['path']:
            norm_name = parse_filename( self.file_info['path'] )[1]
        return norm_name

    def local_data( self ):
        '''Returns dataset for db.add_local method'''
        dataset = ( self.rom_info['release_number'], self.file_info['path'],
                self.normalized_name, self.file_info['size'],
                self.file_info['crc32'] )
        return dataset

    def remove( self ):
        '''Remove file from disk and local_roms table'''
        path = re.sub( r":.*$", '', self.file_info['path'] )
        try:
            os.unlink( path )
            self.database.remove_local( path )
        except OSError as exc:
            print "Failed to remove file: %s" % ( exc )

    def filename( self ):
        '''Formatted filename'''
        # TODO: configurable filename format
        if self.rom_info['release_number'] or self.rom_info['name']:
            name = "%04d - %s (%s).nds" % (
                int( self.rom_info['release_number'] ), self.rom_info['name'],
                    self.rom_info['region'] )
        else:
            archive_file = self.archive_path()[1]
            if archive_file:
                name = os.path.basename( archive_file )
            else:
                name = os.path.basename( self.file_info['path'] )

        return name

    def upload( self, path ):
        '''Copy rom to flashcart'''
        ( main_path, archive_file ) = self.archive_path()
        if not archive_file:
            shutil.copy( main_path, '%s/%s' % ( path, self.filename() ) )
        else:
            ext  = extension( main_path )
            archive = create_archive( main_path )
            archive.extract( archive_file, path )
            os.rename( '%s/%s' % ( path, archive_file ),
                    '%s/%s' % ( path, self.filename() ) )

    def __str__( self ):
        # TODO: fix formatting somehow
        rom_string = ''
        if self.rom_info['release_number'] or self.rom_info['name']:
            rom_string = "%4s - %s (%s) [%s]" % (
                self.rom_info['release_number'], self.rom_info['name'],
                    self.rom_info['region'], self.rom_info['released_by'] )
        else:
            rom_string = '%s( %s )' % ( self.normalized_name,
                    self.file_info['path'] )
        if self.file_info['size']:
            rom_string += ' Size: %s' % self.size_mb()
        if self.file_info['path'] and re.search( ':', self.file_info['path'] ):
            rom_string += ' [Archived]'
        return rom_string

class Nds:
    ''' Reads the contents of .nds files '''
    def __init__( self, file_path ):
        self.file_path = os.path.abspath( file_path )
        self.rom       = {}
        self.hardware  = {}

    def is_valid( self ):
        '''Checks validity of rom'''
        valid = 1
        if self.hardware['capacity'] > 4096:
            valid = 0
        return valid

    def parse( self ):
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

class Archive:
    '''Generic archive handler'''
    def __init__( self, path, config ):
        self.path      = os.path.abspath( path )
        self.config    = config
        self.file_list = []

    def is_valid( self ):
        '''Check if archive contains any nds files'''
        result = 0
        if len( self.file_list ):
            result = 1
        return result

    def get_nds( self, nds_name ):
        '''Get parsed nds object from archive'''
        self.extract( nds_name, self.config.tmp_dir )
        tmp_file = '%s/%s' % ( self.config.tmp_dir, nds_name )
        nds = Nds( tmp_file )
        nds.parse()
        os.unlink( tmp_file )
        return nds

class Zip( Archive ):
    '''Zip archive handler'''
    def scan_files( self, ext = 'nds' ):
        '''Scan archive'''
        archive = zipfile.ZipFile( self.path, 'r' )
        for compressed in archive.namelist():
            if re.search( "\.%s$" % ext, compressed, flags = re.IGNORECASE ):
                self.file_list.append( compressed )
        archive.close()

    def extract( self, archive_file, path ):
        '''Extract specified file to path'''
        archive = zipfile.ZipFile( self.path, 'r' )
        archive.extract( archive_file, path )
        archive.close()
        return "%s/%s" % ( path, archive_file )

class Zip7( Archive ):
    '''7zip archive handler'''
    def scan_files( self, ext = 'nds' ):
        '''Scan archive'''
        list_archive = subprocess.Popen( [ '7z', 'l', self.path ],
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
            self.path, archive_file ], stdout = subprocess.PIPE,
            stderr = subprocess.PIPE )
        decompress.wait()
        return "%s/%s" % ( path, archive_file )

class Rar( Archive ):
    '''Rar archive handler'''
    def scan_files( self, ext = 'nds' ):
        '''Scan archive'''
        list_archive = subprocess.Popen( [ 'unrar', 'lb', self.path ],
                stdout = subprocess.PIPE, stderr = subprocess.PIPE )

        for filename in list_archive.stdout.readlines():
            filename = filename.rstrip()
            if re.search( "\.%s$" % ext, filename, flags = re.IGNORECASE ):
                self.file_list.append( filename )
        list_archive.wait()

        return 1

    def extract( self, archive_file, path ):
        '''Extract specified file to path'''
        decompress = subprocess.Popen( [ 'unrar', 'x', '-y', self.path, 
            archive_file, path ], stdout = subprocess.PIPE,
            stderr = subprocess.PIPE )
        decompress.wait()
        return "%s/%s" % ( path, archive_file )

def create_archive( path, config ):
    '''Create archive object based on path(extension)'''
    obj = None
    ext = extension( path )
    if ext == 'zip':
        obj = Zip( path, config )
    if ext == '7z':
        obj = Zip7( path, config )
    if ext == 'rar':
        obj = Rar( path, config )
    return obj

def strip_name( name ):
    '''Strip unnecessary information'''
    name = re.sub( r"(\(|\[)[^\(\)\[\]]*(\)|\])" , ''  , name )
    name = re.sub( r"(^|\s)(the|and|a|\&)(\s|$)" , ' ' , name )
    name = re.sub( r"[^\w\d\s]"                  , ''  , name )
    name = re.sub( r"\s+"                        , ' ' , name )
    name = name.strip()

    return name

def parse_filename( filename ):
    '''Parse rom name'''
    config = cfg.Config()
    config.read_config()
    release_number = None

    filename = filename.lower()
    filename = re.sub( r"^.*(/|:)" , ''  , filename )
    filename = re.sub( "\.[^.]+$"  , ''  , filename )
    filename = re.sub( "_"         , ' ' , filename )

    match = re.match(
        r"((\[|\()?(\d+)(\]|\))|(\d+)\s*-\s*)\s*(.*)",
        filename
    )

    if match:
        if match.group( 3 ):
            release_number = int( match.group( 3 ) )
            filename       = match.group( 6 )
        elif match.group( 5 ):
            release_number = int( match.group( 5 ) )
            filename       = match.group( 6 )

    location = None
    for tag in re.findall( r"(\(|\[)(\w+)(\)|\])", filename ):
        if not location:
            location = config.region_code( tag[1] )

    filename = strip_name( filename )

    return ( release_number, filename, location )

def extension( file_name ):
    '''Returns the extension of specified file'''
    result = ''
    match  = re.match( r".*\.([^.]+)$", file_name )
    if match:
        result = match.group( 1 ).lower()

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

# FIXME: make that a property of Nds
def capsize( cap ):
    '''Returns capacity size of original cartridge'''
    return pow( 2, 20 + cap ) / 8388608
