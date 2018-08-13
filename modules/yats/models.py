# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.utils import timezone

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

# user profiles
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True)

    organisation = models.ForeignKey('organisation', null=True)

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
    c_date = models.DateTimeField(default=timezone.now)
    c_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')
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
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=255, default='transparent')

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
    caption = models.CharField(max_length=255)
    description = models.TextField()
    type = models.ForeignKey(ticket_type, null=True)
    priority = models.ForeignKey(ticket_priority, null=True)
    customer = models.ForeignKey(organisation)
    assigned = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', null=True, blank=True)
    resolution = models.ForeignKey(ticket_resolution, null=True)
    closed = models.BooleanField(default=False)
    state = models.ForeignKey(ticket_flow, null=True, blank=True, default=get_flow_start)
    close_date = models.DateTimeField(null=True)
    last_action_date = models.DateTimeField(null=True)
    keep_it_simple = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.last_action_date = timezone.now()
        tickets_participants.objects.filter(ticket=self).update(seen=False)
        super(tickets, self).save(*args, **kwargs)

class tickets_participants(models.Model):
    ticket = models.ForeignKey(tickets)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')
    seen = models.BooleanField(default=False)

class tickets_comments(base):
    ticket = models.ForeignKey(tickets)
    comment = models.TextField()
    action = models.SmallIntegerField(default=0)  # 0 = nothing, 1 = close, 2 = reopen, 3 = ref, 6 = comment, 7 = reassign

    def save(self, *args, **kwargs):
        super(tickets_comments, self).save(*args, **kwargs)

        tickets.objects.filter(id=self.ticket_id).update(last_action_date=self.c_date)

class tickets_files(base):
    ticket = models.ForeignKey(tickets)
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    public = models.BooleanField(default=False)
    checksum = models.CharField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        super(tickets_files, self).save(*args, **kwargs)

        tickets.objects.filter(id=self.ticket_id).update(last_action_date=self.c_date)

    class Meta:
        ordering = ['c_date']

class tickets_reports(base):
    name = models.CharField(max_length=255)
    search = models.TextField()

class tickets_history(base):
    ticket = models.ForeignKey(tickets)
    old = models.TextField()
    new = models.TextField()
    action = models.SmallIntegerField(default=0)  # 0 = nothing, 1 = close, 2 = reopen, 3 = ref, 4 = ticket changed, 5 = file added, 6 = comment added, 7 = reassign, 8 = del file

class boards(base):
    name = models.CharField(max_length=255)
    columns = models.TextField()

    def __unicode__(self):
        return self.name
