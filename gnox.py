"""
gnox - Gmail Notifications Over XMPP.
Copyright (C) 2011  Alexander Solovets

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import ConfigParser
import logging
import optparse
import os
import time
import xmpp

PROG_NAME = 'gnox'
CONFIG_FILE = '.gnoxrc'

NS_DISCO = 'http://jabber.org/protocol/disco#info'
NS_NOTIFY = 'google:mail:notify'

LOG_LEVELS = [logging.CRITICAL, logging.ERROR, logging.WARN, logging.INFO,
              logging.DEBUG]

retry_pause = 5

logging.basicConfig()
log = logging.getLogger(PROG_NAME)


def parse_mail_notification(mbox):
    if not mbox.has_attr('total-matched'):
        log.error('"total-matched" attribute is absent')
        return

    count = mbox.getAttr('total-matched')
    print count

    for thread in mbox.getChildren():
        subj = thread.getTag('subject')
        print subj.getData()

def send_mail_request(dispatcher):
    iq = xmpp.protocol.Iq('get', queryNS=NS_NOTIFY)
    log.debug('sending new mail request:\n' + str(iq))
    dispatcher.send(iq)


def notify_callback(dispatcher, iq):
    log.debug('IQ received:\n' + unicode(iq))

    if iq.getTag('new-mail'):
        if (iq.getType() == 'error'):
            log.error(iq.getError())
        else:
            log.info('new mail notify received')
            iq = iq.buildReply('result')
            log.debug('sending confirmation response\n' + str(iq))
            dispatcher.send(iq)
            send_mail_request(dispatcher)

        raise xmpp.protocol.NodeProcessed

    mbox = iq.getTag('mailbox')
    if mbox:
        parse_mail_notification(mbox)
        raise xmpp.protocol.NodeProcessed


def feature_request_callback(dispatcher, iq):
    children = iq.getQueryChildren()
    if children:
        for child in children:
            if (child.getName() == 'feature' and
                child.getAttr('var') == NS_NOTIFY):
                log.info('notifications supported')
                dispatcher.UnregisterHandler('iq', feature_request_callback,
                                             ns=NS_DISCO)
                dispatcher.RegisterHandler('iq', notify_callback, ns=NS_NOTIFY)
                send_mail_request(dispatcher)
                raise xmpp.protocol.NodeProcessed


def msg_loop(client, domain):
    #client.RegisterHandler('iq', iq_callback)
    client.RegisterHandler('iq', feature_request_callback, ns=NS_DISCO)

    iq = xmpp.protocol.Iq('get', to=domain, queryNS=NS_DISCO)
    log.debug('sending feature request:\n' + str(iq))
    client.send(iq)

    while True:
        client.Process(1)


def connect(jid, password, retry):
    jid = xmpp.protocol.JID(jid)
    domain = jid.getDomain()

    try:
        while True:
            client = xmpp.Client(domain, debug=[])
            dispatcher = client.connect()

            if dispatcher:
                log.info('connected')
                auth = client.auth(jid.getNode(), password,
                                   resource=jid.getResource())
                client.sendInitPresence(False)

                if auth:
                    log.info('authenticated')
                    msg_loop(client, domain)
                    break

            log.error('authentication failed')

            if not retry:
                break
            else:
                log.info('next try after %d seconds' % retry_pause)
                time.sleep(retry_pause)
    except KeyboardInterrupt:
        client.disconnect()


def main():
    parser = optparse.OptionParser(prog=PROG_NAME)
    parser.add_option('-v', action='count', help='verbosity level')
    parser.add_option('-r', '--retry', action='store_true',
                      help='retry on failure')

    opts, args = parser.parse_args()

    if opts.v:
        if opts.v > len(LOG_LEVELS):
            parser.error('too high verbosity level - must be between 0 and 5')
        else:
            log.setLevel(LOG_LEVELS[opts.v - 1])

    config = ConfigParser.ConfigParser()
    config.read([os.path.join(i, CONFIG_FILE)
                 for i in [os.path.expanduser('~'), os.getcwd()]])

    connect(config.get('user', 'jid'), config.get('user', 'password'),
                       opts.retry)


if __name__ == '__main__':
    main()
