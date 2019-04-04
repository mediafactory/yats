# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import getpass
import xmlrpclib
from furl import furl
from yats.models import docs, docs_files
from yats.docs import get_doc_files_folder
import re
import os
import mimetypes
try:
    from xmlrpclib import Binary
except ImportError:
    from xmlrpc.client import Binary

def convert(text, base_path, multilines=True):
    text = re.sub('\r\n', '\n', text)
    text = re.sub(r'{{{(.*?)}}}', r'`\1`', text)
    text = re.sub(r'(?sm){{{(\n?#![^\n]+)?\n(.*?)\n}}}', r'```\n\2\n```', text)

    text = text.replace('[[TOC]]', '')
    text = text.replace('[[BR]]', '\n')
    text = text.replace('[[br]]', '\n')

    if multilines:
        text = re.sub(r'^\S[^\n]+([^=-_|])\n([^\s`*0-9#=->-_|])', r'\1 \2', text)

    text = re.sub(r'(?m)^======\s+(.*?)\s+======$', r'\n###### \1', text)
    text = re.sub(r'(?m)^=====\s+(.*?)\s+=====$', r'\n##### \1', text)
    text = re.sub(r'(?m)^====\s+(.*?)\s+====$', r'\n#### \1', text)
    text = re.sub(r'(?m)^===\s+(.*?)\s+===$', r'\n### \1', text)
    text = re.sub(r'(?m)^==\s+(.*?)\s+==$', r'\n## \1', text)
    text = re.sub(r'(?m)^=\s+(.*?)\s+=$', r'\n# \1', text)
    text = re.sub(r'^             * ', r'****', text)
    text = re.sub(r'^         * ', r'***', text)
    text = re.sub(r'^     * ', r'**', text)
    text = re.sub(r'^ * ', r'*', text)
    text = re.sub(r'^ \d+. ', r'1.', text)

    a = []
    is_table = False
    for line in text.split('\n'):
        if not line.startswith('    '):
            line = re.sub(r'\[\[(https?://[^\[\]\|]+)\|([^\[\]]+)\]\]', r'[\2](\1)', line)
            line = re.sub(r'\[(https?://[^\s\[\]]+)\s([^\[\]]+)\]', r'[\2](\1)', line)
            line = re.sub(r'\[wiki:([^\s\[\]]+)\s([^\[\]]+)\]', r'[\2](%s/\1)' % os.path.relpath('/wikis/', base_path), line)
            line = re.sub(r'\[source:([^\s\[\]]+)\s([^\[\]]+)\]', r'[\2](%s/\1)' % os.path.relpath('/tree/master/', base_path), line)
            line = re.sub(r'source:([\S]+)', r'[\1](%s/\1)' % os.path.relpath('/tree/master/', base_path), line)
            line = re.sub(r'\!(([A-Z][a-z0-9]+){2,})', r'\1', line)
            line = re.sub(r'\[\[Image\(source:([^(]+)\)\]\]', r'![](%s/\1)' % os.path.relpath('/tree/master/', base_path), line)
            line = re.sub(r'\[\[Image\(([^(]+)\)\]\]', r'![](\1)', line)
            line = re.sub(r'\'\'\'(.*?)\'\'\'', r'*\1*', line)
            line = re.sub(r'\'\'(.*?)\'\'', r'_\1_', line)
            if line.startswith('||'):
                if not is_table:
                    sep = re.sub(r'[^|]', r'-', line)
                    line = line + '\n' + sep
                    is_table = True
                line = re.sub(r'\|\|', r'|', line)
            else:
                is_table = False
        else:
            is_table = False
        a.append(line)
    text = '\n'.join(a)
    return text

class Command(BaseCommand):
    help = 'import wiki from trac'
    requires_migrations_checks = True
    requires_system_checks = False

    def _get_pass(self, prompt="Password: "):
        p = getpass.getpass(prompt=prompt)
        if not p:
            raise CommandError("aborted")
        return p

    def add_arguments(self, parser):
        parser.add_argument('username', help='Username for TRAC')
        parser.add_argument('server', help='URL to TRAC XMLRPC API with login - e.g. http://your.server.de/login/rpc/')
        parser.add_argument('yatsuser', help='user used to create the docs in YATS')

    def handle(self, *args, **options):
        if options['username']:
            username = options['username']
        else:
            raise CommandError('missing username')

        if options['server']:
            server = options['server']
        else:
            raise CommandError('missing server')

        if options['yatsuser']:
            yatsuser = options['yatsuser']
        else:
            raise CommandError('missing yatsuser')

        password = self._get_pass()

        user = get_user_model().objects.get(username=yatsuser)

        url = furl(server)
        url.password = password
        url.username = username

        rpc_srv = xmlrpclib.ServerProxy(url.tostr(), allow_none=True, use_datetime=True)
        documents = rpc_srv.wiki.getAllPages()
        for doc in documents:
            if doc.startswith('Trac'):
                continue
            if doc.startswith('Wiki'):
                continue

            page = rpc_srv.wiki.getPage(doc)
            info = rpc_srv.wiki.getPageInfo(doc)
            # print info

            d = docs()
            d.caption = doc
            d.text = convert(page, '/docs/').strip()
            d.u_date = info['lastModified']
            d.save(user=user)

            atts = rpc_srv.wiki.listAttachments(doc)
            for att in atts:
                print '=> %s' % att
                path, filename = os.path.split(att)
                file = rpc_srv.wiki.getAttachment(att)

                f = docs_files()
                f.name = filename
                f.size = 0
                #f.checksum =
                f.content_type = mimetypes.guess_type(filename)
                f.doc_id = d.id
                f.public = True
                f.save(user=user)

                dest = get_doc_files_folder()
                if not os.path.exists(dest):
                    os.makedirs(dest)

                with open('%s%s.dat' % (dest, f.id), 'wb+') as destination:
                    destination.write(Binary(file))

                # todo:
                # checksum
                # convert preview

            self.stdout.write('%s => %s' % (doc, d.pk))
