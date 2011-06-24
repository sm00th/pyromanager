'''Database manipulation module'''
import re, os, time, shutil
import urllib2
import sqlite3
import rom
import cfg
from xml.dom import minidom

def node_text( node_list ):
    '''Extract text from node'''
    text = []
    for node in node_list:
        if node.nodeType == node.TEXT_NODE:
            text.append( node.data )
    return ''.join( text )

class SQLdb():
    '''Sqlite3 db interface'''
    def __init__( self, db_file = None, config = None ):
        if not config:
            config = cfg.Config()
        config.read_config()
        rom.mkdir( config.config_dir )
        self.database = sqlite3.connect( db_file or config.db_file )

    def __del__( self ):
        self.database.close()

    def _create_tables( self ):
        '''Creates tables if they dont exist'''
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
            'release_id TEXT,' + \
            'path TEXT,' + \
            'search_name TEXT,' + \
            'size NUMERIC,' + \
            'crc NUMERIC,' + \
            'UNIQUE( path ) ON CONFLICT REPLACE);'
        )
        cursor.close()
        self.save()

    def import_known( self, provider ):
        '''Imports known roms from provider'''
        self._create_tables()

        cursor = self.database.cursor()
        for data in provider.rom_list:
            cursor.execute(
                'INSERT OR REPLACE INTO known VALUES(?,?,?,?,?,?,?)',
                data
            )
        cursor.close()
        return 1

    def search_crc( self, crc, table = 'known' ):
        '''Search known roms by crc value'''
        id_list = None
        cursor = self.database.cursor()
        returned = cursor.execute(
            'SELECT id FROM %s WHERE crc=?' % table,
            ( crc, )
        ).fetchall()
        if returned:
            id_list = [ x[0] for x in returned ]
        cursor.close()

        return id_list

    def search_name( self, name, region = None, table = 'known' ):
        '''Search known roms by name'''
        result = []

        returned    = None
        cursor      = self.database.cursor()
        search_name = '%' + re.sub( r"\s", '%', name ) + '%'
        if region != None:
            returned = cursor.execute(
                'SELECT id ' + \
                'FROM %s ' % table + \
                'WHERE search_name LIKE ? and region=?',
                ( search_name, region ) 
            ).fetchall()
        else:
            returned = cursor.execute(
                'SELECT id ' + \
                'FROM %s ' % table + \
                'WHERE search_name LIKE ?',
                ( search_name, ) 
            ).fetchall()
        if returned:
            result = [ x[0] for x in returned ]
        cursor.close()

        return result

    def remove_local( self, path ):
        '''Remove file from local'''
        cursor = self.database.cursor()
        cursor.execute( 'DELETE from local where path LIKE ?', (
            '%s%%' % path, ) )
        cursor.close()
        return 1

    def file_info( self, relid ):
        '''File info from local table'''
        cursor = self.database.cursor()
        result = ( None, None, None, None )
        returned = cursor.execute(
            'SELECT release_id, path, size, crc ' + \
            'FROM local WHERE relid=?',
            ( relid, )
        ).fetchone()
        if returned:
            result = returned
        cursor.close()

        return result

    def rom_info( self, relid ):
        '''Rom info from known table'''
        cursor = self.database.cursor()
        result = ( None, None, None, None, None, None )
        returned = cursor.execute(
            'SELECT id, name, publisher, released_by, region, ' + \
            'search_name ' + \
            'FROM known WHERE id=?',
            ( relid, )
        ).fetchone()
        if returned:
            result = returned
        cursor.close()

        return result

    def add_local( self, local_info ):
        '''Add local rom to db'''
        cursor = self.database.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO local ' + \
            '( release_id, path, search_name, size, crc ) ' + \
            'values ( ?, ?, ?, ?, ? )',
            local_info
        )
        return 1

    def find_dupes( self ):
        '''Search for duplicate roms'''
        result = []
        cursor = self.database.cursor()
        dupes = cursor.execute(
            'SELECT COUNT(*) as entries, crc FROM ' + \
            'local GROUP BY crc HAVING entries > 1'
        ).fetchall()
        if dupes:
            result = dupes
        cursor.close()
        return result

    def already_in_local( self, path, include_unindentified = 0 ):
        '''Check if path is already present in local'''
        result = 0
        cursor = self.database.cursor()
        ret = cursor.execute(
            'SELECT id, release_id FROM local ' + \
            'WHERE path=?',
            ( path, )
        ).fetchone()
        if ret:
            if ret[1] or include_unindentified:
                result = 1
        cursor.close()
        return result

    def save( self ):
        '''Commit changes to database'''
        self.database.commit()

class AdvansceneXML():
    '''Advanscene xml parser'''
    def __init__( self, path, config ):
        self.path     = path
        self.config   = config
        self.rom_list = []

    def update( self ):
        '''Download new xml from advanscene'''
        rom.mkdir( self.config.config_dir )
        updated    = 0
        dat_url    = 'http://advanscene.com/offline/datas/ADVANsCEne_NDS_S.zip'
        zip_path   = '%s/%s' % ( self.config.tmp_dir, dat_url.split('/')[-1] )

        url_handler = urllib2.urlopen( dat_url )
        if not( os.path.exists( self.config.xml_file ) )or time.gmtime(
                os.stat( self.config.xml_file ).st_mtime ) < time.strptime(
                url_handler.info().getheader( 'Last-Modified' ),
                '%a, %d %b %Y %H:%M:%S %Z' ):
            updated = 1
            file_handler = open( zip_path, 'w' )
            file_handler.write( url_handler.read() )
            file_handler.close()
            archive = rom.Zip( zip_path, self.config )
            archive.scan_files( 'xml' )
            archive_xml = archive.file_list[0]
            archive.extract( archive_xml, self.config.tmp_dir )
            shutil.move( '%s/%s' % ( self.config.tmp_dir, archive_xml ),
                    self.config.xml_file )
            os.unlink( zip_path )

        return updated

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
        region = node_text(
                node.getElementsByTagName( 'location' )[0].childNodes )
        release_number = int( node_text(
                node.getElementsByTagName( 'releaseNumber' )[0].childNodes ) )
        crc = self.get_crc( node )
        normalized_name = rom.strip_name( title.lower() )
        return ( release_number, title, crc, publisher, released_by,
                region, normalized_name )

    def get_crc( self, node ):
        '''Returns crc from rom node'''
        for crc in node.getElementsByTagName( 'romCRC' ):
            if crc.getAttribute( 'extension' ) != '.nds':
                continue
            else:
                return int( node_text( crc.childNodes ), 16 )
        return None
