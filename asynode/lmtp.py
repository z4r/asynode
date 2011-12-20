from smtp import SMTPOutcomingAutomaton, SMTPIncomingAutomaton

class LMTPOutcomingAutomaton(SMTPOutcomingAutomaton):
    @staticmethod
    def _HELO(localname):
        return 'LHLO '+ localname, '250'

class LMTPIncomingAutomaton(SMTPIncomingAutomaton):
    def _LHLO(self, arg):
        if not arg:
            return self.reply('501 Syntax: LHLO hostname')
        if self._greeting:
            return self.reply('503 Duplicate LHLO')
        self._greeting = arg
        return self.reply('250 {s.fqdn}'.format(s=self))

    def _HELO(self, arg):
        return self.not_implemented('HELO')

if __name__ == '__main__':
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
    from opt import parse_input
    OPTIONS, ARGS = parse_input()
    import asyncore
    from common import ConnectionFactory
    NODE = ConnectionFactory(
        instate=LMTPIncomingAutomaton, outstate=LMTPOutcomingAutomaton
    )
    if OPTIONS.server:
        NODE.listen(OPTIONS.host, OPTIONS.port)
    else:
        KWARGS = interactive()
        NODE.send(OPTIONS.host, OPTIONS.port, *ARGS, **KWARGS) # pylint: disable=W0142
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        import sys
        sys.exit()

