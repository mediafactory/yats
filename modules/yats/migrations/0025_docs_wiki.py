# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2019-10-04 09:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('yats', '0024_tickets_comments_edited_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='docs',
            name='wiki',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]