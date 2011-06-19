'''Rom info'''
import os, re, shutil
import pyNDSrom.file
import cfg

class Rom:
    '''internal representation of roms'''

    def __init__( self, rom_data = None, file_data = None ):
        self.rom_info = {
                'release_number'  : None,
                'name'            : None,
                'publisher'       : None,
                'released_by'     : None,
                'region'          : None,
                'normalized_name' : None,
        }
        self.file_info = {
                'path'  : None,
                'size'  : None,
                'crc32' : None,
        }
        if file_data:
            self.set_file_info( file_data )
        if rom_data:
            self.set_rom_info( rom_data )

    def has_data( self ):
        '''Checks if there is any information in this object'''
        result = 0
        if self.rom_info['name'] or self.rom_info['path']:
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

    def set_file_info( self, file_data ):
        '''Set file information'''
        self.file_info = {
                'path'  : file_data[0],
                'size'  : file_data[1],
                'crc32' : file_data[2],
        }
        return 1

    def set_rom_info( self, rom_data ):
        '''Set rom information'''
        config = cfg.Config()
        config.read_config()
        self.rom_info = {
                'release_number'  : rom_data[0],
                'name'            : rom_data[1],
                'publisher'       : rom_data[2],
                'released_by'     : rom_data[3],
                'region'          : config.region_name( rom_data[4] ),
                'normalized_name' : rom_data[5],
        }
        return 1,

    def size_mb( self ):
        '''Returns size in MB'''
        result = 'Unknown'
        if self.file_info['size']:
            result = "%.2fM" % ( self.file_info['size'] / 1048576.0 )
        return result


    def archive_path( self ):
        '''Separates inarchive file from actual path'''
        main_path    = self.file_info['path']
        archive_file = None
        try:
            ( main_path, archive_file ) = self.file_info['path'].split( ':' )
        except ValueError:
            pass
        return ( main_path, archive_file )

    def filename( self ):
        '''Formatted filename'''
        # TODO: filename format
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

    def remove( self, database = None ):
        '''Remove file from disk, if database is specified also remove from
        local_roms'''
        path = re.sub( r":.*$", '', self.file_info['path'] )
        try:
            os.unlink( path )
        except OSError as exc:
            print "Failed to remove file: %s" % ( exc )

        if database:
            database.remove_local( path )

        return 1

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
