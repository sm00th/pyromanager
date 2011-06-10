'''User interface routines for pyROManager'''
import cmdln
import pyNDSrom.db
import pyNDSrom.file
from cfg import __config__ as config

def list_question( msg, choice_list, default=None ):
    '''Qustion with multiple choices'''
    print "%s [%s](Default: %s)" % ( 
        msg, '/'.join( [ str(x) for x in choice_list ] ),
        default
    )
    reply = raw_input().lower()
    if not reply:
        reply = default
    else:
        try:
            reply = int( reply[0] )
        except ValueError:
            reply = ''

    if reply not in choice_list:
        print "Unexpected input"
        return list_question( msg, choice_list, default )

    return reply


def question_yn( msg, default="y" ):
    '''Yes/No question'''
    choices = {
        'y' : [ 'y', 1 ],
        'n' : [ 'n', 0 ],
    }
    choices[default][0] = choices[default][0].upper()
    choice_list = []
    for vals in choices.values():
        choice_list.append( vals[0] )
    print "%s [%s] " % ( msg, '/'.join( choice_list ) ),
    reply = raw_input().lower()
    if not reply:
        reply = default
    else:
        reply = reply[0]

    if reply not in choices:
        print "Unexpected input: %s" % reply
        return question_yn( msg, default )

    return choices[reply][1]

class Cli( cmdln.Cmdln ):
    def get_optparser( self ):
        parser = cmdln.Cmdln.get_optparser( self )
        parser.add_option(
            "--with-db",
            dest="dbFile",
            help="use specified db-file"
        )
        return parser

    @cmdln.alias( "i", "im" )
    @cmdln.option( "--no-subdirs", action = "store_true",
            help = "do not scan subdirs" )
    @cmdln.option( "--non-interactive", action = "store_true",
            help = "do not ask any questions(probably a bad idea)" )
    @cmdln.option( "-u", "--update", action = "store_true",
            help = "do not rescan files already in db" )
    def do_import( self, subcmd, opts, path ):
        """${cmd_name}: import roms from dir into database

        ${cmd_usage}
        ${cmd_option_list}
        """

        #scanner = pyNDSrom.rom.scanner( "%s/%s" % ( config['confDir'],
            #config['dbFile'] ) )
        #scanner.scanIntoDB( path )
        pyNDSrom.file.scan( path )
        print "subcmd: %s, opts: %s" % ( subcmd, opts )

    @cmdln.alias( "l", "ls" )
    @cmdln.option( "-d", "--duplicates", action = "store_true",
            help = "show duplicate entries only" )
    @cmdln.option( "-k", "--known", action = "store_true",
            help = "query known roms, not the local ones" )
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
            help = "specify xml file to updatefrom" )
    def do_updatedb( self, subcmd, opts ):
        """${cmd_name}: download and import new dat from advanscene

        ${cmd_usage}
        ${cmd_option_list}
        """

        xml = pyNDSrom.db.AdvansceneXML( '%s/%s' % ( config['confDir'],
            config['xmlDB'] ) )
        db = pyNDSrom.db.SQLdb( '%s/%s' % ( config['confDir'], config['dbFile'] ) )
        db.import_known( xml )
        print "subcmd: %s, opts: %s" % ( subcmd, opts )

