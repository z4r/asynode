from smtplib import CRLF, quotedata as qd
from base64 import b64encode

from state import PushState, FinalState, PassState
from state import OutcomingAutomaton, IncomingAutomaton

class AsyncSMTPException(Exception):
    pass

class SMTPOutcomingState(OutcomingAutomaton):
    def __init__(self, *args, **kwargs):
        r'''
        >>> s = SMTPOutcomingState(
        ...     auth = ('user', 'pass'),
        ...     localname = '@work',
        ...     source = 'me@work.it',
        ...     targets = ['you@work.it', 'us@work.it',],
        ...     message = 'Hello World!\nHello Again!',
        ... )
        >>> s._data ==  [
        ... (None, '220'),
        ... ('AUTH PLAIN AHVzZXIAcGFzcw==', '235'),
        ... ('HELO @work', '250'),
        ... ('MAIL FROM: <me@work.it>', '250'),
        ... ('RCPT TO: <you@work.it>', '250'),
        ... ('RCPT TO: <us@work.it>', '250'),
        ... ('DATA', '354'),
        ... ('Hello World!\r\nHello Again!\r\n.', '250'),
        ... ('QUIT', '221'),
        ... ]
        True
        >>> s.next(None, 'INIT') #INIT
        State(push=None, terminator='\r\n', close=False, final=False)
        >>> s.next(None, 'CONNECT') #CONNECT
        State(push=None, terminator=None, close=False, final=False)
        >>> s.next('220') #ACK CONNECT
        State(push='AUTH PLAIN AHVzZXIAcGFzcw==\r\n', terminator=None, close=False, final=False)
        >>> s.next('235') #ACK AUTH
        State(push='HELO @work\r\n', terminator=None, close=False, final=False)
        >>> s.next('250') #ACK HELO
        State(push='MAIL FROM: <me@work.it>\r\n', terminator=None, close=False, final=False)
        >>> s.next('250') #ACK MAIL
        State(push='RCPT TO: <you@work.it>\r\n', terminator=None, close=False, final=False)
        >>> s.next('250') #ACK RCPT_1
        State(push='RCPT TO: <us@work.it>\r\n', terminator=None, close=False, final=False)
        >>> s.next('250') #ACK RCPT_2
        State(push='DATA\r\n', terminator=None, close=False, final=False)
        >>> s.next('354') #ACK DATA
        State(push='Hello World!\r\nHello Again!\r\n.\r\n', terminator=None, close=False, final=False)
        >>> s.next('250') #ACK SENDDATA
        State(push='QUIT\r\n', terminator=None, close=False, final=False)
        >>> s.next('221') #ACK QUIT
        State(push=None, terminator=None, close=False, final=True)
        '''
        self._data = [(None, '220')]
        if kwargs.get('auth'):
            self._data.append((
                'AUTH PLAIN ' + b64encode(("\0%s\0%s") % kwargs.get('auth')),
                '235',
            ))
        self._data.append(('HELO '+ kwargs['localname'], '250'))
        self._data.append(('MAIL FROM: <%s>'% kwargs['source'], '250'))
        for rcptto in kwargs['targets']:
            self._data.append(('RCPT TO: <%s>'% rcptto, '250'))
        self._data.append(('DATA', '354'))
        self._data.append((self.quotedata(kwargs['message']), '250'))
        self._data.append(('QUIT', '221'))
        self._nextcheck = None

    def INIT(self, data):
        return PushState(terminator=CRLF)

    def CONNECT(self, data):
        return self.TERMINATOR(data)

    def TERMINATOR(self, data):
        self._check(data, self._nextcheck)
        try:
            push, self._nextcheck = self._data.pop(0)
            if push is not None:
                push += CRLF
            return PushState(push=push)
        except IndexError:
            return FinalState()

    @staticmethod
    def _check(data, success_code):
        if success_code is not None  and not data.startswith(success_code):
            raise AsyncSMTPException(data)

    @staticmethod
    def quotedata(data):
        q = qd(data)
        if q[-2:] != CRLF:
            q += CRLF
        q += "."
        return q

