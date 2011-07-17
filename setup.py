#!/usr/bin/env python

from distutils.core import setup

setup( name          = "pyromanager",
        version      = "0.1.1",
        description  = 'nds rom manager',
        author       = 'Artem Savkov',
        author_email = 'artem.savkov@gmail.com',
        url          = 'http://github.com/sm00th/pyromanager',
        license      = 'GPL',
        platforms    = 'Linux',
        packages     = [
            'pyromanager',
        ],
        py_modules   = [
            'pyromanager.db',
            'pyromanager.ui',
            'pyromanager.rom',
            'pyromanager.cfg',
        ],
        package_dir  = {
            'pyromanager' : 'pyromanager'
        },

        scripts      = [
            'pyromgr',
        ],

        classifiers  = [
            'Topic :: ROM :: NDS',
            'License :: GPL License',
            'Environment :: Console',
            'Development Status :: 1 - Alpha',
        ],

        requires = [
            'cmdln',
            'pyxml',
        ],
    )
