# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('request_profiler', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profilingrecord',
            name='http_referer',
            field=models.CharField(default='', max_length=400),
            preserve_default=True,
        ),
    ]
