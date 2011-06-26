'''Provides classes related to roms'''
import os, re, zipfile, subprocess, shutil
import struct, binascii, time
import cfg
import ui

class RomInfo:
    '''Rom information from database'''
    def __init__( self, release_id, database, config ):
        self.relid           = release_id
        self.database        = database
        self.config          = config
        self.name            = None
        self.publisher       = None
        self.released_by     = None
        self.region          = None
        self.normalized_name = None

        ( self.name, self.publisher, self.released_by, self.region,
                self.normalized_name ) = self.database.rom_info( self.relid
                        )[1:6]

    @property
    def filename( self ):
        '''Formatted filename'''
        return "%04d - %s (%s).nds" % (
                int( self.relid ), self.name, 
                self.config.region_name( self.region ) )

    def __str__( self ):
        return "%4s - %s (%s) [%s]" % ( self.relid, self.name,
                self.config.region_name( self.region ), self.released_by )

class FileInfo:
    '''Local file information'''
    def __init__( self, path, database, config, lid = None ):
        self.database  = database
        self.config    = config
        self.nds       = None
        self.name_info = None
        self.db_info   = None
        self.path      = None

        if path:
            self.path = path
        elif lid != None:
            ( release_id, path, size, crc ) = self.database.file_info( lid )
            self.path = path
            self.db_info = {
                    'relid' : release_id,
                    'size'  : size,
                    'crc'   : crc,
            }
            self._parse_name()

    def init( self ):
        '''Get nds object and prepare name_info'''
        nds = None
        if self.is_archived():
            ( archive_path, nds_name ) = self._split_path()
            archive = archive_obj( archive_path, self.config )
            nds = archive.get_nds( nds_name )
        else:
            nds = Nds( self.path )
            nds.parse()

        self.nds = nds
        self._parse_name()

    def _parse_name( self ):
        '''Parse filename'''
        ( relid, name, region ) = parse_filename( self.path )
        self.name_info = {
            'release_id'      : relid,
            'normalized_name' : name,
            'region'          : region,
        }

    def _split_path( self ):
        '''Split archive path'''
        archive_path = self.path
        file_path    = None
        try:
            ( archive_path, file_path ) = self.path.split( ':' )
        except ValueError:
            pass
        return ( archive_path, file_path )

    def is_archived( self ):
        '''Check if nds file is in archive'''
        if re.search( ':', self.path ):
            return True

    def is_initialized( self ):
        '''Check if object is properly initialized'''
        if self.nds or self.db_info:
            return True

    def _confirm_file( self, relid = None ):
        '''Confirm that file was detected right'''
        result = None
        if type( relid ) == int:
            rom_obj = RomInfo( relid, self.database, self.config )
            print "File '%s' was identified as %s" % (
                    os.path.basename( self.path ),
                    rom_obj
            )
            result = ui.question_yn( "Is this correct?" )
        elif type( relid ) == list:
            print "File '%s' can be one of the following:" % (
                    os.path.basename( self.path ) )
            index = 0
            for release_id in relid:
                rom_obj = RomInfo( release_id, self.database, self.config )
                print " %d. %s" % ( index, rom_obj )
                index += 1
            result = ui.list_question( "Which one?",
                    range(index) + [None] )
        print

        return result

    def _ask_name( self ):
        '''Ask user for rom name'''
        search_name = None
        print "Wasn't able to automatically identify %s" % ( self.path )
        if ui.question_yn( "Want to manually search by name?" ):
            print "Enter name: ",
            search_name = raw_input().lower()
        return search_name

    def _name_search( self, relid_list ):
        '''Search database by name'''
        relid = None
        if len( relid_list ) == 1 and self._confirm_file(
                relid_list[0] ):
            relid = relid_list[0]
        else:
            answer = self._confirm_file( relid_list )
            if answer != None:
                relid = relid_list[answer]
            else:
                search_name = self._ask_name()
                if search_name:
                    new_relid_list = self.database.search_name(
                            search_name, table = 'known' )
                    if new_relid_list:
                        relid = self._name_search( new_relid_list )
        return relid

    def is_valid( self ):
        '''Check if nds is a valid rom-file'''
        if not self.is_initialized():
            self.init()
        return self.nds.is_valid()

    @property
    def normalized_name( self ):
        '''Normalized filename'''
        if not self.is_initialized():
            self.init()
        return self.name_info['normalized_name']

    @property
    def size( self ):
        '''File size in bytes'''
        if not self.is_initialized():
            self.init()
        result = None
        if self.nds:
            result = self.nds.size
        elif self.db_info:
            result = self.db_info['size']
        return result

    @property
    def size_mb( self ):
        '''File size in megabytes'''
        if not self.is_initialized():
            self.init()
        result = 'Unknown'
        if self.nds:
            result = "%.2fM" % ( self.nds.size / 1048576.0 )
        elif self.db_info:
            result = "%.2fM" % ( self.db_info['size'] / 1048576.0 )
        return result

    @property
    def crc( self ):
        '''File crc'''
        if not self.is_initialized():
            self.init()
        result = None
        if self.nds:
            result = self.nds.crc
        elif self.db_info:
            result = self.db_info['crc']
        return result

    def get_rom_info( self ):
        '''Get rom info from database'''
        if not self.is_initialized():
            self.init()
        relid = None

        if self.db_info:
            relid = self.db_info['relid']
        else:
            try:
                relid = self.database.search_crc( self.crc, 'known' )[0]
            except TypeError:
                pass
            if not relid:
                relid_list = self.database.search_name(
                        self.name_info['normalized_name'],
                        self.name_info['region'], table = 'known' )
                if ( self.name_info['release_id'] in relid_list ) or (
                        self.name_info['release_id'] and self._confirm_file(
                            self.name_info['release_id'] ) ):
                    relid = self.name_info['release_id']
                elif relid_list:
                    relid = self._name_search( relid_list )
                else:
                    search_name = self._ask_name()
                    if search_name:
                        relid_list = self.database.search_name(
                                search_name, table = 'known' )
                        if relid_list:
                            relid = self._name_search( relid_list )
        return RomInfo( relid, self.database, self.config )

    def upload( self, path, filename = None ):
        '''Copy rom to flashcart'''
        if not filename:
            filename = re.sub( r"^.*(/|:)", '', self.path )

        if self.is_archived():
            ( archive_path, nds_name ) = self._split_path()
            archive = archive_obj( archive_path, self.config )
            archive.extract( nds_name, path )
            os.rename( '%s/%s' % ( path, nds_name ),
                    '%s/%s' % ( path, filename ) )
        else:
            shutil.copy( self.path, '%s/%s' % ( path, filename ) )

    def remove( self ):
        '''Delete file and remove from local table'''
        path = re.sub( r":.*$", '', self.path )
        os.unlink( path )
        self.database.remove_local( path )

    def __str__( self ):
        return '%s (%s)' % ( self.name_info['normalized_name'], self.path )

