'''Provides interfaces to databases'''
import re, os, time
import urllib2
import sqlite3
from rom import mkdir, strip_name, Zip
from xml.dom import minidom

class SQLdb():
    '''Interface for sqlite3 database'''
    def __init__( self, db_file = None ):
        mkdir( os.path.dirname( db_file ) )
        # TODO: check reeeeeeeeeeeally carefully if this is safe thing to do.
        self.database = sqlite3.connect( db_file, check_same_thread = False )

    def __del__( self ):
        self.database.close()

    def _create_tables( self ):
        '''Creates tables if they don't exist'''
        cursor = self.database.cursor()
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS known ' + \
            '(id INTEGER PRIMARY KEY,' + \
            'name TEXT,' + \
            'crc NUMERIC,' + \
            'publisher TEXT,' + \
            'released_by TEXT,' + \
            'region NUMERIC,' + \
            'search_name TEXT);'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS local ' + \
            '(id INTEGER PRIMARY KEY,' +\
            'release_id NUMERIC,' + \
            'path TEXT,' + \
            'search_name TEXT,' + \
            'size NUMERIC,' + \
            'crc NUMERIC,' + \
            'UNIQUE( path ) ON CONFLICT REPLACE);'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS db_info ' + \
            '(key TEXT PRIMARY KEY,' +\
            'val TEXT );'
        )
        cursor.close()
        self.save()

    def import_known( self, provider ):
        '''Imports roms given by provider'''
        self._create_tables()

        cursor = self.database.cursor()
        for data in provider:
            cursor.execute(
                'INSERT OR REPLACE INTO known VALUES(?,?,?,?,?,?,?)',
                data
            )
        self.updated()
        cursor.close()

    def updated( self ):
        '''Sets db_info.u_time to current time'''
        self._create_tables()

        cursor = self.database.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO db_info VALUES(?,?)',
            ( 'u_time', '%d' % ( time.time() ) )
        )
        cursor.close()

    @property
    def last_updated( self ):
        '''Returns time when database was last updated'''
        u_time = 0
        cursor = self.database.cursor()
        try:
            returned = cursor.execute(
                'SELECT val FROM db_info WHERE key = "u_time"',
            ).fetchone()
            if returned:
                u_time = int( returned[0] )
        except sqlite3.OperationalError:
            self._create_tables()

        cursor.close()
        return u_time

    def search_crc( self, crc, table = 'known' ):
        '''Search roms by crc, returns list'''
        id_list  = []
        cursor   = self.database.cursor()
        try:
            returned = cursor.execute(
                'SELECT id FROM %s WHERE crc=? ORDER BY id' % table,
                ( crc, )
            ).fetchall()
            if returned:
                id_list = [ x[0] for x in returned ]
        except sqlite3.OperationalError:
            self._create_tables()

        cursor.close()
        return id_list

    def search_name( self, name, region = None, table = 'known' ):
        '''Search roms by name [and regioncode], returns list'''
        result = []

        returned    = None
        cursor      = self.database.cursor()
        try:
            search_name = '%' + re.sub( r"\s", '%', name ) + '%'
            if region != None:
                returned = cursor.execute(
                    'SELECT id ' + \
                    'FROM %s ' % table + \
                    'WHERE search_name LIKE ? and region=? ORDER BY id',
                    ( search_name, region ) 
                ).fetchall()
            else:
                returned = cursor.execute(
                    'SELECT id ' + \
                    'FROM %s ' % table + \
                    'WHERE search_name LIKE ? ORDER BY id',
                    ( search_name, ) 
                ).fetchall()
            if returned:
                result = [ x[0] for x in returned ]
        except sqlite3.OperationalError:
            self._create_tables()

        cursor.close()
        return result

    def search_local( self, retval, column, search_val ):
        '''Search local table'''
        result  = []
        cursor  = self.database.cursor()
        try:
            id_list = cursor.execute(
                'SELECT %s FROM local WHERE %s=? ORDER BY id' % ( retval,
                    column ), ( search_val, ) ).fetchall()
            if id_list:
                result = [ local_id[0] for local_id in id_list ]
        except sqlite3.OperationalError:
            self._create_tables()

        cursor.close()
        return result

    def remove_local( self, path ):
        '''Remove rom from local table by given path'''
        cursor = self.database.cursor()
        try:
            cursor.execute( 'DELETE from local where path LIKE ?', (
                '%s%%' % path, ) )
        except sqlite3.OperationalError:
            self._create_tables()
        cursor.close()

    def file_info( self, lid ):
        '''Returns file information from local table by given local id'''
        cursor = self.database.cursor()
        result = ( None, None, None, None )
        try:
            returned = cursor.execute(
                'SELECT release_id, path, size, crc ' + \
                'FROM local WHERE id=?',
                ( lid, )
            ).fetchone()
            if returned:
                result = returned
        except sqlite3.OperationalError:
            self._create_tables()
        cursor.close()

        return result

    def rom_info( self, relid ):
        '''Returns rom information from known table by given release id'''
        cursor = self.database.cursor()
        result = ( None, None, None, None, None, None )
        try:
            returned = cursor.execute(
                'SELECT id, name, publisher, released_by, region, ' + \
                'search_name ' + \
                'FROM known WHERE id=?',
                ( relid, )
            ).fetchone()
            if returned:
                result = returned
        except sqlite3.OperationalError:
            self._create_tables()
        cursor.close()

        return result

    def add_local( self, local_info ):
        '''Adds rom to local table'''
        cursor = self.database.cursor()
        try:
            cursor.execute(
                'INSERT OR REPLACE INTO local ' + \
                '( release_id, path, search_name, size, crc ) ' + \
                'values ( ?, ?, ?, ?, ? )',
                local_info
            )
        except sqlite3.OperationalError:
            self._create_tables()
        cursor.close()

    def find_dupes( self ):
        '''Searches for duplicate roms'''
        result = []
        cursor = self.database.cursor()
        try:
            dupes = cursor.execute(
                'SELECT COUNT(*) as entries, crc FROM ' + \
                'local GROUP BY crc HAVING entries > 1'
            ).fetchall()
            if dupes:
                result = dupes
        except sqlite3.OperationalError:
            self._create_tables()
        cursor.close()
        return result

    def path_list( self ):
        '''Returns the list of all paths in local table'''
        result = []
        cursor = self.database.cursor()
        try:
            paths = cursor.execute( 'SELECT path FROM local').fetchall()
            if paths:
                result = [ path[0] for path in paths ]
        except sqlite3.OperationalError:
            self._create_tables()
        cursor.close()
        return result

    def already_in_local( self, path, include_unindentified = 0 ):
        '''Checks if path is already present in local table'''
        result = False
        cursor = self.database.cursor()
        try:
            ret = cursor.execute(
                'SELECT id, release_id FROM local ' + \
                'WHERE path=?',
                ( path, )
            ).fetchone()
            if ret:
                if ret[1] or include_unindentified:
                    result = True
        except sqlite3.OperationalError:
            self._create_tables()
        cursor.close()
        return result

    def save( self ):
        '''Commits changes to database'''
        self.database.commit()

