# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
import django
from django.db import models, IntegrityError
from django.db import transaction
import random

class Migration(DataMigration):

    def forwards(self, orm):
        for cat in orm.Category.objects.all():
            ## Attempt to set some possibly-appropriate unique name into the
            ## category name in each case.
            label = cat.label
            names = [  # names to try (until it gets unique.
                ''.join(v[0] for v in label.lower().split()),
                ''.join(v[:2] for v in label.lower().split()),
                label.lower().replace(' ', '_'),
                label.lower(),
                label,  # the label should be unique always, riiight?
                "%s_%x" % (label, random.getrandbits(16))]  # but no, play safe.
            for name in names:
                with transaction.commit_on_success():
                    try:
                        cat.name = name
                        cat.save()
                    except IntegrityError:
                        pass  # will try the next
                    else:
                        break
            # With any luck at all, the category should have a non-null
            # unique name by this point (otherwise the server admin should
            # shoot own foot literally as well).
        # ... forwards migrated.

    def backwards(self, orm):
        pass  ## Nothing to do here: category names will not matter.


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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '16', 'unique': 'True', 'null': 'True'}),
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
