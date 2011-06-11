'''Rom info'''
import pyNDSrom.file
import pyNDSrom.db
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
                'path' : None,
                'size' : None,
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
                self.normalized_name, self.file_info['size'] )
        return dataset

    def set_file_info( self, file_data ):
        '''Set file information'''
        self.file_info = {
                'path' : file_data[0],
                'size' : file_data[1],
        }
        return 1

    def set_rom_info( self, rom_data ):
        '''Set rom information'''
        self.rom_info = {
                'release_number'  : rom_data[0],
                'name'            : rom_data[1],
                'publisher'       : rom_data[2],
                'released_by'     : rom_data[3],
                'region'          : pyNDSrom.db.decode_location( rom_data[4] ),
                'normalized_name' : rom_data[5],
        }
        return 1,

    def __str__( self ):
        rom_string = "%s - %s (%s)" % (
            self.rom_info['release_number'], self.rom_info['name'],
                self.rom_info['region'] )
        if self.file_info['size']:
            rom_string += ' Size: %d' % self.file_info['size']
        return rom_string