class AdvansceneXML():
    '''Advanscene xml parser'''
    def __init__( self, path = None ):
        self.path     = path
        self.rom_list = []

    def update( self, database, tmp_dir ):
        '''Download new xml from advanscene'''
        updated    = False
        dat_url    = 'http://advanscene.com/offline/datas/ADVANsCEne_NDS_S.zip'
        zip_path   = '%s/%s' % ( tmp_dir, dat_url.split('/')[-1] )

        try:
            url_handler = urllib2.urlopen( dat_url )
            if time.gmtime( database.last_updated ) < time.strptime(
                    url_handler.info().getheader( 'Last-Modified' ),
                    '%a, %d %b %Y %H:%M:%S %Z' ):
                updated = True
                file_handler = open( zip_path, 'w' )
                file_handler.write( url_handler.read() )
                file_handler.close()
                archive = Zip( zip_path, tmp_dir )
                archive.scan_files( 'xml' )
                archive_xml = archive.file_list[0]
                archive.extract( archive_xml, tmp_dir )

                tmp_db = '%s/%s' % ( tmp_dir, archive_xml )
                self.path = tmp_db
                self.parse()
                database.import_known( self )

                os.unlink( tmp_db )
                os.unlink( zip_path )
        except urllib2.URLError as exc:
            print "Unable to download xml: %s" % ( exc )
            exit( 2 )

        return updated

    def parse( self ):
        '''Parses the xml file'''
        try:
            xml = minidom.parse( self.path )
            for node in xml.getElementsByTagName( 'game' ):
                self.rom_list.append( parse_node( node ) )
        except IOError:
            raise Exception( 'AdvParse',
                    'Can not open or parse file %s' % self.path )

    def __contains__( self, item ):
        return self.rom_list.__contains__( item )

    def __iter__( self ):
        return self.rom_list.__iter__()

    def __len__( self ):
        return self.rom_list.__len__()

    def __getitem__( self, item ):
        return self.rom_list.__getitem__( item )

def parse_node( node ):
    '''Parse node'''
    title = node_text( node.getElementsByTagName( 'title' )[0].childNodes )
    publisher = node_text(
            node.getElementsByTagName( 'publisher' )[0].childNodes )
    released_by = node_text(
            node.getElementsByTagName( 'sourceRom' )[0].childNodes )
    region = int( node_text(
            node.getElementsByTagName( 'location' )[0].childNodes ) )
    release_number = int( node_text(
            node.getElementsByTagName( 'releaseNumber' )[0].childNodes ) )
    crc = node_crc( node )
    normalized_name = strip_name( title.lower() )
    return ( release_number, title, crc, publisher, released_by,
            region, normalized_name )

def node_text( node_list ):
    '''Extract text from node'''
    text = []
    for node in node_list:
        if node.nodeType == node.TEXT_NODE:
            text.append( node.data )
    return ''.join( text )

def node_crc( node ):
    '''Returns crc from rom node'''
    for crc in node.getElementsByTagName( 'romCRC' ):
        if crc.getAttribute( 'extension' ) != '.nds':
            continue
        else:
            return int( node_text( crc.childNodes ), 16 )
    return None
