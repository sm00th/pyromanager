import cmdln

class cli( cmdln.Cmdln ):

    @cmdln.alias( "i", "im" )
    @cmdln.option( "-s", "--no-subdirs", action = "store_true",
                  help = "do not scan subdirs" )
    @cmdln.option( "-n", "--non-interactive", action = "store_true",
                   help = "do not ask any questions(probably a bad idea)" )
    def do_import( self, subcmd, opts, path ):
        """${cmd_name}: import roms from dir into database
        
        ${cmd_usage}
        ${cmd_option_list}
        """
        print "scanning %s(not really yet)" % path
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
        print "sir, we are going to download stuff, sir"
        print "subcmd: %s, opts: %s" % ( subcmd, opts )

