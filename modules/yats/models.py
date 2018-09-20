# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.text import slugify
from markdownx.models import MarkdownxField

import json
import uuid

YES_NO_DONT_KNOW = (
    (None, '---------'),
    (True, _('yes')),
    (False, _('no')),
)

STATE_CHOICES = (
    (0, _('working state')),
    (1, _('first state')),
    (2, _('last state')),
)

def get_flow_start():
    start = ticket_flow.objects.filter(active_record=True, type=1)[:1]
    if len(start) > 0:
        return start[0]

def get_flow_end():
    end = ticket_flow.objects.filter(active_record=True, type=2)[:1]
    if len(end) > 0:
        return end[0]

def get_next_flow(current_state):
    pass

def get_default_resolution():
    return ticket_resolution.objects.first()

def convertPrio(value):
    if value:
        if value == 0:
            return None
        try:
            return ticket_priority.objects.get(caldav=value).pk
        except ticket_priority.DoesNotExist:
            prios = ticket_priority.objects.get(caldav__gt=value).order_by('caldav').pk
            try:
                return prios[0]
            except:
                return None
    else:
        return None


# user profiles
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True)

    organisation = models.ForeignKey('organisation', null=True)
    jabber = models.CharField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            try:
                p = UserProfile.objects.get(user=self.user)
                self.pk = p.pk
            except UserProfile.DoesNotExist:
                pass

        super(UserProfile, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _('user profile')
        verbose_name_plural = _(u'user profiles')


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # try/except just for syncdb / south
        try:
            UserProfile.objects.get_or_create(user=instance)
        except:
            pass

post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL)

