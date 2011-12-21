from smtp import SMTPOutcomingAutomaton, SMTPIncomingAutomaton

class LMTPOutcomingAutomaton(SMTPOutcomingAutomaton):
    @staticmethod
    def _helo(localname):
        return 'LHLO '+ localname, '250'

class LMTPIncomingAutomaton(SMTPIncomingAutomaton):
    def _lhlo(self, arg):
        if not arg:
            return self.reply('501 Syntax: LHLO hostname')
        if self._greeting:
            return self.reply('503 Duplicate LHLO')
        self._greeting = arg
        return self.reply('250 {s.fqdn}'.format(s=self))

    def _helo(self, arg):
        return self.not_implemented('HELO')

if __name__ == '__main__':
    from opt import main_mail
    main_mail(instate=LMTPIncomingAutomaton, outstate=LMTPOutcomingAutomaton)