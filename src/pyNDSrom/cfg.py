'''Configuration for pyNDSrom'''
import os
import subprocess
import ConfigParser

# TODO: actual config
__config__ = {
    'confDir'    : os.path.expanduser( "~/.pyROManager" ),
    'dbFile'     : 'pyro.db',
    'xmlDB'      : 'ADVANsCEne_NDS_S.xml',
    'flash_path' : '/home/sm00th/flash',
    'extensions' : [ 'nds', 'zip', '7z', 'rar' ],
    'location'   : {
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
    },
}

def check_bin( binfile ):
    '''Determine if binary is somewhere in $PATH'''
    exists = 1
    chk = subprocess.Popen( [ binfile ], stdout = subprocess.PIPE,
            stderr = subprocess.PIPE )
    if chk.wait() == 127:
        exists = 0

    return exists

class Config:
    '''Config class'''
    def __init__( self, rc_file = "~/.pyROManager.rc" ):
        self.rc_file = os.path.expanduser( rc_file )
        self._paths   = {
                'conf_dir'  : os.path.expanduser( "~/.pyROManager" ),
                'db_file'   : 'pyro.db',
                'xml_file'  : 'advanscene.xml',
                'flashcart' : '/mnt/ds',
        }
        self._locations = {
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
        self._extensions = None

    def write_config( self ):
        '''Dump current config to file'''
        parser = ConfigParser.ConfigParser()
        parser.add_section( 'paths' )
        for file_type in [ 'db_file', 'xml_file', 'flashcart' ]:
            parser.set( 'paths', file_type, self._paths[file_type] )
        parser.write( file( self.rc_file, 'w' ) )

    def read_config( self ):
        '''Read and parse rc_file'''
        parser = ConfigParser.ConfigParser()
        if os.path.isfile( self.rc_file ):
            parser.read( self.rc_file )
        else:
            self.write_config()

        if parser.has_option( 'paths', 'db_file' ):
            self._paths['db_file'] = parser.get( 'paths', 'db_file' )
        if parser.has_option( 'paths', 'xml_file' ):
            self._paths['xml_file'] = parser.get( 'paths', 'xml_file' )
        if parser.has_option( 'paths', 'flashcart' ):
            self._paths['flashcart'] = parser.get( 'paths', 'flashcart' )

    @property
    def flashcart( self ):
        '''Flashcart mountpoint'''
        return self._paths['flashcart']

    @property
    def db_file( self ):
        '''Full path to db file'''
        return '%s/%s' % ( self._paths['conf_dir'], self._paths['db_file'] )

    @property
    def xml_file( self ):
        '''Full path to advanscene xml file'''
        return '%s/%s' % ( self._paths['conf_dir'], self._paths['xml_file'] )

    @property
    def extensions( self ):
        '''List of allowed extensions'''
        if not self._extensions:
            self._extensions = [ 'nds', 'zip' ]
            if check_bin( '7z' ):
                self._extensions.append( '7z' )
            if check_bin( 'rar' ):
                self._extensions.append( 'rar' )

        return self._extensions

    def region_code( self, name ):
        '''Translates location name to int'''
        for ( location_id, aliases ) in self._locations.iteritems():
            if name.lower() in [ x.lower() for x in aliases ]:
                return location_id
        return None

    def region_name( self, location_id, return_type=1 ):
        '''Translates location id to it's name'''
        result = 'Unknown: %d' % location_id
        if return_type not in range(3):
            return_type = 1
        try:
            result = self._locations[location_id][return_type]
        except KeyError:
            pass

        return result
