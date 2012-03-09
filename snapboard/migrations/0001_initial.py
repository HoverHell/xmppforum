# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Group'
        db.create_table('snapboard_group', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=36)),
        ))
        db.send_create_signal('snapboard', ['Group'])

        # Adding M2M table for field users on 'Group'
        db.create_table('snapboard_group_users', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('group', models.ForeignKey(orm['snapboard.group'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('snapboard_group_users', ['group_id', 'user_id'])

        # Adding M2M table for field admins on 'Group'
        db.create_table('snapboard_group_admins', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('group', models.ForeignKey(orm['snapboard.group'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('snapboard_group_admins', ['group_id', 'user_id'])

        # Adding model 'Invitation'
        db.create_table('snapboard_invitation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sb_invitation_set', to=orm['snapboard.Group'])),
            ('sent_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sb_sent_invitation_set', to=orm['auth.User'])),
            ('sent_to', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sb_received_invitation_set', to=orm['auth.User'])),
            ('sent_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('response_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('accepted', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
        ))
        db.send_create_signal('snapboard', ['Invitation'])

        # Adding model 'Category'
        db.create_table('snapboard_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('view_perms', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
            ('read_perms', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
            ('post_perms', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=2)),
            ('new_thread_perms', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=2)),
            ('view_group', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='can_view_category_set', null=True, to=orm['snapboard.Group'])),
            ('read_group', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='can_read_category_set', null=True, to=orm['snapboard.Group'])),
            ('post_group', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='can_post_category_set', null=True, to=orm['snapboard.Group'])),
            ('new_thread_group', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='can_create_thread_category_set', null=True, to=orm['snapboard.Group'])),
        ))
        db.send_create_signal('snapboard', ['Category'])

        # Adding model 'Moderator'
        db.create_table('snapboard_moderator', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['snapboard.Category'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sb_moderator_set', to=orm['auth.User'])),
        ))
        db.send_create_signal('snapboard', ['Moderator'])

        # Adding model 'Thread'
        db.create_table('snapboard_thread', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=160)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['snapboard.Category'])),
            ('closed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('csticky', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('gsticky', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('snapboard', ['Thread'])

        # Adding model 'Post_revisions'
        db.create_table('snapboard_post_revisions', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['auth.User'], blank=True)),
            ('thread', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['snapboard.Thread'])),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('texth', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True, blank=True)),
            ('previous', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='prev', null=True, to=orm['snapboard.Post_revisions'])),
        ))
        db.send_create_signal('snapboard', ['Post_revisions'])

        # Adding model 'Post'
        db.create_table('snapboard_post', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('path', self.gf('django.db.models.fields.CharField')(unique=True, max_length=90000)),
            ('depth', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('numchild', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['auth.User'], blank=True)),
            ('thread', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['snapboard.Thread'])),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('texth', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True, blank=True)),
            ('censor', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('freespeech', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('previous', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='prev_last', null=True, to=orm['snapboard.Post_revisions'])),
            ('tlid', self.gf('django.db.models.fields.IntegerField')(default=None, null=True, blank=True)),
        ))
        db.send_create_signal('snapboard', ['Post'])

        # Adding unique constraint on 'Post', fields ['thread', 'tlid']
        db.create_unique('snapboard_post', ['thread_id', 'tlid'])

        # Adding model 'AbuseReport'
        db.create_table('snapboard_abusereport', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('post', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sb_abusereport_set', to=orm['snapboard.Post'])),
            ('submitter', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sb_abusereport_set', to=orm['auth.User'])),
        ))
        db.send_create_signal('snapboard', ['AbuseReport'])

        # Adding unique constraint on 'AbuseReport', fields ['post', 'submitter']
        db.create_unique('snapboard_abusereport', ['post_id', 'submitter_id'])

        # Adding model 'WatchList'
        db.create_table('snapboard_watchlist', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sb_watchlist', to=orm['auth.User'])),
            ('post', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sb_watchinglist', to=orm['snapboard.Post'])),
            ('xmppresource', self.gf('django.db.models.fields.CharField')(max_length=80, blank=True)),
        ))
        db.send_create_signal('snapboard', ['WatchList'])

        # Adding model 'UserSettings'
        db.create_table('snapboard_usersettings', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='sb_usersettings', unique=True, to=orm['auth.User'])),
            ('ppp', self.gf('django.db.models.fields.IntegerField')(default=20)),
            ('tpp', self.gf('django.db.models.fields.IntegerField')(default=20)),
            ('reverse_posts', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('snapboard', ['UserSettings'])

        # Adding M2M table for field frontpage_filters on 'UserSettings'
        db.create_table('snapboard_usersettings_frontpage_filters', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('usersettings', models.ForeignKey(orm['snapboard.usersettings'], null=False)),
            ('category', models.ForeignKey(orm['snapboard.category'], null=False))
        ))
        db.create_unique('snapboard_usersettings_frontpage_filters', ['usersettings_id', 'category_id'])

        # Adding model 'UserBan'
        db.create_table('snapboard_userban', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sb_userban_set', unique=True, to=orm['auth.User'])),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('snapboard', ['UserBan'])

        # Adding model 'IPBan'
        db.create_table('snapboard_ipban', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('address', self.gf('django.db.models.fields.IPAddressField')(unique=True, max_length=15, db_index=True)),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('snapboard', ['IPBan'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'AbuseReport', fields ['post', 'submitter']
        db.delete_unique('snapboard_abusereport', ['post_id', 'submitter_id'])

        # Removing unique constraint on 'Post', fields ['thread', 'tlid']
        db.delete_unique('snapboard_post', ['thread_id', 'tlid'])

        # Deleting model 'Group'
        db.delete_table('snapboard_group')

        # Removing M2M table for field users on 'Group'
        db.delete_table('snapboard_group_users')

        # Removing M2M table for field admins on 'Group'
        db.delete_table('snapboard_group_admins')

        # Deleting model 'Invitation'
        db.delete_table('snapboard_invitation')

        # Deleting model 'Category'
        db.delete_table('snapboard_category')

        # Deleting model 'Moderator'
        db.delete_table('snapboard_moderator')

        # Deleting model 'Thread'
        db.delete_table('snapboard_thread')

        # Deleting model 'Post_revisions'
        db.delete_table('snapboard_post_revisions')

        # Deleting model 'Post'
        db.delete_table('snapboard_post')

        # Deleting model 'AbuseReport'
        db.delete_table('snapboard_abusereport')

        # Deleting model 'WatchList'
        db.delete_table('snapboard_watchlist')

        # Deleting model 'UserSettings'
        db.delete_table('snapboard_usersettings')

        # Removing M2M table for field frontpage_filters on 'UserSettings'
        db.delete_table('snapboard_usersettings_frontpage_filters')

        # Deleting model 'UserBan'
        db.delete_table('snapboard_userban')

        # Deleting model 'IPBan'
        db.delete_table('snapboard_ipban')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'snapboard.abusereport': {
            'Meta': {'unique_together': "(('post', 'submitter'),)", 'object_name': 'AbuseReport'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sb_abusereport_set'", 'to': "orm['snapboard.Post']"}),
            'submitter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sb_abusereport_set'", 'to': "orm['auth.User']"})
        },
        'snapboard.category': {
            'Meta': {'object_name': 'Category'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'new_thread_group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'can_create_thread_category_set'", 'null': 'True', 'to': "orm['snapboard.Group']"}),
            'new_thread_perms': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '2'}),
            'post_group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'can_post_category_set'", 'null': 'True', 'to': "orm['snapboard.Group']"}),
            'post_perms': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '2'}),
            'read_group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'can_read_category_set'", 'null': 'True', 'to': "orm['snapboard.Group']"}),
            'read_perms': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'view_group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'can_view_category_set'", 'null': 'True', 'to': "orm['snapboard.Group']"}),
            'view_perms': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'})
        },
        'snapboard.group': {
            'Meta': {'object_name': 'Group'},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'sb_admin_of_group_set'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '36'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'sb_member_of_group_set'", 'symmetrical': 'False', 'to': "orm['auth.User']"})
        },
        'snapboard.invitation': {
            'Meta': {'object_name': 'Invitation'},
            'accepted': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sb_invitation_set'", 'to': "orm['snapboard.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'response_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'sent_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sb_sent_invitation_set'", 'to': "orm['auth.User']"}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'sent_to': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sb_received_invitation_set'", 'to': "orm['auth.User']"})
        },
        'snapboard.ipban': {
            'Meta': {'object_name': 'IPBan'},
            'address': ('django.db.models.fields.IPAddressField', [], {'unique': 'True', 'max_length': '15', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'snapboard.moderator': {
            'Meta': {'object_name': 'Moderator'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['snapboard.Category']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sb_moderator_set'", 'to': "orm['auth.User']"})
        },
        'snapboard.post': {
            'Meta': {'unique_together': "(('thread', 'tlid'),)", 'object_name': 'Post'},
            'censor': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'depth': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'freespeech': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'numchild': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '90000'}),
            'previous': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prev_last'", 'null': 'True', 'to': "orm['snapboard.Post_revisions']"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'texth': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'thread': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['snapboard.Thread']"}),
            'tlid': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['auth.User']", 'blank': 'True'})
        },
        'snapboard.post_revisions': {
            'Meta': {'object_name': 'Post_revisions'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'previous': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prev'", 'null': 'True', 'to': "orm['snapboard.Post_revisions']"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'texth': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'thread': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['snapboard.Thread']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['auth.User']", 'blank': 'True'})
        },
        'snapboard.thread': {
            'Meta': {'object_name': 'Thread'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['snapboard.Category']"}),
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'csticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'gsticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '160'})
        },
        'snapboard.userban': {
            'Meta': {'object_name': 'UserBan'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sb_userban_set'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'snapboard.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'frontpage_filters': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['snapboard.Category']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ppp': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'reverse_posts': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'tpp': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'sb_usersettings'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'snapboard.watchlist': {
            'Meta': {'object_name': 'WatchList'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sb_watchinglist'", 'to': "orm['snapboard.Post']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sb_watchlist'", 'to': "orm['auth.User']"}),
            'xmppresource': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        }
    }

    complete_apps = ['snapboard']
