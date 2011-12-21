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

def main_loop():
    import asyncore
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        import sys
        sys.exit()

def main_mail(instate, outstate):
    def interactive():
        import socket
        source = raw_input("Please enter a source: ")
        targets = raw_input("Please enter a list of targets [',' separated]: ")
        message = [raw_input("Please enter text to send [CRTL+C to STOP]: ")]
        while True:
            try:
                message.append(raw_input())
            except KeyboardInterrupt:
                break
        return dict(
            #auth = ('user', 'pass'),
            localname = socket.getfqdn(),
            source = source,
            targets = targets.split(','),
            message = '\n'.join(message),
        )
    import logging
    logging.basicConfig(level=logging.INFO)
    options, args = parse_input()
    from core import ConnectionFactory
    node = ConnectionFactory(
        instate=instate, outstate=outstate
    )
    if options.server:
        node.listen(options.host, options.port)
    else:
        kwargs = interactive()
        node.send(
            options.host, options.port, *args, **kwargs
        )
    main_loop()
