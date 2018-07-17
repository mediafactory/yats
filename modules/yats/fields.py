from django.utils.translation import ugettext_lazy as _
from django import forms
from django.conf import settings
from django.forms.utils import ValidationError
from os import chmod
import hashlib
from io import BytesIO
try:
    import pyclamd
except:
    pass

class yatsFileField(forms.FileField):
    default_error_messages = {
        'virus_found': _(u"file is infected by virus: %s"),
        'virus_engine_error': _(u'unable to initialize scan engine on host %s')
    }

    def clean(self, data, initial=None):
        f = super(yatsFileField, self).clean(initial or data)
        if f is None:
            return None
        elif not data and initial:
            return initial

        if settings.FILE_UPLOAD_VIRUS_SCAN and pyclamd:
            # virus scan
            try:
                if not hasattr(pyclamd, 'scan_stream'):
                    cd = pyclamd.ClamdUnixSocket()
                else:
                    pyclamd.init_network_socket('localhost', 3310)
                    cd = pyclamd

                # We need to get a file object for clamav. We might have a path or we might
                # have to read the data into memory.
                if hasattr(data, 'temporary_file_path'):
                    chmod(data.temporary_file_path(), 0664)
                    result = cd.scan_file(data.temporary_file_path())
                else:
                    if hasattr(data, 'read'):
                        result = cd.scan_stream(data.read())
                    else:
                        result = cd.scan_stream(data['content'])
            except:
                from socket import gethostname
                raise ValidationError(self.error_messages['virus_engine_error'] % gethostname())

            if result:
                msg = ' '.join(result[result.keys()[0]]).replace('FOUND ', '')
                raise ValidationError(self.error_messages['virus_found'] % msg)


        hasher = hashlib.md5()
        # We need to get a file object for clamav. We might have a path or we might
        # have to read the data into memory.
        if hasattr(data, 'temporary_file_path'):
            with open(data.temporary_file_path(), 'rb') as afile:
                buf = afile.read()
                hasher.update(buf)
            self.hash = hasher.hexdigest()
        else:
            if hasattr(data, 'read'):
                data.seek(0)
                buf = data.read()
                hasher.update(buf)
            else:
                hasher.update(data['content'].read())
        f.hash = hasher.hexdigest()

        return f
