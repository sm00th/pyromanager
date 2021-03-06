'''User interface routines for pyromanager'''
import cmdln, os, re
import db, cfg, rom
import logging

logging.basicConfig( format="%(asctime)-15s %(levelname)-9s %(message)s" )
log = logging.getLogger( 'pyromgr' )
log.setLevel( logging.INFO )

def verbose( self, opt, value, parser, *args, **kwargs ):
    log.setLevel( logging.DEBUG )


def colorize( msg, colorid = 0 ):
    '''Colorize string'''
    return "\x1b[%i;01m%s\x1b[39;49;00m" % ( colorid, msg )

class Cli( cmdln.Cmdln ):
    def __init__( self, *args ):
        cmdln.Cmdln.__init__( self, args )
        self.config = cfg.Config()
        self.color  = True
        self.config.read_config()
        self.database = db.SQLdb( self.config.db_file )

    def get_optparser( self ):
        parser = cmdln.Cmdln.get_optparser( self )
        parser.add_option(
            "--with-db",
            dest="db_file",
            help="use specified db-file"
        )
        parser.add_option(
            "-v",
            "--verbose",
            action = "callback",
            callback = verbose,
            help="verbose logging"
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

        rom.import_path( path, opts, self.database, self.config, self )

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
                rom_obj = rom.Rom( None, self.database, self.config, self,
                        file_info = rom.FileInfo( None, self.config.tmp_dir,
                            self.database.file_info( local_id ) ) )
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
                lambda id: rom.Rom( None, self.database, self.config, self,
                    file_info = rom.FileInfo( None, self.config.tmp_dir,
                        self.database.file_info( id ) ) ),
                self.database.search_name( name, table = 'local' )
        )
        answer = self.list_question( "Possible roms:", rom_list, "Which one?" )
        if answer != None:
            rom_list[answer].upload( path )
            save_list = rom_list[answer].get_saves()
            if save_list:
                answer = self.list_question( "Savefiles found for this rom:",
                        save_list, "Which one should be uploaded?" )
                if answer != None:
                    save_list[answer].upload( path )

    @cmdln.alias( "rd" )
    def do_rmdupes( self, subcmd, opts ):
        """${cmd_name}: remove duplicate roms from disk

        ${cmd_usage}
        ${cmd_option_list}
        """
        for ( entries, crc ) in self.database.find_dupes():
            rom_list = map(
                    lambda id: rom.Rom( None, self.database, self.config, self,
                        file_info = rom.FileInfo( None, self.config.tmp_dir,
                            self.database.file_info( id ) ) ),
                    self.database.search_crc( crc, table = 'local' )
            )

            pre_msg = "%d duplicates found for *%s*\n" % ( entries,
                    rom_list[0] ) + "Delete all but one(None - let all be)"
            answer = self.list_question( pre_msg, rom_list, "Which one?" )
            if answer != None:
                del rom_list[answer]
                for rom_obj in rom_list:
                    rom_obj.remove()
                    self.database.save()
            print

    @cmdln.alias( "udb" )
    @cmdln.option( "-f", "--force", action = "store_true",
            help = "Force update even if xml is up to date" )
    def do_updatedb( self, subcmd, opts ):
        """${cmd_name}: download and import new dat from advanscene

        ${cmd_usage}
        ${cmd_option_list}
        """

        xml = db.AdvansceneXML()
        if xml.update( self.database, self.config.tmp_dir ) or opts.force:
            self.database.save()
            log.info( "Database updated" )
        else:
            log.info( "Already up to date" )

    @cmdln.alias( "c", "cdb" )
    def do_cleandb( self, subcmd, opts ):
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

    @cmdln.alias( "bs" )
    def do_backupsaves( self, subcmd, opts, *path ):
        """${cmd_name}: Savefile manager

        ${cmd_usage}
        ${cmd_option_list}
        """

        if path:
            path = path[0]
        else:
            path = self.config.flashcart

        for nds_path in rom.search( path, self.config ):
            save_path = rom.get_save( nds_path, self.config.save_ext )
            if save_path:
                local_id = rom.identify( nds_path, self.database )
                if local_id:
                    relid = None
                    try:
                        relid = self.database.search_local( 'release_id',
                                'id', local_id )[0]
                    except TypeError:
                        pass
                    save_mtime = os.stat( save_path ).st_mtime
                    save = rom.SaveFile( relid, local_id, save_mtime, None,
                            self.config )
                    if not save.stored():
                        log.info( "Backing up %s %s" % ( save_path, save ) )
                        save.copy_from( save_path )

    def highlight( self, msg ):
        result = msg
        if self.color:
            result = re.sub( r'\*([^*]+)\*', colorize( r'\1', 31 ), msg )
        else:
            result = re.sub( r'\*([^*]+)\*', r'\1', msg )
        return result

    def list_question( self, pre_msg, choice_list, msg, default = None ):
        '''Qustion with multiple choices'''
        if pre_msg:
            print "%s" % self.highlight( pre_msg )
        index = 0
        for choice in choice_list:
            print_index = "%3d" % index
            if self.color:
                print_index = colorize( print_index, 32 )
            print " %s. %s" % ( print_index, choice )
            index += 1

        index_list = range( index ) + [ None ]

        print "%s [%s] (Default: %s)" % (
            msg, '/'.join( [ str(x) for x in index_list ] ),
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

        if reply not in index_list:
            print "Unexpected input"
            return self.list_question( pre_msg, choice_list, msg, default )

        return reply

    def get_string( self, prompt ):
        print "%s: " % ( prompt ),
        return raw_input()

    def question_yn( self, pre_msg, msg, default="y" ):
        '''Yes/No question'''
        if pre_msg:
            print "%s" % self.highlight( pre_msg )
        choices = {
            'y' : [ 'y', True ],
            'n' : [ 'n', False ],
        }
        choices[default][0] = choices[default][0].upper()
        if self.color:
            choices[default][0] = colorize( choices[default][0], 32 )
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
            return self.question_yn( msg, default )

        return choices[reply][1]
