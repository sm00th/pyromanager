'''User interface routines for pyROManager'''
import cmdln, os
import db, cfg, rom

def list_question( msg, choice_list, default=None ):
    '''Qustion with multiple choices'''
    print "%s [%s](Default: %s)" % ( 
        msg, '/'.join( [ str(x) for x in choice_list ] ),
        default
    ),
    reply = raw_input().lower()
    if not reply:
        reply = default
    else:
        try:
            reply = int( reply )
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
    def __init__( self, *args ):
        cmdln.Cmdln.__init__( self, args )
        self.config = cfg.Config()
        self.config.read_config()
        self.database = db.SQLdb( self.config.db_file )

    def get_optparser( self ):
        parser = cmdln.Cmdln.get_optparser( self )
        parser.add_option(
            "--with-db",
            dest="db_file",
            help="use specified db-file"
        )
        return parser

    @cmdln.alias( "i", "im" )
    @cmdln.option( "--no-subdirs", action = "store_true",
            help = "do not scan subdirs" )
    @cmdln.option( "--non-interactive", action = "store_true",
            help = "do not ask any questions(probably a bad idea)" )
    @cmdln.option( "-r", "--full-rescan", action = "store_true",
            help = "readd files even if already in db" )
    def do_import( self, subcmd, opts, path ):
        """${cmd_name}: import roms from dir into database

        ${cmd_usage}
        ${cmd_option_list}
        """

        rom.import_path( path, opts, self.config, self.database )

    @cmdln.alias( "l", "ls" )
    @cmdln.option( "-k", "--known", action = "store_true",
            help = "query known roms, not the local ones" )
    def do_list( self, subcmd, opts, *terms ):
        """${cmd_name}: query db for roms

        ${cmd_usage}
        ${cmd_option_list}
        """
        if not terms:
            terms = [ '%' ]
        for term in terms:
            for local_id in self.database.search_name( term, table = 'local' ):
                rom_obj = rom.Rom( None, self.database, self.config, file_info =
                        rom.FileInfo( None, self.database, self.config,
                            local_id ) )
                print rom_obj

    @cmdln.alias( "u", "up" )
    def do_upload( self, subcmd, opts, name, *path ):
        """${cmd_name}: upload roms to flashcart

        ${cmd_usage}
        ${cmd_option_list}
        """

        if not path:
            path = self.config.flashcart

        rom_list = map(
                lambda id: rom.Rom( None, self.database, self.config,
                    file_info = rom.FileInfo( None, self.database, self.config,
                        id ) ),
                self.database.search_name( name, table = 'local' )
        )
        index = 0
        for rom_obj in rom_list:
            print " %3d. %s" % ( index, rom_obj )
            index += 1
        answer = list_question( "Which one?", range( index ) + [None] )
        if answer != None:
            rom_list[answer].upload( path )

    def do_rmdupes( self, subcmd, opts ):
        """${cmd_name}: remove duplicate roms from disk

        ${cmd_usage}
        ${cmd_option_list}
        """
        for ( entries, crc ) in self.database.find_dupes():
            rom_list = map(
                    lambda id: rom.Rom( None, self.database, self.config,
                        file_info = rom.FileInfo( None, self.database,
                            self.config, id ) ),
                    self.database.search_crc( crc, table = 'local' )
            )
            print "%d duplicates found for %s" % ( entries, rom_list[0] )
            print "Delete all but one(None - let all be)"
            index = 0
            for rom_obj in rom_list:
                print " %d. %s" % ( index, rom_obj.path )
                index += 1
            answer = list_question( "Which one?", range( index ) + [None] )
            if answer != None:
                del rom_list[answer]
                for rom_obj in rom_list:
                    rom_obj.remove()
                    self.database.save()
            print

    @cmdln.option( "-f", "--force", action = "store_true",
            help = "Force update even if xml is up to date" )
    def do_updatedb( self, subcmd, opts ):
        """${cmd_name}: download and import new dat from advanscene

        ${cmd_usage}
        ${cmd_option_list}
        """

        xml = db.AdvansceneXML( self.config.xml_file, self.config )
        if xml.update() or opts.force:
            xml.parse()
            self.database.import_known( xml )
            self.database.save()
            print "Database updated"
        else:
            print "Already up to date"

    def do_clean( self, subcmd, opts ):
        """${cmd_name}: Find and remove from db files that are no longer
        present

        ${cmd_usage}
        ${cmd_option_list}
        """

        for path in self.database.path_list():
            path = path.split( ':' )[0]
            if not os.path.exists( path ):
                self.database.remove_local( path )
        self.database.save()
