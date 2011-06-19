'''Rom info'''
import os, re, shutil
import pyNDSrom.file
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
        self.info      = {}
        self.name_info = None

    def init( self ):
        try:
            # FIXME: helloooo, archives
            self.info['size'] = os.path.getsize( self.path )

            handler          = open( self.path, 'rb' )
            self.info['crc'] = binascii.crc32( handler.read() & 0xFFFFFFFF )
            handler.close()
        except IOError, OSError as exc:
            print 'Failed to read file %s: %s' % ( self.file_path, exc )

    def query_db( self ):
        if not self.info:
            self.init()

        relid = self.database.search_known_crc( self.info['crc'] )

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
            ext  = pyNDSrom.file.extension( main_path )
            if ext == 'zip':
                archive = pyNDSrom.file.ZIP( main_path )
            elif ext == '7z':
                archive = pyNDSrom.file.ZIP7( main_path )
            elif ext == 'rar':
                archive = pyNDSrom.file.RAR( main_path )
            archive.extract( archive_file, path )
            os.rename( '%s/%s' % ( path, archive_file ),
                    '%s/%s' % ( path, self.filename() ) )

    def size_mb( self ):
        '''Returns size in MB'''
        result = 'Unknown'
        if self.file_info['size']:
            result = "%.2fM" % ( self.file_info['size'] / 1048576.0 )
        return result

    def remove( self ):
        '''Remove file from disk and local_roms table'''
        path = re.sub( r":.*$", '', self.file_info['path'] )
        try:
            os.unlink( path )
            self.database.remove_local( path )
        except OSError as exc:
            print "Failed to remove file: %s" % ( exc )

        return 1

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
            norm_name = pyNDSrom.file.parse_filename( 
                    self.file_info['path'] )[1]
        return norm_name

    def local_data( self ):
        '''Returns dataset for db.add_local method'''
        dataset = ( self.rom_info['release_number'], self.file_info['path'],
                self.normalized_name, self.file_info['size'],
                self.file_info['crc32'] )
        return dataset

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