class Rom:
    '''internal representation of roms'''

    def __init__( self, path, database, config,
            rom_info = None, file_info = None ):
        self.database  = database
        self.config    = config
        self.rom_info  = rom_info
        self.file_info = file_info

        if not self.file_info:
            self.file_info = FileInfo( os.path.abspath( path ), database, config )

    def is_valid( self ):
        '''If rom is valid'''
        return self.file_info.is_valid()

    def is_in_db( self ):
        '''Check if file is present in local table'''
        return self.database.already_in_local( self.file_info.path, 1 )

    def is_initialized( self ):
        '''Checks if there is any information in this object'''
        if self.file_info.is_initialized() or self.rom_info:
            return True

    def add_to_db( self ):
        '''Add current rom file to database'''
        if not self.rom_info:
            self.rom_info  = self.file_info.get_rom_info()

        local_info = ( self.rom_info.relid, self.file_info.path,
                self.normalized_name, self.file_info.size, self.file_info.crc )
        self.database.add_local( local_info )
        self.database.save()

    @property
    def path( self ):
        '''Path to nds file'''
        return self.file_info.path

    @property
    def normalized_name( self ):
        '''Normalized name'''
        result = ''
        if self.rom_info:
            result = self.rom_info.normalized_name
        else:
            result = self.file_info.normalized_name
        return result

    def remove( self ):
        '''Remove file from disk and local table'''
        self.file_info.remove()

    def upload( self, path ):
        '''Copy rom to flashcart'''
        self.file_info.upload( path, self.rom_info.filename )

    def get_saves( self ):
        '''Check if rom has any backed up saves'''
        save_list = []
        if self.rom_info:
            relid   = self.rom_info.relid
            localid = self.database.search_local( 'id', 'path',
                    self.file_info.path )[0]

            remote_name = re.sub( 'nds', self.config.save_ext,
                    self.rom_info.filename, flags = re.IGNORECASE )
            mkdir( self.config.saves_dir )
            for savefile in os.listdir( self.config.saves_dir ):
                if not( os.path.isfile( '%s/%s' % ( self.config.saves_dir,
                    savefile ) ) and re.match( r"\d+_\d+_\d+.sav", savefile,
                        flags = re.IGNORECASE ) ):
                    continue
                ( s_relid, s_lid, s_mtime ) = map( int,  savefile[0:-4].split(
                    '_' ) )
                if s_relid == relid or s_lid == localid:
                    save_list.append( SaveFile( s_relid, s_lid, s_mtime,
                        remote_name, self.config ) )
        return save_list

    def __str__( self ):
        if not self.rom_info:
            self.rom_info  = self.file_info.get_rom_info()
        string = [ '%s' % self.rom_info ]
        if self.file_info:
            string.append( self.file_info.size_mb )
            if self.file_info.is_archived():
                string.append( '[Archive]' )

        return ' '.join( string )

