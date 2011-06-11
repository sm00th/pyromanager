'''File operations'''
import os, re
import struct, binascii
import pyNDSrom.db
from pyNDSrom.cfg import __config__ as config

def extension( file_name ):
    '''Returns the extension of specified file'''
    result = ''
    match  = re.match( r".*\.([^.]+)$", file_name )
    if match:
        result = match.group( 1 ).lower()

    return result

def search( path ):
    '''Returns list of acceptable files'''
    result = []
    path     = os.path.abspath( path )
    for file_name in os.listdir( path ):
        file_path = '%s/%s' % ( path, file_name )
        if os.path.isdir( file_path ):
            result += search( file_path )
        else:
            ext = extension( file_path )
            if ext in config['extensions']:
                result.append( ( file_path, ext ) )
    return result

def scan( path ):
    '''Scan path for roms'''
    database = pyNDSrom.db.SQLdb( "%s/%s" % ( config['confDir'],
        config['dbFile'] ) )
    for file_info in search( path ):
        if file_info[1] == 'nds':
            nds = NDS( file_info[0], database )
            if nds.is_valid:
                nds.add_to_db()

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
            location = pyNDSrom.db.encode_location( tag[1] )

    filename = strip_name( filename )

    return [ release_number, filename, location ]

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

class NDS:
    ''' Reads and(maybe) writes the contents of .nds files '''
    def __init__( self, file_path, database = None ):
        self.file_path = os.path.abspath( file_path )
        self.database  = database
        self.rom       = {}
        self.hardware  = {}

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
        except IOError:
            raise Exception( 'Failed to read file' )

    def add_to_db( self ):
        '''Add current nds file to database'''
        if self.database:
            self.database.add_local( self.db_data() )

        return 1

    def query_db( self ):
        '''Get info about nds file from database'''
        db_releaseid = None
        if not self.rom_info:
            db_releaseid = self.database.search_crc( self.rom['crc32'] )
            if not db_releaseid:
                ( release_number, rom_name, location ) = parse_filename(
                        self.file_path )
                r_releaseid      = self.database.search_relnum( release_number )
                n_releaseid_list = self.database.search_name( rom_name,
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
                                if answer:
                                    db_releaseid = n_releaseid_list[answer]

        if db_releaseid:
            self.rom_info = self.database.rom_info( db_releaseid )
            self.rom_info.set_file_info( ( self.file_path, self.rom['size'] ) )
        else:
            self.rom_info = pyNDSrom.rom.Rom( file_data = ( self.file_path,
                self.rom['size'] ) )
            print "Wasn't able to identify %s" % ( self.file_path )
        return 1

    def confirm_file( self, db_releaseid ):
        '''Confirm that file was detected right'''
        result = 0
        if type( db_releaseid ) == int:
            rom = self.database.rom_info( db_releaseid )
            print "File '%s' was identified as %s" % (
                    os.path.basename( self.file_path ),
                    rom,
            )
            result = pyNDSrom.ui.question_yn( "Is this correct?" )
        elif type( db_releaseid ) == list:
            print "File '%s' can be one of the following:" % ( 
                    os.path.basename( self.file_path ) )
            index = 0
            for release_id in db_releaseid:
                rom = self.database.rom_info( release_id )
                print " %d. %s" % ( index, rom )
                index += 1
            result = pyNDSrom.ui.list_question( "Which one?",
                    range(index) + [None] )

        return result

    def db_data( self ):
        '''Data accepted by db.add_local method'''
        self.query_db()
        return self.rom_info


#elif re.search( "\.zip$", fullPath, flags = re.IGNORECASE ):
    #try:
        #zipFile = zipfile.ZipFile( fullPath, "r" )
        #for archiveFile in zipFile.namelist():
            #if re.search( "\.nds$", archiveFile, flags = re.IGNORECASE ):
                # TODO: maybe we can use zipfile.read instead of actually 
                # unzipping stuff
                # NB: hardcoding /tmp/ is probably an awfull idea
                #zipFile.extract( archiveFile, '/tmp/' )
                #gameInfo = self.processNDSFile( '/tmp/' + archiveFile,
                    #interactive )

                #if gameInfo != 0:
                    #self.db.addLocalRom( os.path.abspath( fullPath ) + ":" + \
                            #archiveFile, gameInfo )
                #os.unlink( '/tmp/' + archiveFile )
        #zipFile.close()
    #except Exception as e:
        #print "Failed parsing zip-archive %s: %s" % ( fullPath, e )
