'''Database manipulation module'''
import re
import sqlite3
import pyNDSrom.rom
import pyNDSrom.file
from xml.dom import minidom
from pyNDSrom.cfg import __config__ as config

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
            'crc32 NUMERIC,' + \
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
            cursor.execute(
                'INSERT OR REPLACE INTO known_roms VALUES(?,?,?,?,?,?,?)',
                data
            )
        self.database.commit()
        cursor.close()
        return 1

    def search_known_crc( self, crc32 ):
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

    def search_known_relnum( self, release_id ):
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

    def search_known_name( self, name, location=None ):
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

    def local_roms_name( self, name ):
        '''Search local roms by name'''
        result = []

        returned     = None
        cursor     = self.database.cursor()
        normalized_name = '%' + re.sub( r"\s", '%', name ) + '%'
        returned = cursor.execute(
            'SELECT release_id, path_to_file, size, crc32 ' + \
            'FROM local_roms ' + \
            'WHERE normalized_name LIKE ? ' + \
            'ORDER BY release_id',
            ( normalized_name, ) 
        ).fetchall()
        if returned:
            for ( release_id, path, size, crc32 ) in returned:
                rom = pyNDSrom.rom.Rom()
                if release_id:
                    rom = self.rom_info( release_id )
                rom.set_file_info( ( path, size, crc32 ) )
                result.append( rom )
        cursor.close()

        return result

# TODO: refactor those search functions
    def local_roms_crc32( self, crc32 ):
        '''Search local roms by crc32'''

        returned = None
        result   = []
        cursor   = self.database.cursor()
        returned = cursor.execute(
            'SELECT release_id, path_to_file, size ' + \
            'FROM local_roms ' + \
            'WHERE crc32=? ',
            ( crc32, ) 
        ).fetchall()
        if returned:
            for ( release_id, path, size ) in returned:
                rom = pyNDSrom.rom.Rom()
                if release_id:
                    rom = self.rom_info( release_id )
                rom.set_file_info( ( path, size, crc32 ) )
                result.append( rom )
        cursor.close()

        return result

    def remove_local( self, path ):
        cursor = self.database.cursor()
        cursor.execute( 'DELETE from local_roms where path_to_file=?', (path, ) )
        self.database.commit()
        cursor.close()
        return 1

    def rom_info( self, release_number ):
        '''Returns rom info for rom specified by release number'''
        rom_data = pyNDSrom.rom.Rom()
        cursor = self.database.cursor()
        returned = cursor.execute(
            'SELECT release_id, name, publisher, released_by, location, ' + \
            'normalized_name ' + \
            'FROM known_roms WHERE release_id=?',
            ( release_number, )
        ).fetchone()
        if returned:
            rom_data.set_rom_info( returned )
        cursor.close()

        return rom_data

    def add_local( self, rom_info ):
        '''Add local rom to db'''
        cursor = self.database.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO local_roms ' + \
            '( release_id, path_to_file, normalized_name, size, crc32 ) ' + \
            'values ( ?, ?, ?, ?, ? )',
            rom_info.local_data()
        )
        self.database.commit()
        return 1

    def find_dupes( self ):
        '''Search for duplicate roms'''
        result = []
        cursor = self.database.cursor()
        dupes = cursor.execute(
            'SELECT COUNT(*) as entries, crc32 FROM ' + \
            'local_roms GROUP BY crc32 HAVING entries > 1'
        ).fetchall()
        if dupes:
            result = dupes
        cursor.close()
        return result

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
        title = node_text( node.getElementsByTagName( 'title' )[0].childNodes )
        publisher = node_text(
                node.getElementsByTagName( 'publisher' )[0].childNodes )
        released_by = node_text(
                node.getElementsByTagName( 'sourceRom' )[0].childNodes )
        location = node_text(
                node.getElementsByTagName( 'location' )[0].childNodes )
        release_number = int( node_text(
                node.getElementsByTagName( 'releaseNumber' )[0].childNodes ) )
        crc32 = self.get_crc( node )
        normalized_name = pyNDSrom.file.strip_name( title.lower() )
        return ( release_number, title, crc32, publisher, released_by,
                location, normalized_name )

    def get_crc( self, node ):
        '''Returns crc from rom node'''
        for crc in node.getElementsByTagName( 'romCRC' ):
            if crc.getAttribute( 'extension' ) != '.nds':
                continue
            else:
                return int( node_text( crc.childNodes ), 16 )
        return None
