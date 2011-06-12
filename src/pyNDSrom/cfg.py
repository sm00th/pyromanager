'''Configuration for pyNDSrom'''
import os

# TODO: actual config
__config__ = {
    'confDir'    : os.path.expanduser( "~/.pyROManager" ),
    'dbFile'     : 'pyro.db',
    'xmlDB'      : 'ADVANsCEne_NDS_S.xml',
    'extensions' : [ 'nds', 'zip', '7z' ],
    #'extensions' : [ 'nds', 'zip', '7z', 'rar' ], Lets do nds alone first
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

