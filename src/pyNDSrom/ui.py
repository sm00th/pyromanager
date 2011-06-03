import pyNDSrom
import cmdln
import os
import sys

config = {
        'confDir' : os.path.expanduser( "~/.pyROManager" ),
        'dbFile'  : 'pyro.db',
        'xmlDB'   : 'ADVANsCEne_NDS_S.xml',
}

def question_yn( question, default="y" ):
    choices = {
            'y' : [ 'y', 1 ],
            'n' : [ 'n', 0 ],
        }
    choices[default][0] = choices[default][0].upper()
    choiceList = []
    for vals in choices.values():
        choiceList.append( vals[0] )
    print "%s [%s] " % ( question, '/'.join( choiceList ) ),
    reply = raw_input().lower()
    if not reply:
        reply = default
    else:
        reply = reply[0]

    if reply not in choices:
        print "Unexpected input"
        return question_yn( question, default )

    import pprint
    pprint.pprint( choices )
    return choices[reply][1]

class cli( cmdln.Cmdln ):

    def get_optparser( self ):
        parser = cmdln.Cmdln.get_optparser( self )
        parser.add_option( "--with-db", dest="dbFile", help="use specified db-file" )
        return parser

    @cmdln.alias( "i", "im" )
    @cmdln.option( "--no-subdirs", action="store_true",
            help="do not scan subdirs" )
    @cmdln.option( "--non-interactive", action="store_true",
            help="do not ask any questions(probably a bad idea)" )
    def do_import( self, subcmd, opts, path ):
        """${cmd_name}: import roms from dir into database
        
        ${cmd_usage}
        ${cmd_option_list}
        """

        scanner = pyNDSrom.DirScanner( "%s/%s" % ( config['confDir'],
            config['dbFile'] ) )
        scanner.scanIntoDB( path )
        print "scanning %s(not really yet)" % path
        print "subcmd: %s, opts: %s" % ( subcmd, opts )

    @cmdln.alias( "l", "ls" )
    @cmdln.option( "-d", "--duplicates", action="store_true",
            help="show duplicate entries only" )
    @cmdln.option( "-k", "--known", action = "store_true",
            help="query known roms, not the local ones" )
    def do_list( self, subcmd, opts, *terms ):
        """${cmd_name}: query db for roms
        
        ${cmd_usage}
        ${cmd_option_list}
        """
        if terms:
            for term in terms:
                print "searching for %s..." % term
        else:
            print "list errything"
        print "subcmd: %s, opts: %s" % ( subcmd, opts )

    @cmdln.option( "-x", "--xml",
            help="specify xml file to updatefrom" )
    def do_updatedb( self, subcmd, opts ):
        """${cmd_name}: download and import new dat from advanscene
        
        ${cmd_usage}
        ${cmd_option_list}
        """

        xml = pyNDSrom.AdvansceneXML( '%s/%s' % ( config['confDir'],
            config['xmlDB'] ) )
        db = pyNDSrom.SQLdb( '%s/%s' % ( config['confDir'], config['dbFile'] ) )
        db.importKnownFrom( xml )
        print "subcmd: %s, opts: %s" % ( subcmd, opts )

