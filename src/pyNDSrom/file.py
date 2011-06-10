'''File operations'''
import os, re
import struct, binascii
from pyNDSrom.cfg import __config__ as config

def extension( file_name ):
    '''Returns the extension of specified file'''
    result = ''
    match  = re.match( r".*\.([^.]+)$", file_name )
    if match:
        result = match.group( 1 )

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
            if extension( file_path ) in config['extensions']:
                result.append( file_path )
    return result

def scan( path ):
    '''Scan path for roms'''
    for file_name in search( path ):
        print file_name

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
    def __init__( self, file_path ):
        self.file_path = file_path
        self.rom       = {}
        self.hardware  = {}

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
            nds = open( self.file_path, 'rb' )

            nds.seek( 0 )
            self.rom['title'] = byte_to_string( nds.read( 12 ) )
            self.rom['code']  = byte_to_string( nds.read( 4 ) )
            self.rom['maker'] = byte_to_string( nds.read( 2 ) )

            self.hardware['unit_code']  = byte_to_int( nds.read( 1 ) )
            self.hardware['encryption'] = byte_to_int( nds.read( 1 ) )
            self.hardware['capacity']   = capsize(
                byte_to_int( nds.read( 2 ) )
            )

            nds.seek( 0 )
            self.rom['crc32'] = binascii.crc32( nds.read() ) & 0xFFFFFFFF

            nds.close()
        except IOError:
            raise Exception( 'Failed to parse file' )
