'''Rom info'''
class Rom:
    '''internal representation of roms'''

    def __init__( self ):
        self.release_number  = None
        self.name            = None
        self.normalized_name = None
        self.size            = None
        self.publisher       = None
        self.region          = None
        self.path            = None

    def __str__( self ):
        return "%d - %s (%s) Size: %s" % ( self.release_number, self.name, 
                self.region, self.size )
