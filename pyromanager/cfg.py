'''Provides configuration for pyromanager'''
import os
import subprocess
import ConfigParser

DEFAULT_RC = os.path.expanduser( "~/.pyromgr.rc" )
CONFIGURABLE_PATHS = [ 'db_file', 'flashcart', 'tmp_dir' ]
LOCATIONS = {
    0  : ( 'Europe'      , 'EUR'   , 'E' ),
    1  : ( 'USA'         , 'USA'   , 'U' ),
    2  : ( 'Germany'     , 'GER'   , 'G' ),
    4  : ( 'Spain'       , 'SPA'   , 'S' ),
    5  : ( 'France'      , 'FRA'   , 'F' ),
    6  : ( 'Italy'       , 'ITA'   , 'I' ),
    7  : ( 'Japan'       , 'JPN'   , 'J' ),
    8  : ( 'Netherlands' , 'DUTCH' , 'N' ),
    19 : ( 'Australia'   , 'AUS'   , 'A' ),
    22 : ( 'Korea'       , 'KOR'   , 'K' ),
}

def region_code( name ):
    '''Translates region name to it's code (int)'''
    for ( location_id, aliases ) in LOCATIONS.iteritems():
        if name.lower() in [ x.lower() for x in aliases ]:
            return location_id
    return None

def region_name( location_id, return_type=1 ):
    '''Translates region code to it's name(str)'''
    if location_id:
        result = 'Unknown: %d' % location_id
    else:
        result = 'Unknown'
    if return_type not in range(3):
        return_type = 1
    try:
        result = LOCATIONS[location_id][return_type]
    except KeyError:
        pass

    return result

def is_bin_available( binfile ):
    '''Determine if binary is somewhere in $PATH'''
    exists = True
    try:
        chk = subprocess.Popen( [ binfile ], stdout = subprocess.PIPE,
                stderr = subprocess.PIPE )
        if chk.wait() == 127:
            exists = False
    except OSError:
        exists = False

    return exists

class Config:
    '''Contais all the settings for pyromanager'''
    def __init__( self, rc_file = DEFAULT_RC ):
        self.rc_file = os.path.expanduser( rc_file )
        self._paths  = {
                'assets_dir' : os.path.expanduser( "~/.pyromgr" ),
                'saves_dir'  : 'saves',
                'db_file'    : 'pyromgr.db',
                'tmp_dir'    : '/tmp',
                'flashcart'  : '/mnt/ds',
        }
        self._saves = {
                'extension' : 'sav'
        }
        self._rom = {
                'trim' : 'true'
        }
        self._extensions = None

    def write_config( self ):
        '''Save changes to rc-file'''
        parser = ConfigParser.ConfigParser()

        parser.add_section( 'paths' )
        for file_type in CONFIGURABLE_PATHS:
            parser.set( 'paths', file_type, self._paths[file_type] )

        parser.add_section( 'saves' )
        for ( save_opt, save_val ) in self._saves.iteritems():
            parser.set( 'saves', save_opt, save_val )

        parser.add_section( 'rom' )
        for ( rom_opt, rom_val ) in self._rom.iteritems():
            parser.set( 'rom', rom_opt, rom_val )

        parser.write( file( self.rc_file, 'w' ) )

    def read_config( self ):
        '''Read and parse rc-file'''
        parser = ConfigParser.ConfigParser()
        if os.path.isfile( self.rc_file ):
            parser.read( self.rc_file )
        elif self.rc_file == DEFAULT_RC:
            self.write_config()
            return

        if parser.has_section( 'paths' ):
            for file_type in CONFIGURABLE_PATHS:
                if parser.has_option( 'paths', file_type ):
                    self._paths[file_type] = parser.get( 'paths', file_type )
        if parser.has_section( 'saves' ):
            for save_opt in self._saves.keys():
                self._saves[save_opt] = parser.get( 'saves', save_opt )
        if parser.has_section( 'rom' ):
            for rom_opt in self._rom.keys():
                self._rom[rom_opt] = parser.get( 'rom', rom_opt )

    @property
    def assets_dir( self ):
        '''Path to directory containing additional files'''
        return self._paths['assets_dir']

    @property
    def tmp_dir( self ):
        '''Temporary dir, used to temporary extract archives into it to parse
        nds files'''
        return self._paths['tmp_dir']

    @property
    def flashcart( self ):
        '''Flashcart mountpoint'''
        return self._paths['flashcart']

    @property
    def db_file( self ):
        '''Full path to sqlite database file'''
        return '%s/%s' % ( self._paths['assets_dir'], self._paths['db_file'] )

    @property
    def saves_dir( self ):
        '''Full path to saves directory'''
        return '%s/%s' % ( self._paths['assets_dir'], self._paths['saves_dir'] )

    @property
    def save_ext( self ):
        '''Savefile extension'''
        return self._saves['extension']

    @property
    def trim( self ):
        '''Savefile extension'''
        return self._rom['trim']

    @property
    def extensions( self ):
        '''List of supported extensions'''
        if not self._extensions:
            self._extensions = [ 'nds', 'zip' ]
            if is_bin_available( '7z' ):
                self._extensions.append( '7z' )
            if is_bin_available( 'rar' ):
                self._extensions.append( 'rar' )

        return self._extensions
