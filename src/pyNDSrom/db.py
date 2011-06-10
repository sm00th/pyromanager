'''Database manipulation module'''
import sqlite3
from xml.dom import minidom
import re
from cfg import __config__ as config

def encode_location( name ):
    '''Translates location name to int'''
    for ( location_id, aliases ) in config['location'].iteritems():
        if name.lower() in [ x.lower() for x in aliases ]:
            return location_id

    return None

def decode_location( location_id, return_type=1 ):
    '''Translates location id to it's name'''
    result = 'Unknown: %d' % location_id
    if return_type not in range(3):
        return_type = 1
    try:
        result = config['location'][location_id][return_type]
    except KeyError:
        pass

    return result

def strip_name( name ):
    '''Strip unnecessary information'''
    name = re.sub( r"(\(|\[)[^\(\)\[\]]*(\)|\])" , ''  , name )
    name = re.sub( r"the"                        , ''  , name )
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
            location = encode_location( tag[1] )

    filename = strip_name( filename )

    return [ release_number, filename, location ]

def node_text( node_list ):
    '''Extract text from node'''
    text = []
    for node in node_list:
        if node.nodeType == node.TEXT_NODE:
            text.append( node.data )
    return ''.join( text )

class SQLdb():
    '''Sqlite3 db interface'''
    def __init__( self, db_file ):
        # TODO: check if db_file specified and read from config?
        self.database = sqlite3.connect( db_file )

    def __del__( self ):
        self.database.close()

    def _create_tables( self ):
        '''Creates tables if they dont exist'''
        cursor = self.database.cursor()
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS known_roms ' + \
            '(release_id INTEGER PRIMARY KEY,' + \
            'name TEXT,' + \
            'crc32 NUMERIC,' + \
            'publisher TEXT,' + \
            'released_by TEXT,' + \
            'location NUMERIC,' + \
            'normalized_name TEXT);'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS local_roms ' + \
            '(id INTEGER PRIMARY KEY,' +\
            'release_id TEXT,' + \
            'path_to_file TEXT,' + \
            'normalized_name TEXT,' + \
            'size NUMERIC,' + \
            'UNIQUE( path_to_file ) ON CONFLICT REPLACE);'
        )
        self.database.commit()
        cursor.close()

    def import_known( self, provider ):
        '''Imports known roms from provider'''
        self._create_tables()

        # TODO: exception handling
        cursor = self.database.cursor()
        for data in provider.rom_list:
            normalized_name = strip_name( data[1] )
            cursor.execute(
                'INSERT OR REPLACE INTO known_roms VALUES(?,?,?,?,?,?,?)',
                data + ( normalized_name.lower(), )
            )
        self.database.commit()
        cursor.close()
        return 1

    def search_crc( self, crc32 ):
        '''Search known roms by crc32 value'''
        release_number = None
        cursor = self.database.cursor()
        returned = cursor.execute(
            'SELECT release_id FROM known_roms WHERE crc32=?',
            ( crc32, )
        ).fetchone()
        if returned:
            release_number = returned[0]
        cursor.close()

        return release_number

    def search_relnum( self, release_id ):
        '''Search known roms by release number'''
        release_number = None
        cursor = self.database.cursor()
        returned = cursor.execute(
            'SELECT release_id ' + \
            'FROM known_roms ' + \
            'WHERE release_id=?', 
            ( release_id, ) 
        ).fetchone()
        if returned:
            release_number = returned[0]
        cursor.close()

        return release_number

    def search_name( self, name, location=None ):
        '''Search known roms by name'''
        result = []

        returned     = None
        cursor     = self.database.cursor()
        normalized_name = '%' + re.sub( r"\s", '%', name ) + '%'
        if location != None:
            returned = cursor.execute(
                'SELECT release_id ' + \
                'FROM known_roms ' + \
                'WHERE normalized_name LIKE ? and location=?',
                ( normalized_name, location ) 
            ).fetchall()
        else:
            returned = cursor.execute(
                'SELECT release_id ' + \
                'FROM known_roms ' + \
                'WHERE normalized_name LIKE ?', 
                ( normalized_name, ) 
            ).fetchall()
        if returned:
            result = [ x[0] for x in returned ]
        cursor.close()

        return result

    def rom_info( self, release_number ):
        '''Returns rom info for rom specified by release number'''
        rom_data = None
        cursor = self.database.cursor()
        returned = cursor.execute(
            'SELECT release_id,name,publisher,released_by,location ' + \
            'FROM known_roms WHERE release_id=?',
            ( release_number, )
        ).fetchone()
        if returned:
            rom_data = returned
        cursor.close()

        return rom_data

    def add_local( self, path, release_number ):
        '''Add local rom to db'''
        normalized_name = parse_filename( path )[1]
        cursor = self.database.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO local_roms ' + \
            '( release_id, path_to_file, normalized_name ) ' + \
            'values ( ?, ?, ? )',
            ( release_number, path, normalized_name )
        )
        self.database.commit()

class AdvansceneXML():
    '''Advanscene xml parser'''
    def __init__( self, path ):
        self.path     = path
        self.rom_list = []

        self.parse()

    def parse( self ):
        '''Parse specified xml'''
        try:
            xml = minidom.parse( self.path )
            for node in xml.getElementsByTagName( 'game' ):
                self.rom_list.append( self.parse_node( node ) )
        except IOError:
            raise Exception( 'Can not open or parse file %s' % self.path )

    def parse_node( self, node ):
        '''Parse node'''
        title          = node_text( node.getElementsByTagName( 'title' )[0].childNodes )
        publisher      = node_text( node.getElementsByTagName( 'publisher' )[0].childNodes )
        released_by    = node_text( node.getElementsByTagName( 'sourceRom' )[0].childNodes )
        location       = node_text( node.getElementsByTagName( 'location' )[0].childNodes )
        release_number = int( node_text( node.getElementsByTagName( 'releaseNumber' )[0].childNodes ) )
        crc32          = self.get_crc( node )
        return ( release_number, title, crc32, publisher, released_by, location )

    def get_crc( self, node ):
        '''Returns crc from rom node'''
        for crc in node.getElementsByTagName( 'romCRC' ):
            if crc.getAttribute( 'extension' ) != '.nds':
                continue
            else:
                return int( node_text( crc.childNodes ), 16 )
        return None
