# -*- coding: utf-8 -*-
from django.conf import settings

from background_task import background
import subprocess
import os

@background()
def do_send_signal(msg, rcpt_list, atts=[]):
    if not rcpt_list:
        return

    if not getattr(settings, 'SIGNAL_BIN', '') or not getattr(settings, 'SIGNAL_USERNAME', ''):
        return

    # Recipients can arrive as a list AND/OR as comma-separated strings
    # (e.g. SIGNAL_TEST_RECIPIENT / TICKET_NEW_SIGNAL_RCPT). Flatten to a list of
    # single numbers — signal-cli expects each recipient as its own argument, not
    # a comma-joined string (which it mangles into one "Unregistered user").
    recipients = []
    for entry in rcpt_list:
        if not entry:
            continue
        recipients.extend(r.strip() for r in str(entry).split(',') if r.strip())

    for rcpt in recipients:
        # signal-cli --config C -u SENDER send -m "msg" RECIPIENT
        command = settings.SIGNAL_BIN
        if getattr(settings, 'SIGNAL_CONFIG', ''):
            command = '%s --config %s' % (command, settings.SIGNAL_CONFIG)
        command = '%s -u %s send -m "%s"' % (command, settings.SIGNAL_USERNAME, msg.replace('"', ''))
        # phone numbers are positional recipients; Signal usernames (e.g. "Andree.01")
        # must be passed via --username, otherwise signal-cli treats them as a number.
        if rcpt.startswith('+'):
            command = '%s %s' % (command, rcpt)
        else:
            command = '%s --username %s' % (command, rcpt)
        if len(atts) > 0:
            command = '%s -a' % command
            for att in atts:
                command = '%s %s' % (command, att)
        command = '%s 2>> /tmp/signal_err' % command
        subprocess.run(command, shell=True, stdin=None, stdout=None, stderr=None, env={'LANG': 'de_DE.UTF-8'}, close_fds=True)


@background()
def unlink_file(filename):
    if os.path.isfile(filename):
        print('unlink %s' % filename)
        os.unlink(filename)
