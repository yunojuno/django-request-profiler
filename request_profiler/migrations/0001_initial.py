# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'RuleSet'
        db.create_table(u'request_profiler_ruleset', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True, db_index=True)),
            ('uri_regex', self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True)),
            ('user_group_filter', self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True)),
            ('include_anonymous', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'request_profiler', ['RuleSet'])

        # Adding model 'ProfilingRecord'
        db.create_table(u'request_profiler_profilingrecord', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('session_key', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
            ('start_ts', self.gf('django.db.models.fields.DateTimeField')()),
            ('end_ts', self.gf('django.db.models.fields.DateTimeField')()),
            ('duration', self.gf('django.db.models.fields.FloatField')()),
            ('http_method', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('request_uri', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('remote_addr', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('http_user_agent', self.gf('django.db.models.fields.CharField')(max_length=400)),
            ('view_func_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('response_status_code', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'request_profiler', ['ProfilingRecord'])


    def backwards(self, orm):
        # Deleting model 'RuleSet'
        db.delete_table(u'request_profiler_ruleset')

        # Deleting model 'ProfilingRecord'
        db.delete_table(u'request_profiler_profilingrecord')


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
        u'request_profiler.profilingrecord': {
            'Meta': {'object_name': 'ProfilingRecord'},
            'duration': ('django.db.models.fields.FloatField', [], {}),
            'end_ts': ('django.db.models.fields.DateTimeField', [], {}),
            'http_method': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'http_user_agent': ('django.db.models.fields.CharField', [], {'max_length': '400'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'remote_addr': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'request_uri': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'response_status_code': ('django.db.models.fields.IntegerField', [], {}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'start_ts': ('django.db.models.fields.DateTimeField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'view_func_name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'request_profiler.ruleset': {
            'Meta': {'object_name': 'RuleSet'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'uri_regex': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'user_group_filter': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'})
        }
    }

    complete_apps = ['request_profiler']