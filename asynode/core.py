""" This module is the core of asynode.
It implements a listener :class:`BaseServerd`,
a bi-directional connection handler :class:`Connection`
and a factory :class:`ConnectionFactory` to link connections and break point
handlers. The term ``break point``  is intended to indicate a point in the
protocol execution you need to interpret an event.
"""
import asyncore
import asynchat
import socket
import logging
LOGGER = logging.getLogger('asynode')

__all__ = (
    'BaseServerd',
    'Connection',
    'ConnectionFactory',
)

class BaseServerd(asyncore.dispatcher):
    """ This class is responsible for managing incoming event.
    On an incoming event, it calls back ``on_accept`` function passed during its
    initialization.

    :param host: network host name or ip.
    :type host: :class:`str`
    :param port: listening port.
    :type port: :class:`int`
    :param on_accept: callback function called on accept event.
    :type on_accept: callable

    .. note:: ``on_accept`` have to *accept* a :class:`socket` as input
        parameter.
    """
    def __init__ (self, host, port, on_accept):
        " Initialize and bind an Event Listener."
        asyncore.dispatcher.__init__ (self)
        self.on_accept = on_accept
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)
        LOGGER.info('Listening on {h}:{p}'.format(h=host, p=port))

    def handle_accept(self):
        sock, _ = self.accept()
        self.on_accept(sock)


class Connection(asynchat.async_chat):
    """ A :class:`Connection` can implement an event handler (**SERVER MODE**)
    or an event creator (**CLIENT MODE**). Input and output data management is
    handled through some break points to an external object that notify
    something to be managed. After managing a break point you can re-enter
    inside this class via :meth:`callback`.

    +------------------------+-----------------+
    | Break Point            | State           |
    +========================+=================+
    | ``__init__()``         | ``INITIAL``     |
    +------------------------+-----------------+
    | ``handle_connect()``   | ``OPERATIVE``   |
    +------------------------+-----------------+
    | ``found_terminator()`` | ``OPERATIVE``   |
    +------------------------+-----------------+

    .. note::
        Only in **CLIENT MODE** we have to handle a connection.

    :param automaton: break point function.
    :type automaton: :class:`state.Automaton`
    :param sock: an initialized `socket` [**SERVER MODE**] or nothing [**CLIENT MODE**].
    :type sock: :class:`socket`

    .. note::
        `callback` function will be called with
        *state, inbuffer, cid and a callback*

    .. warning:: Probably you wouldn't subclass it.
    """
    def __init__(self, automaton, sock=None):
        " Initilize a new :class:`Connection`"
        sock = sock or socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        asynchat.async_chat.__init__(self, sock)
        self.automaton = automaton
        self._buffer = []
        if self.addr:
            LOGGER.info('Incoming connection from {s.addr}'.format(s=self))
        self.process('INITIAL', self._buffer)

    def process(self, state, data):
        """ Process a break point """
        next_state = self.automaton.next(''.join(data), state)
        data = next_state.push
        terminator = next_state.terminator
        close = next_state.close
        LOGGER.debug('NEXT {d!r} {t!r}'.format(d=data, t=terminator))
        if terminator is not None:
            LOGGER.debug('Setting terminator to {t!r}'.format(t=terminator))
            self.set_terminator(terminator)
        if data is not None:
            logd = data.strip() or '<QUIT>'
            LOGGER.info('{s.local} => {s.remote}: {d!r}'.format(s=self, d=logd))
            self.push(data)
        if close:
            self.close_when_done()

    def collect_incoming_data(self, data):
        LOGGER.info('{s.local} <= {s.remote}: {d!r}'.format(s=self, d=data))
        self._buffer.append(data)

    def handle_connect(self):
        LOGGER.info('Connected to {s.remote}'.format(s=self))
        self.process('OPERATIVE', self._buffer)

    def found_terminator(self):
        if not self._buffer:
            self.handle_close()
        self.process('OPERATIVE', self._buffer)
        self._buffer = []

    def handle_close(self):
        LOGGER.info('Closing {s.remote}'.format(s=self))
        asynchat.async_chat.handle_close(self)

    def handle_error(self):
        LOGGER.error('Handling connection error')
        self.process('ERROR', self._buffer)

    @property
    def remote(self):
        """ Return the address of the remote endpoint.
        For IP sockets, the address info is a pair (hostaddr, port).
        """
        try:
            return self.socket.getpeername()
        except Exception as e:
            LOGGER.error(e)
            return '', ''

    @property
    def local(self):
        """ Return the address of the local endpoint.
        For IP sockets, the address info is a pair (hostaddr, port).
        """
        return self.socket.getsockname()


class ConnectionFactory(object):
    """ This class helps to create connections and manage their break points
    binding connections and their break points handlers.

    :param instate: Incoming connection break point handler.
    :type instate: :class:`Automaton`
    :param outstate: Outcoming connection break point handler.
    :type outstate: :class:`Automaton`
    """
    def __init__(self, instate, outstate, **kwargs):
        " Initilize a new :class:`ConnectionFactory`"
        self.instate    = instate
        self.outstate   = outstate
        self.listener   = kwargs.get('listener', BaseServerd)
        self.incoming   = kwargs.get('inconn', Connection)
        self.outcoming  = kwargs.get('outconn', Connection)
        self.collect    = kwargs.get('collect', lambda x: x)

    def listen(self, host, port, on_accept=None):
        """ Create a listener (default :class:`BaseServerd`) bound on
        host:port.
        """
        on_accept = on_accept or self.accept
        self.listener(host, port, on_accept)

    def accept(self, sock):
        """ Create an incoming connection (default :class:`Connection`) and its
        break point handler.

        .. note:: Usually called after a listener's accept.
        """
        conn = self.incoming(self.instate(), sock)
        self.collect(conn)

    def send(self, host, port, *args, **kwargs):
        """ Create and connect an outcoming connection (default
        :class:`Connection`) and its break point handler.
        """
        conn = self.outcoming(self.outstate(*args, **kwargs))
        self.collect(conn)
        conn.connect((host, port))
