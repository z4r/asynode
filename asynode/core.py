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

    :param cid: the connection identifier.
    :type cid: hashable
    :param callback: break point function.
    :type callback: callable
    :param sock: an initialized `socket` [**SERVER MODE**] or nothing [**CLIENT MODE**].
    :type sock: :class:`socket`

    .. note::
        `callback` function will be called with
        *state, inbuffer, cid and a callback*

    .. warning:: Probably you wouldn't subclass it.
    """
    def __init__(self, cid, callback, sock=None):
        " Initilize a new :class:`Connection`"
        sock = sock or socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        asynchat.async_chat.__init__(self, sock)
        self.cid = cid
        self._process = callback
        self._buffer = []
        if self.addr:
            LOGGER.info('Incoming connection from {a}'.format(a=self.addr))
        self._process('INITIAL', self._buffer, cid, self.callback)

    def callback(self, data=None, terminator=None, close=False):
        """ This method, *passed to the event handler function*, is the entry
        point after a complete break point handling.

        :param data: message to send to the other peer.
        :type data: :class:`str`
        :param terminator: new internal terminator.
        :type terminator: :class:`str` or :class:`int`
        :param close: close the channel when done.
        :type close: :class:`bool`
        """
        LOGGER.debug('CALLBACK {d!r} {t!r}'.format(d=data, t=terminator))
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
        LOGGER.info('Connected to {a}'.format(a=self.remote))
        self._process('OPERATIVE', self._buffer, self.cid, self.callback)

    def found_terminator(self):
        if not self._buffer:
            self.handle_close()
        self._process('OPERATIVE', self._buffer, self.cid, self.callback)
        self._buffer = []

    def handle_close(self):
        LOGGER.info('Closing {a}'.format(a=self.remote or ''))
        asynchat.async_chat.handle_close(self)

    @property
    def remote(self):
        """ Return the address of the remote endpoint.
        For IP sockets, the address info is a pair (hostaddr, port).
        """
        return self.socket.getpeername()

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
        self._id        = 0
        self._cache     = {}

    def listen(self, host, port):
        """ Create a listener (default :class:`BaseServerd`) bound on
        host:port.
        """
        self.listener(host, port, self.accept)

    def accept(self, sock):
        """ Create an incoming connection (default :class:`Connection`) and its
        break point handler.

        .. note:: Usually called after a listener's accept.
        """
        cid = self.get_next()
        self._cache[cid] = self.instate()
        self.incoming(cid, self.process, sock)

    def send(self, host, port, *args, **kwargs):
        """ Create and connect an outcoming connection (default
        :class:`Connection`) and its break point handler.
        """
        cid = self.get_next()
        self._cache[cid] = self.outstate(*args, **kwargs)
        self.outcoming(cid, self.process).connect((host, port))

    def process(self, state, data, cid, callback):
        """ Link between connections and break point handlers.

        :param state: break point type.
        :type state: :class:`str`
        :param data: break point buffer.
        :type data: :class:`list`
        :param cid: break point sender identifier.
        :type cid: hashable
        :param callback: connection entry point.
        :type callback: callable.
        """
        next_state = self._cache[cid].next(''.join(data), state)
        if next_state.final:
            del self._cache[cid]
        callback(next_state.push, next_state.terminator, next_state.close)

    def get_next(self):
        " Return a new connection id"
        self._id += 1
        return self._id