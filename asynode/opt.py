from optparse import OptionParser

def parse_input():
    parser = OptionParser()
    parser.add_option('-s', '--server',
        action  = 'store_true',
        dest    = "server",
        help    = "Server MODE",
        default = False,
    )
    parser.add_option('-a', '--address',
        action  = 'store',
        dest    = "host",
        help    = "Host [localhost]",
        default = 'localhost',
    )
    parser.add_option('-p', '--port',
        action  = 'store',
        dest    = 'port',
        type    = 'int',
        help    = 'Port [8080]',
        default = 8080,
    )
    return parser.parse_args()