import socket
class SMTPIncomingState(IncomingAutomaton):
    def __init__(self, *args, **kwargs):
        r'''
        >>> s = SMTPIncomingState(fqdn='z4r.buongiorno.loc')
        >>> s.next(None, 'INIT')
        State(push='220 z4r.buongiorno.loc 1.0\r\n', terminator='\r\n', close=False, final=False)
        >>> s.next('HELO')
        State(push='501 Syntax: HELO hostname\r\n', terminator=None, close=False, final=False)
        >>> s.next('HELO @work')
        State(push='250 z4r.buongiorno.loc\r\n', terminator=None, close=False, final=False)
        >>> s.next('HELO @work')
        State(push='503 Duplicate HELO/EHLO\r\n', terminator=None, close=False, final=False)
        >>> s.next('RCPT TO: <you@work.it>')
        State(push='503 Error: need MAIL command\r\n', terminator=None, close=False, final=False)
        >>> s.next('MAIL FROM: ')
        State(push='501 Syntax: MAIL FROM:<address>\r\n', terminator=None, close=False, final=False)
        >>> s.next('MAIL FROM: <me@work.it>')
        State(push='250 Ok\r\n', terminator=None, close=False, final=False)
        >>> s.next('MAIL FROM: <me@work.it>')
        State(push='503 Error: nested MAIL command\r\n', terminator=None, close=False, final=False)
        >>> s.next('DATA')
        State(push='503 Error: need RCPT command\r\n', terminator=None, close=False, final=False)
        >>> s.next('RCPT TO: <you@work.it>')
        State(push='250 Ok\r\n', terminator=None, close=False, final=False)
        >>> s.next('RCPT TO: <us@work.it>')
        State(push='250 Ok\r\n', terminator=None, close=False, final=False)
        >>> s.next('DATA SEND')
        State(push='501 Syntax: DATA\r\n', terminator=None, close=False, final=False)
        >>> s.next('DATA')
        State(push='354 End data with <CR><LF>.<CR><LF>\r\n', terminator='\r\n.\r\n', close=False, final=False)
        >>> s.next('Hello World!\r\nHello Again!')
        State(push='250 Ok\r\n', terminator='\r\n', close=False, final=False)
        >>> s.next('QUIT')
        State(push='221 Bye', terminator=None, close=True, final=True)
        '''
        self.fqdn = kwargs.get('fqdn', socket.getfqdn())
        self.version = kwargs.get('version', '1.0')
        self.__command = True
        self.__data = ''
        self.__greeting = False
        self.__mailfrom = None
        self.__rcpttos = []

    def INIT(self, data):
        return PushState(
            push='220 {s.fqdn} {s.version}'.format(s=self) + CRLF,
            terminator=CRLF,
        )

    def TERMINATOR(self, data):
        if self.__command:
            if not data:
                return self.reply('500 Error: bad syntax')
            i = data.find(' ')
            if i < 0:
                command, arg = data.upper(), None
            else:
                command, arg = data[:i].upper(), data[i+1:].strip()
            method = getattr(self, '_' + command, None)
            if not method:
                return self.reply('502 Error: command {c!r} not implemented'.format(c=command))
            return method(arg)
        else:
            indata = []
            for text in data.split(CRLF):
                if text and text[0] == '.':
                    text = text[1:]
                indata.append(text[1:])
            self.__data = '\n'.join(indata)
            self.__command = True
            return self.reply('250 Ok', CRLF)

    def _HELO(self, arg):
        if not arg:
            return self.reply('501 Syntax: HELO hostname')
        if self.__greeting:
            return self.reply('503 Duplicate HELO/EHLO')
        self.__greeting = arg
        return self.reply('250 {s.fqdn}'.format(s=self))

    def _MAIL(self, arg):
        address = self.__getaddr('FROM:', arg) if arg else None
        if not address:
            return self.reply('501 Syntax: MAIL FROM:<address>')
        if self.__mailfrom:
            return self.reply('503 Error: nested MAIL command')
        self.__mailfrom = address
        return self.reply('250 Ok')

    def _RCPT(self, arg):
        if not self.__mailfrom:
            return self.reply('503 Error: need MAIL command')
        address = self.__getaddr('TO:', arg) if arg else None
        if not address:
            return self.reply('501 Syntax: RCPT TO: <address>')
        self.__rcpttos.append(address)
        return self.reply('250 Ok')

    def _DATA(self, arg):
        if not self.__rcpttos:
            return self.reply('503 Error: need RCPT command')
        if arg:
            return self.reply('501 Syntax: DATA')
        self.__command = False
        return self.reply('354 End data with <CR><LF>.<CR><LF>', CRLF+'.'+CRLF)

    def _QUIT(self, arg):
        return FinalState(push='221 Bye', close=True)

    def _NOOP(self, arg):
        return self.reply('501 Syntax: NOOP' if arg else '250 Ok')

    def _RSET(self, arg):
        if arg:
            return self.reply('501 Syntax: RSET')
        self.__mailfrom = None
        self.__rcpttos = []
        self.__data = ''
        self.__command = True
        return self.reply('250 Ok')

    @staticmethod
    def __getaddr(keyword, arg):
        address = None
        keylen = len(keyword)
        if arg[:keylen].upper() == keyword:
            address = arg[keylen:].strip()
            if not address:
                pass
            elif address[0] == '<' and address[-1] == '>' and address != '<>':
                address = address[1:-1]
        return address

    @staticmethod
    def reply(message, terminator=None):
        return PushState(message + CRLF, terminator)


if __name__ == '__main__':
    def interactive():
        source = raw_input("Please enter a source: ")
        targets = raw_input("Please enter a list of targets [',' separated]: ").split(',')
        message = [raw_input("Please enter text to send [ENTER + CRTL+C to STOP]: ")]
        while True:
            try:
                message.append(raw_input())
            except KeyboardInterrupt:
                break
        return dict(
            #auth = ('user', 'pass'),
            localname = socket.getfqdn(),
            source = source,
            targets = targets,
            message = '\n'.join(message),
        )
    import logging
    logging.basicConfig(level=logging.INFO)
    from opt import input
    options, args = input()
    import asyncore
    from common import Node
    node = Node(instate=SMTPIncomingState, outstate=SMTPOutcomingState)
    if options.server:
        node.listen(options.host, options.port)
    else:
        kwargs = interactive()
        node.send(options.host, options.port, *args, **kwargs)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        import sys
        sys.exit()