# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfilingRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('session_key', models.CharField(max_length=40, blank=True)),
                ('start_ts', models.DateTimeField(verbose_name=b'Request started at')),
                ('end_ts', models.DateTimeField(verbose_name=b'Request ended at')),
                ('duration', models.FloatField(verbose_name=b'Request duration (sec)')),
                ('http_method', models.CharField(max_length=10)),
                ('request_uri', models.URLField(verbose_name=b'Request path')),
                ('remote_addr', models.CharField(max_length=100)),
                ('http_user_agent', models.CharField(max_length=400)),
                ('view_func_name', models.CharField(max_length=100, verbose_name=b'View function')),
                ('response_status_code', models.IntegerField()),
                ('response_content_length', models.IntegerField()),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RuleSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enabled', models.BooleanField(default=True, db_index=True)),
                ('uri_regex', models.CharField(default=b'', help_text='Regex used to filter by request URI.', max_length=100, verbose_name='Request path regex', blank=True)),
                ('user_filter_type', models.IntegerField(default=0, help_text='Filter requests by type of user.', verbose_name='User type filter', choices=[(0, b'All users (inc. None)'), (1, b'Authenticated users only'), (2, b'Users in a named group')])),
                ('user_group_filter', models.CharField(default=b'', help_text='Group used to filter users.', max_length=100, verbose_name='User group filter', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
