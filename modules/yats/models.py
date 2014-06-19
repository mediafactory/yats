# -*- coding: utf-8 -*- 
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.db.models.signals import post_save

import datetime

YES_NO_DONT_KNOW = (
    (None, '---------'),
    (True, _('yes')),
    (False, _('no')),
)

# user profiles
class UserProfile(models.Model):
    user = models.OneToOneField(User, null=True)
    
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
        UserProfile.objects.get_or_create(user=instance)

post_save.connect(create_user_profile, sender=User)

class base(models.Model):
    active_record = models.BooleanField(default=True)

    # creation
    c_date = models.DateTimeField(default=datetime.datetime.now)
    c_user = models.ForeignKey(User, related_name='+')
    # update
    u_date = models.DateTimeField(default=datetime.datetime.now)
    u_user = models.ForeignKey(User, related_name='+')
    # deletion'
    d_date = models.DateTimeField(null=True)
    d_user = models.ForeignKey(User, related_name='+', null=True)

    def save(self, *args, **kwargs):
        if not 'user' in kwargs and not 'user_id' in kwargs:
            raise Exception('missing user')
        if 'user' in kwargs:
            self.u_user = kwargs['user']
            if not self.pk:
                self.c_user = kwargs['user']
            del kwargs['user']
        if 'user_id' in kwargs:
            self.u_user_id = kwargs['user_id']
            if not self.pk:
                self.c_user_id = kwargs['user_id']
            del kwargs['user_id']
        super(base, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not 'user' in kwargs and not 'user_id' in kwargs:
            raise Exception('missing user for delete')
        self.d_date = datetime.datetime.now()
        if 'user' in kwargs:
            self.d_user = kwargs['user']
        if 'user_id' in kwargs:
            self.d_user_id = kwargs['user_id']
        self.active = False
        self.save()
        
    class Meta():
        abstract = True
        
class organisation(base):
    name = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.name

class ticket_type(base):
    name = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.name

class ticket_priority(base):
    name = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.name
    
class ticket_resolution(base):
    name = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.name

class tickets(base):
    caption = models.CharField(max_length=255)
    description = models.TextField()
    type = models.ForeignKey(ticket_type, null=True)
    priority = models.ForeignKey(ticket_priority, null=True)
    customer = models.ForeignKey(organisation)
    assigned = models.ForeignKey(User, related_name='+', null=True, blank=True)
    resolution = models.ForeignKey(ticket_resolution, null=True)
    closed = models.BooleanField(default=False)
    
class tickets_participants(models.Model):
    ticket = models.ForeignKey(tickets)
    user = models.ForeignKey(User, related_name='+')

class tickets_comments(base):
    ticket = models.ForeignKey(tickets)
    comment = models.TextField()
    action = models.SmallIntegerField(default=0) # 0 = nothing, 1 = close, 2 = reopen, 3 = ref

class tickets_files(base):
    ticket = models.ForeignKey(tickets)
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    public = models.BooleanField(default=False)
    
class tickets_reports(base):
    name = models.CharField(max_length=255)
    search = models.TextField()
    