# -*- coding: utf-8 -*-
from django.conf import settings

from background_task import background
import subprocess

@background()
def do_send_signal(msg, rcpt_list, atts=[]):
    if len(rcpt_list) == 0:
        return

    if not hasattr(settings, 'SIGNAL_BIN') or settings.SIGNAL_BIN == '' or not hasattr(settings, 'SIGNAL_USERNAME') or settings.SIGNAL_USERNAME == '':
        return

    for rcpt in rcpt_list:
        # signal-cli -u USERNAME send -m "test" RECIPIENT
        command = settings.SIGNAL_BIN
        if hasattr(settings, 'SIGNAL_CONFIG') and settings.SIGNAL_CONFIG != '':
            command = '%s --config %s' % (command, settings.SIGNAL_CONFIG)
        command = '%s -u %s send -m "%s" %s' % (command, settings.SIGNAL_USERNAME, msg.replace('"', ''), rcpt)
        if len(atts) > 0:
            command = '%s -a' % command
            for att in atts:
                command = '%s %s' % (command, att)
        subprocess.run([command, '2>> /tmp/signal_err'], shell=True, stdin=None, stdout=None, stderr=None, env={'LANG': 'de_DE.UTF-8'}, close_fds=True)
