# -*- coding: utf-8 -*- 
from django import forms
from django.contrib.auth.models import User
from django.utils import importlib
from django.conf import settings
from django.forms.models import construct_instance
from bootstrap_toolkit.widgets import BootstrapDateInput
from django.utils.translation import ugettext as _
from yats.fields import yatsFileField
from yats.models import ticket_resolution, ticket_flow, ticket_flow_edges, boards

mod_path, cls_name = settings.TICKET_CLASS.rsplit('.', 1)
mod = importlib.import_module(mod_path)
mod_cls = getattr(mod, cls_name)

def save_instance(form, instance, fields=None, fail_message='saved',
                  commit=True, exclude=None, construct=True, user=None):
    """
    Saves bound Form ``form``'s cleaned_data into model instance ``instance``.

    If commit=True, then the changes to ``instance`` will be saved to the
    database. Returns ``instance``.

    If construct=False, assume ``instance`` has already been constructed and
    just needs to be saved.
    """
    if construct:
        instance = construct_instance(form, instance, fields, exclude)
    opts = instance._meta
    if form.errors:
        raise ValueError("The %s could not be %s because the data didn't"
                         " validate." % (opts.object_name, fail_message))

    # Wrap up the saving of m2m data as a function.
    def save_m2m():
        cleaned_data = form.cleaned_data
        # Note that for historical reasons we want to include also
        # virtual_fields here. (GenericRelation was previously a fake
        # m2m field).
        for f in opts.many_to_many + opts.virtual_fields:
            if not hasattr(f, 'save_form_data'):
                continue
            if fields and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            if f.name in cleaned_data:
                f.save_form_data(instance, cleaned_data[f.name])
    if commit:
        # If we are committing, save the instance and the m2m data immediately.
        instance.save(user=user)
        save_m2m()
    else:
        # We're not committing. Add a method to the form to allow deferred
        # saving of m2m data.
        form.save_m2m = save_m2m
    return instance

class TicketsForm(forms.ModelForm):
    required_css_class = 'required'
    
    file_addition = forms.BooleanField(required=False)
       
    def __init__(self, *args, **kwargs):
        if not 'user' in kwargs:
            raise Exception('missing user')
        self.user = kwargs.pop('user')
        self.view_only = kwargs.pop('view_only', False)

        if not 'customer' in kwargs:
            raise Exception('missing customer')
        self.customer = kwargs.pop('customer')
        
        if 'exclude_list' in kwargs:
            exclude_list = kwargs.pop('exclude_list')
        else:
            exclude_list = []
            
        if not 'is_stuff' in kwargs or not kwargs.pop('is_stuff'):
            exclude_list = list(set(exclude_list + settings.TICKET_NON_PUBLIC_FIELDS))
            
            super(TicketsForm, self).__init__(*args, **kwargs)
            
            if self.fields.get('customer'):
                self.fields['customer'].queryset = self.fields['customer'].queryset.filter(pk=self.customer) 
        else:
            super(TicketsForm, self).__init__(*args, **kwargs)
        
        for field in exclude_list:
            del self.fields[field]
            
        for field in self.fields:
            if type(self.fields[field]) is forms.fields.DateField:
                self.fields[field].widget = BootstrapDateInput()
                
        # remove fields after close
        if not self.instance.pk is None and self.instance.closed and not self.view_only:
            available_fields = []
            for field in self.fields:
                available_fields.append(str(field))
                
            for field in available_fields:
                if str(field) not in settings.TICKET_EDITABLE_FIELDS_AFTER_CLOSE:
                    del self.fields[str(field)]
            
        # disallow non state
        if 'state' in self.fields:
            self.fields['state'].empty_label = None
        
            # only allow possible states
            if not self.instance.pk is None and not self.view_only:
                flows = list(ticket_flow_edges.objects.select_related('next').filter(now=self.instance.state).exclude(next__type=2).values_list('next', flat=True))
                flows.append(self.instance.state_id)
                self.fields['state'].queryset = self.fields['state'].queryset.filter(id__in=flows)
                    
    def save(self, commit=True):
        """
        Saves this ``form``'s cleaned_data into model instance
        ``self.instance``.

        If commit=True, then the changes to ``instance`` will be saved to the
        database. Returns ``instance``.
        """
        if self.instance.pk is None:
            fail_message = 'created'
        else:
            fail_message = 'changed'
        return save_instance(self, self.instance, self._meta.fields,
                             fail_message, commit, self._meta.exclude,
                             construct=False, user=self.user)

    class Meta:
        model = mod_cls
        exclude = ['c_date', 'c_user', 'u_date', 'u_user', 'd_date', 'd_user', 'active_record', 'closed', 'close_date', 'last_action_date']
        
