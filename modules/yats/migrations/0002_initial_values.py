# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from yats.models import ticket_priority, ticket_resolution, ticket_type

class Migration(DataMigration):

    def forwards(self, orm):
        user = User.objects.all()[0]
        
        ticket_priority(name=_('trivial')).save(user=user)
        ticket_priority(name=_('minor')).save(user=user)
        ticket_priority(name=_('major')).save(user=user)
        ticket_priority(name=_('critical')).save(user=user)
        ticket_priority(name=_('blocker')).save(user=user)
        
        ticket_resolution(name=_('dupplicate')).save(user=user)
        ticket_resolution(name=_('fixed')).save(user=user)
        ticket_resolution(name=_('won\'t fix')).save(user=user)
        ticket_resolution(name=_('invalid')).save(user=user)
        
        ticket_type(name=_('undefined')).save(user=user)
        ticket_type(name=_('bug')).save(user=user)
        ticket_type(name=_('feature request')).save(user=user)
        ticket_type(name=_('enhancement')).save(user=user)

    def backwards(self, orm):
        "Write your backwards methods here."

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'yats.organisation': {
            'Meta': {'object_name': 'organisation'},
            'active_record': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'c_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'c_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"}),
            'd_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'd_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'u_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'u_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"})
        },
        u'yats.ticket_priority': {
            'Meta': {'object_name': 'ticket_priority'},
            'active_record': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'c_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'c_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"}),
            'd_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'd_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'u_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'u_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"})
        },
        u'yats.ticket_resolution': {
            'Meta': {'object_name': 'ticket_resolution'},
            'active_record': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'c_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'c_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"}),
            'd_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'd_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'u_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'u_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"})
        },
        u'yats.ticket_type': {
            'Meta': {'object_name': 'ticket_type'},
            'active_record': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'c_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'c_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"}),
            'd_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'd_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'u_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'u_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"})
        },
        u'yats.tickets': {
            'Meta': {'object_name': 'tickets'},
            'active_record': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'assigned': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'c_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'c_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['yats.organisation']"}),
            'd_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'd_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'priority': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['yats.ticket_priority']", 'null': 'True'}),
            'resolution': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['yats.ticket_resolution']", 'null': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['yats.ticket_type']", 'null': 'True'}),
            'u_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'u_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"})
        },
        u'yats.tickets_comments': {
            'Meta': {'object_name': 'tickets_comments'},
            'active_record': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'c_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'c_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"}),
            'comment': ('django.db.models.fields.TextField', [], {}),
            'd_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'd_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ticket': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['yats.tickets']"}),
            'u_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'u_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"})
        },
        u'yats.tickets_files': {
            'Meta': {'object_name': 'tickets_files'},
            'active_record': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'c_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'c_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"}),
            'content_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'd_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'd_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'size': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'ticket': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['yats.tickets']"}),
            'u_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'u_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"})
        },
        u'yats.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organisation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['yats.organisation']", 'null': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'null': 'True'})
        }
    }

    complete_apps = ['yats']
    symmetrical = True