class base(models.Model):
    active_record = models.BooleanField(default=True)

    # creation
    c_date = models.DateTimeField(_('creation time'), default=timezone.now)
    c_user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('creator'), related_name='+')
    # update
    u_date = models.DateTimeField(default=timezone.now)
    u_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')
    # deletion'
    d_date = models.DateTimeField(null=True)
    d_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', null=True)

    def save(self, *args, **kwargs):
        if 'user' not in kwargs and 'user_id' not in kwargs:
            raise Exception('missing user')
        if 'user' in kwargs:
            self.u_user = kwargs['user']
            if not self.pk:
                self.c_user = kwargs['user']
            else:
                self.u_user = kwargs['user']
            del kwargs['user']
        if 'user_id' in kwargs:
            self.u_user_id = kwargs['user_id']
            if not self.pk:
                self.c_user_id = kwargs['user_id']
            else:
                self.u_user_id = kwargs['user_id']
            del kwargs['user_id']
        self.u_date = timezone.now()
        super(base, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if 'user' not in kwargs and 'user_id' not in kwargs:
            raise Exception('missing user for delete')
        self.d_date = timezone.now()
        if 'user' in kwargs:
            self.d_user = kwargs['user']
        if 'user_id' in kwargs:
            self.d_user_id = kwargs['user_id']
        self.active_record = False
        self.save(**kwargs)

    class Meta():
        abstract = True

class organisation(base):
    name = models.CharField(max_length=255)
    hourly_rate = models.FloatField(null=True)

    def __unicode__(self):
        return self.name

class ticket_type(base):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('ticket type')
        verbose_name_plural = _(u'ticket types')

class ticket_priority(base):
    list_display = ('name', 'caldav')

    name = models.CharField(max_length=255)
    color = models.CharField(max_length=255, default='transparent')
    caldav = models.SmallIntegerField(default=0)  # defined from 0-9 0=undefined, 1=highest, 9=lowest

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('ticket priority')
        verbose_name_plural = _(u'ticket priorities')

class ticket_resolution(base):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('ticket resolution')
        verbose_name_plural = _(u'ticket resolutions')

class ticket_flow(base):
    name = models.CharField(max_length=255)
    type = models.SmallIntegerField(default=0, choices=STATE_CHOICES)  # 1 = open, 2 = close, 0 = all nodes in between

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('ticket state')
        verbose_name_plural = _(u'ticket states')

class ticket_flow_edges(base):
    now = models.ForeignKey(ticket_flow, related_name='now')
    next = models.ForeignKey(ticket_flow, related_name='next')

class tickets(base):
    caption = models.CharField(_('caption'), max_length=255)
    description = models.TextField(_('description'))
    type = models.ForeignKey(ticket_type, verbose_name=_('type'), null=True)
    priority = models.ForeignKey(ticket_priority, verbose_name=_('priority'), null=True)
    customer = models.ForeignKey(organisation, verbose_name=_('organisation'))
    assigned = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('assigned'), related_name='+', null=True, blank=True)
    resolution = models.ForeignKey(ticket_resolution, verbose_name=_('resolution'), null=True)
    closed = models.BooleanField(_('closed'), default=False)
    state = models.ForeignKey(ticket_flow, verbose_name=_('state'), null=True, blank=True, default=get_flow_start)
    close_date = models.DateTimeField(_('close date'), null=True)
    last_action_date = models.DateTimeField(_('last action'), null=True)
    keep_it_simple = models.BooleanField(default=True)
    uuid = models.CharField(max_length=255, null=False, blank=False)
    hasAttachments = models.BooleanField(_('has attachments'), default=False)
    hasComments = models.BooleanField(_('has comments'), default=False)

    def save(self, *args, **kwargs):
        self.last_action_date = timezone.now()
        if not self.uuid:
            self.uuid = uuid.uuid4()
        tickets_participants.objects.filter(ticket=self).update(seen=False)
        tickets_ignorants.objects.filter(ticket=self).delete()
        super(tickets, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return "/tickets/view/%i/" % self.id

class tickets_participants(models.Model):
    ticket = models.ForeignKey(tickets)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')
    seen = models.BooleanField(default=False)

class tickets_ignorants(models.Model):
    ticket = models.ForeignKey(tickets)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')

class tickets_comments(base):
    ticket = models.ForeignKey(tickets)
    comment = models.TextField()
    action = models.SmallIntegerField(default=0)  # 0 = nothing, 1 = close, 2 = reopen, 3 = ref, 6 = comment, 7 = reassign

    def save(self, *args, **kwargs):
        super(tickets_comments, self).save(*args, **kwargs)

        tickets.objects.filter(id=self.ticket_id).update(last_action_date=self.c_date, hasComments=tickets_comments.objects.filter(ticket=self.ticket_id, active_record=True).count() > 0)

class tickets_files(base):
    ticket = models.ForeignKey(tickets)
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    public = models.BooleanField(default=False)
    checksum = models.CharField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        super(tickets_files, self).save(*args, **kwargs)

        tickets.objects.filter(id=self.ticket_id).update(last_action_date=self.c_date, hasAttachments=tickets_files.objects.filter(ticket=self.ticket_id, active_record=True).count() > 0)

    class Meta:
        ordering = ['c_date']

class tickets_reports(base):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    search = models.TextField()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(tickets_reports, self).save(*args, **kwargs)

        from djradicale.models import DBProperties
        text = {'tag': 'VCALENDAR', 'D:displayname': self.name}
        props, created = DBProperties.objects.get_or_create(path='%s/%s.ics' % (kwargs['user'].username, self.slug), defaults={'text': json.dumps(text)})

    def delete(self, *args, **kwargs):
        from djradicale.models import DBProperties

        path = '%s/%s.ics' % (kwargs['user'].username, self.slug)
        DBProperties.objects.filter(path=path).delete()

        super(tickets_reports, self).delete(*args, **kwargs)

class tickets_history(base):
    ticket = models.ForeignKey(tickets)
    old = models.TextField()
    new = models.TextField()
    action = models.SmallIntegerField(default=0)  # 0 = nothing, 1 = close, 2 = reopen, 3 = ref, 4 = ticket changed, 5 = file added, 6 = comment added, 7 = reassign, 8 = del file, 9 = todo

class boards(base):
    name = models.CharField(max_length=255)
    columns = models.TextField()

    def __unicode__(self):
        return self.name

class docs(base):
    caption = models.CharField(max_length=255)
    text = MarkdownxField()

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/docs/view/%i/" % self.id