class SearchForm(forms.ModelForm):
    required_css_class = 'do_not_require'

    def __init__(self, *args, **kwargs):
        if not 'user' in kwargs:
            raise Exception('missing user')
        self.user = kwargs.pop('user')
        
        if not 'customer' in kwargs:
            raise Exception('missing customer')
        self.customer = kwargs.pop('customer')
        
        if 'include_list' in kwargs:
            include_list = kwargs.pop('include_list')
        else:
            include_list = []
            
        if not 'is_stuff' in kwargs or not kwargs.pop('is_stuff'):
            used_fields = []
            for ele in include_list:
                if not ele in settings.TICKET_NON_PUBLIC_FIELDS:
                    used_fields.append(ele)
            super(SearchForm, self).__init__(*args, **kwargs)
            
            if self.fields.get('customer'):
                self.fields['customer'].queryset = self.fields['customer'].queryset.filter(pk=self.customer) 
        else:
            used_fields = include_list
            super(SearchForm, self).__init__(*args, **kwargs)
        available_fields = []
        for field in self.fields:
            available_fields.append(str(field))
            
        for field in available_fields:
            if str(field) not in used_fields:
                del self.fields[str(field)]
            
        for field in self.fields:
            if type(self.fields[field]) is forms.fields.DateField:
                self.fields[field].widget = BootstrapDateInput()
                
            if type(self.fields[field]) is forms.fields.BooleanField:
                self.fields[field] = forms.NullBooleanField()
                
        # unset initial
        for field in self.fields:
            self.fields[field].initial = None
                                    
    def save(self, commit=True):
        """
        Saves this ``form``'s cleaned_data into model instance
        ``self.instance``.

        If commit=True, then the changes to ``instance`` will be saved to the
        database. Returns ``instance``.
        """
        if self.instance.pk is None:
            fail_message = 'created'
        else:
            fail_message = 'changed'
        return save_instance(self, self.instance, self._meta.fields,
                             fail_message, commit, self._meta.exclude,
                             construct=False, user=self.user)

    class Meta:
        model = mod_cls
        labels = {
            'c_date': _('created'),
            'u_date': _('updated'),
            'd_date': _('deleted'),
            'c_user': _('created by'),
            'u_user': _('last updated by'),
            'd_user': _('deleted by'),
        }
        
class CommentForm(forms.Form):
    comment = forms.CharField(required=True, label=_('comment'))

class UploadFileForm(forms.Form):
    file = yatsFileField(label=_('file'), required=True)
    
class TicketCloseForm(forms.Form):
    resolution = forms.ModelChoiceField(queryset=ticket_resolution.objects.filter(active_record=True), label=_('resolution'))
    close_comment = forms.CharField(widget=forms.Textarea(), label=_('comment'))
    
class TicketReassignForm(forms.Form):
    assigned = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True), label=_('assigned'))
    state = forms.ModelChoiceField(queryset=ticket_flow.objects.all(), label=_('next'), empty_label=None)
    reassign_comment = forms.CharField(widget=forms.Textarea(), label=_('comment'))

ORDER_BY_CHOICES = (
    ('id', _('ticket number')),
    ('close_date', _('closing date'))
)

ORDER_DIR_CHOICES = (
    ('', _('ascending')),
    ('-', _('descending'))
)

POST_FILTER_CHOICES = (
    (0, '-------------'),
    (1, _('days since closed')),
    (2, _('days since created')),
    (3, _('days since last changed')),
    (4, _('days since last action')),
)

class AddToBordForm(forms.Form):
    method = forms.CharField(widget=forms.HiddenInput(), initial='add')
    board = forms.ModelChoiceField(queryset=boards.objects.filter(active_record=True), label=_('board'), empty_label=None)
    column = forms.CharField(label=_('column'))
    limit = forms.IntegerField(label=_('limit'), required=False)
    extra_filter = forms.ChoiceField(choices=POST_FILTER_CHOICES, label=_('extra filter'), required=False)
    days = forms.IntegerField(label=_('days'), required=False)
    order_by = forms.ChoiceField(choices=ORDER_BY_CHOICES, label=_('order by'))
    order_dir = forms.ChoiceField(choices=ORDER_DIR_CHOICES, label=_('order direction'), required=False)
    