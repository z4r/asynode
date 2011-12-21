from smtplib import CRLF, quotedata as qd
from base64 import b64encode

from state import State, Automaton

class AsyncSMTPException(Exception):
    pass

class SMTPOutcomingAutomaton(Automaton):
    def __init__(self, *args, **kwargs):
        r'''
        >>> s = SMTPOutcomingAutomaton(
        ...     auth = ('user', 'pass'),
        ...     localname = '@work',
        ...     source = 'me@work.it',
        ...     targets = ['you@work.it', 'us@work.it',],
        ...     message = 'Hello World!\nHello Again!',
        ... )
        >>> s._indata ==  [
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
        >>> s.next(None, 'INITIAL') #INIT
        State(push=None, terminator='\r\n', close=False, final=False)
        >>> s.next(None) #CONNECT
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
        super(SMTPOutcomingAutomaton, self).__init__()
        self._indata = [(None, '220')]
        if kwargs.get('auth'):
            self._indata.append((
                'AUTH PLAIN ' + b64encode(("\0%s\0%s") % kwargs.get('auth')),
                '235',
            ))
        self._indata.append(self._helo(kwargs['localname']))
        self._indata.append(self._mail(kwargs['source']))
        self._indata.extend(self._rcpt(kwargs['targets']))
        self._indata.append(self._data())
        self._indata.append(self._qmsg(kwargs['message']))
        self._indata.append(self._quit())
        self._nextcheck = None

    def initial(self, data):
        return State.get_push(terminator=CRLF)

    def operative(self, data):
        self._check(data, self._nextcheck)
        try:
            push, self._nextcheck = self._indata.pop(0)
            if push is not None:
                push += CRLF
            return State.get_push(push=push)
        except IndexError:
            return State.get_final()

    @staticmethod
    def _helo(localname):
        return 'HELO '+ localname, '250'

    @staticmethod
    def _mail(source):
        return 'MAIL FROM: <%s>'% source, '250'

    @staticmethod
    def _rcpt(targets):
        for target in targets:
            yield 'RCPT TO: <%s>'% target, '250'

    @staticmethod
    def _data():
        return 'DATA', '354'

    @staticmethod
    def _qmsg(message):
        message = qd(message)
        if not message.endswith(CRLF):
            message += CRLF
        message += "."
        return message, '250'

    @staticmethod
    def _quit():
        return 'QUIT', '221'


    @staticmethod
    def _check(data, success_code):
        if success_code is not None  and not data.startswith(success_code):
            raise AsyncSMTPException(data)

import socket
class SMTPIncomingAutomaton(Automaton):
    def __init__(self, *args, **kwargs):
        r'''
        >>> s = SMTPIncomingAutomaton(fqdn='z4r.buongiorno.loc')
        >>> s.next(None, 'INITIAL')
        State(push='220 z4r.buongiorno.loc 1.0\r\n', terminator='\r\n', close=False, final=False)
        >>> s.next('LHLO')
        State(push="502 Error: command 'lhlo' not implemented\r\n", terminator=None, close=False, final=False)
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
        super(SMTPIncomingAutomaton, self).__init__()
        self.fqdn = kwargs.get('fqdn', socket.getfqdn())
        self.version = kwargs.get('version', '1.0')
        self._command = True
        self._indata = ''
        self._greeting = False
        self._mailfrom = None
        self._rcpttos = []

    def initial(self, data):
        return self.reply(
            message='220 {s.fqdn} {s.version}'.format(s=self),
            terminator=CRLF,
        )

    def operative(self, data):
        if self._command:
            if not data:
                return self.reply('500 Error: bad syntax')
            i = data.find(' ')
            if i < 0:
                command, arg = data.lower(), None
            else:
                command, arg = data[:i].lower(), data[i+1:].strip()
            method = getattr(self, '_' + command, None)
            if not method:
                return self.not_implemented(command)
            return method(arg)
        else:
            return self._qmsg(data)

    def _qmsg(self, arg):
        indata = []
        for text in arg.split(CRLF):
            if text and text[0] == '.':
                text = text[1:]
            indata.append(text[1:])
        self._indata = '\n'.join(indata)
        self._command = True
        return self.reply('250 Ok', CRLF)

    def _helo(self, arg):
        if not arg:
            return self.reply('501 Syntax: HELO hostname')
        if self._greeting:
            return self.reply('503 Duplicate HELO/EHLO')
        self._greeting = arg
        return self.reply('250 {s.fqdn}'.format(s=self))

    def _mail(self, arg):
        address = self.cleanaddr('FROM:', arg) if arg else None
        if not address:
            return self.reply('501 Syntax: MAIL FROM:<address>')
        if self._mailfrom:
            return self.reply('503 Error: nested MAIL command')
        self._mailfrom = address
        return self.reply('250 Ok')

    def _rcpt(self, arg):
        if not self._mailfrom:
            return self.reply('503 Error: need MAIL command')
        address = self.cleanaddr('TO:', arg) if arg else None
        if not address:
            return self.reply('501 Syntax: RCPT TO: <address>')
        self._rcpttos.append(address)
        return self.reply('250 Ok')

    def _data(self, arg):
        if not self._rcpttos:
            return self.reply('503 Error: need RCPT command')
        if arg:
            return self.reply('501 Syntax: DATA')
        self._command = False
        return self.reply('354 End data with <CR><LF>.<CR><LF>', CRLF+'.'+CRLF)

    def _quit(self, arg):
        return State.get_final(push='221 Bye', close=True)

    def _noop(self, arg):
        return self.reply('501 Syntax: NOOP' if arg else '250 Ok')

    def _rset(self, arg):
        if arg:
            return self.reply('501 Syntax: RSET')
        self._mailfrom = None
        self._rcpttos = []
        self._indata = ''
        self._command = True
        return self.reply('250 Ok')

    @staticmethod
    def cleanaddr(keyword, arg):
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
        return State.get_push(message + CRLF, terminator)

    @classmethod
    def not_implemented(cls, command):
        return cls.reply(
            '502 Error: command {c!r} not implemented'.format(c=command)
        )


if __name__ == '__main__':
    from opt import main_mail
    main_mail(instate=SMTPIncomingAutomaton, outstate=SMTPOutcomingAutomaton)