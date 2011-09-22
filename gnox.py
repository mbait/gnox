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
import sys
import time
import xmpp

NS_DISCO = 'http://jabber.org/protocol/disco#info'
NS_NOTIFY = 'google:mail:notify'

CONFIG_FILE = '.gnoxrc'

retry_pause = 5
will_notify = False

logging.basicConfig()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def iq_callback(c, iq):
    global will_notify

    log.debug('IQ received:\n' + unicode(iq))

    new_mail = iq.getTag('new-mail')
    if new_mail and new_mail.getNamespace() == NS_NOTIFY:
        if (iq.getType() == 'error'):
            log.error(iq.getError())
        else:
            iq = iq.buildReply('result')
            log.info('new mail notify received')
            log.debug('sending confirmation response\n' + str(iq))
            c.send(iq)
            iq = xmpp.protocol.Iq('get', to='asolovets@gmail.com',
                                  queryNS=NS_NOTIFY)
            log.debug('sending new mail request:\n' + str(iq))
            c.send(iq)
            raise xmpp.protocol.NodeProcessed

    children = iq.getQueryChildren()
    if children:
        for child in children:
            if (child.getName() == 'feature' and
                child.getAttr('var') == NS_NOTIFY):
                log.info('notifications supported')
                will_notify = True
                break


def main_loop(domain, client):
    global will_notify

    client.RegisterHandler('iq', iq_callback)

    iq = xmpp.protocol.Iq('get', to=domain, queryNS=NS_DISCO)
    log.debug('sending feature request:\n' + str(iq))
    client.send(iq)

    while True:
        if will_notify:
            iq = xmpp.protocol.Iq('get', to='asolovets@gmail.com',
                                  queryNS=NS_NOTIFY)
            log.debug('sending new mail request:\n' + str(iq))
            client.send(iq)
            will_notify = False

        try:
            client.Process(1)
        except KeyboardInterrupt:
            client.disconnect()
            log.info('disconnected')
            break


def main():
    parser = optparse.OptionParser()
    parser.add_option('-v', action='count', help='verbosity level')

    opts, args = parser.parse_args()

    print opts.v

    config = ConfigParser.ConfigParser()
    config.read([os.path.join(i, CONFIG_FILE)
                 for i in [os.path.expanduser('~'), os.getcwd()]])

    sys.exit(0)

    while True:
        jid = xmpp.protocol.JID(user)
        domain = jid.getDomain()
        client = xmpp.Client(domain, debug=[])
        c = client.connect()

        if c:
            log.info('connected')
            auth = client.auth(jid.getNode(), password,
                               resource=jid.getResource())
            client.sendInitPresence(False)

            if auth:
                log.info('authenticated')
                main_loop(domain, client)
                break

            log.error('authentication failed, next try after %d seconds'
                      % retry_pause)

        time.sleep(retry_pause)


if __name__ == '__main__':
    main()
