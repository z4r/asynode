from asynode.opt import main_loop, parse_input
from asynode.state import Automaton, State
from asynode import __version__ as version

CRLF = "\r\n"
HTTP = "HTTP/1.1"

class HTTPOutcomingAutomaton(Automaton):
    def __init__(self, *args, **kwargs):
        r"""
        >>> s = HTTPOutcomingAutomaton(
        ...     method = 'get',
        ...     path = '/',
        ...     hostname = 'localhost'
        ... )
        >>> s._method
        'GET'
        >>> s._headers == {
        ... 'Host': 'localhost',
        ... 'Accept-Encoding': 'identity',
        ... 'User-Agent': 'Asynode ' + version
        ... }
        True
        >>> s._body
        >>> s.next(None, 'INITIAL') #INIT
        State(push=None, terminator='\r\n\r\n', close=False, final=False)
        >>> s.next(None)
        State(push='GET / HTTP/1.1\r\nHost: localhost\r\nAccept-Encoding: identity\r\nUser-Agent: Asynode 0.1\r\n\r\n', terminator=None, close=False, final=False)
        >>> s.next('HTTP/1.0 200 OK')
        State(push=None, terminator=None, close=True, final=True)
        """
        self._method = kwargs.get('method', 'GET').upper()
        self._path = kwargs['path']
        self._headers = {
            'Host': kwargs['hostname'],
            'Accept-Encoding': 'identity',
            'User-Agent': kwargs.get('ua', 'Asynode '+ version)
        }
        self._headers.update(kwargs.get('headers', {}))
        self._body = kwargs.get('body')

    def initial(self, data):
        return State.get_push(terminator=CRLF*2)

    def operative(self, data):
        if data:
            return State.get_final(close=True)
        push = ' '.join([self._method, self._path, HTTP])
        for k,v in self._headers.iteritems():
            push += CRLF + k + ': ' + v
        push += CRLF*2
        return State.get_push(push=push)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    options, args = parse_input()
    from core import ConnectionFactory
    node = ConnectionFactory(
        instate=None, outstate=HTTPOutcomingAutomaton
    )
    if options.server:
        node.listen(options.host, options.port)
    else:
        kwargs = {
            'path':'/api/1.0/',
            'hostname': options.host,
            'headers': {
                'Accept': 'application/xml'
            }
        }
        node.send(
            options.host, options.port, *args, **kwargs
        )
    main_loop()