class SaveFile:
    '''Rom savefile'''
    def __init__( self, relid, lid, mtime, filename, config ):
        self.relid       = int( relid )
        self.lid         = int( lid )
        self.mtime       = float( mtime )
        self.local_name  = '%s/%d_%d_%d.sav' % ( config.saves_dir, self.relid,
                self.lid, self.mtime )
        self.remote_name = filename

        mkdir( config.saves_dir )

    def stored( self ):
        '''Check if file is stored already'''
        if os.path.exists( self.local_name ):
            return True

    def copy_from( self, file_path ):
        '''Copy save from file'''
        shutil.copy( file_path, self.local_name )

    def upload( self, path ):
        '''Upload savefile to specified path'''
        shutil.copy( self.local_name, '%s/%s' % ( path, self.remote_name ) )

    def __str__( self ):
        return time.strftime( "%x %X", time.localtime( self.mtime ) )

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

    @property
    def crc( self ):
        '''CRC checksum of file'''
        return self.rom['crc32']

    @property
    def size( self ):
        '''Size of file'''
        return self.rom['size']

class Archive:
    '''Generic archive handler'''
    def __init__( self, path, config ):
        self.path      = os.path.abspath( path )
        self.config    = config
        self.file_list = []

    def is_valid( self ):
        '''Check if archive contains any nds files'''
        if len( self.file_list ):
            return True

    def extract( self, archive_file, path ):
        '''Extract specified file to path'''
        return "%s/%s" % ( path, archive_file )

    def full_paths( self ):
        '''Returns list of full paths'''
        result = []
        for filename in self.file_list:
            result.append( '%s:%s' % ( self.path, filename ) )
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

    def extract( self, archive_file, path ):
        '''Extract specified file to path'''
        decompress = subprocess.Popen( [ 'unrar', 'x', '-y', self.path, 
            archive_file, path ], stdout = subprocess.PIPE,
            stderr = subprocess.PIPE )
        decompress.wait()
        return "%s/%s" % ( path, archive_file )

def archive_obj( path, config ):
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

    region = None
    for tag in re.findall( r"(\(|\[)(\w+)(\)|\])", filename ):
        if not region:
            region = config.region_code( tag[1] )

    filename = strip_name( filename )

    return ( release_number, filename, region )

# FIXME: os.path.splitext
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
                    if ext == 'nds':
                        result.append( file_path )
                    else:
                        try:
                            archive = archive_obj( file_path, config )
                            archive.scan_files()
                            for arc_path in archive.full_paths():
                                result.append( arc_path )
                        except zipfile.BadZipfile as exc:
                            print "Failed to scan archive %s: %s" % (
                                    file_path, exc )
    except OSError as exc:
        print "Can't scan path %s: %s" % ( path, exc )
    return result

def import_path( path, opts, database, config ):
    '''Import roms from path'''
    for rom_path in search( path, config ):
        rom = Rom( rom_path, database, config )
        if ( ( opts and opts.full_rescan ) or not rom.is_in_db() ) and rom.is_valid():
            rom.add_to_db()

def get_save( path, save_ext = 'sav' ):
    '''Search for savefile of given rom'''
    ( save_path, nds_name ) = os.path.split( path )
    nds_name = os.path.splitext( nds_name )[0]
    for filename in os.listdir( save_path ):
        if os.path.isfile( '%s/%s' % ( save_path, filename ) ) and ( 
                nds_name in filename ):
            if( extension( filename ) == save_ext ):
                return '%s/%s' % ( save_path, filename )

def identify( path, database ):
    '''Get local id by path'''
    local_id = None
    relid = parse_filename( path )[0]
    if relid:
        id_list = database.search_local( 'id', 'release_id', relid )
        if id_list:
            local_id = id_list[0]
    else:
        id_list = database.search_local( 'id', 'size', os.path.getsize( path ) )
        if id_list and len( id_list ) == 1:
            local_id = id_list[0]
        else:
            file_handler = open( path, 'rb' )
            crc = binascii.crc32( file_handler.read() ) & 0xFFFFFFFF
            file_handler.close()
            id_list = database.search_local( 'id', 'crc', crc )
            if id_list:
                local_id = id_list[0]

    return local_id

def mkdir( path ):
    '''Create dir if not exists'''
    if not os.path.exists( path ):
        os.mkdir( path )
