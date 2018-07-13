from django.utils.translation import ugettext_lazy as _
from django import forms
from django.conf import settings
from django.forms.utils import ValidationError
from os import chmod

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

        if settings.FILE_UPLOAD_VIRUS_SCAN:
            # virus scan
            try:
                pyclamd.init_network_socket('localhost', 3310)

                # We need to get a file object for clamav. We might have a path or we might
                # have to read the data into memory.
                if hasattr(data, 'temporary_file_path'):
                    chmod(data.temporary_file_path(), 0664)
                    result = pyclamd.scan_file(data.temporary_file_path())
                else:
                    if hasattr(data, 'read'):
                        result = pyclamd.scan_stream(data.read())
                    else:
                        result = pyclamd.scan_stream(data['content'])
            except:
                from socket import gethostname
                raise ValidationError(self.error_messages['virus_engine_error'] % gethostname())

            if result:
                raise ValidationError(self.error_messages['virus_found'] % result[result.keys()[0]])

        return f
