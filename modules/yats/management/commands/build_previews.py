# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.conf import settings
from yats.models import tickets_files
from yats.shortcuts import convertPDFtoImg, convertOfficeTpPDF

import os

class Command(BaseCommand):
    args = '<>'
    help = 'generate previews for all uploaded files in tickets'

    def handle(self, *args, **options):
        dest = settings.FILE_UPLOAD_PATH
        if not os.path.exists(dest):
            os.makedirs(dest)

        files = tickets_files.objects.exclude(content_type__icontains='access').exclude(content_type__icontains='image')
        for file in files:
            src = '%s%s.dat' % (settings.FILE_UPLOAD_PATH, file.id)
            if not os.path.isfile('%s/%s.preview' % (dest, file.id)):
                self.stdout.write(src)
                if 'pdf' in file.content_type:
                    convertPDFtoImg('%s/%s.dat' % (dest, file.id), '%s/%s.preview' % (dest, file.id))
                else:
                    if 'image' not in file.content_type:
                        tmp = convertOfficeTpPDF('%s/%s.dat' % (dest, file.id))
                        convertPDFtoImg(tmp, '%s/%s.preview' % (dest, file.id))
                        os.unlink(tmp)

        self.stdout.write('done')
