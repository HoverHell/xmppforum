import logging
from datetime import datetime
import time

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import models, connection
from django.db.models import signals, Q
from django.dispatch import dispatcher
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

from django.http import Http404  # for get_post_or_404

import re

from treebeard import mp_tree

from xmppface.xmppstuff import send_notifications

# Monkey-patching no-copying way:
def get_rly_annotated_list(self):
    return super(mp_tree.MP_Node, self).get_annotated_list(self)

## Most likely this stuff should be moved into the Post manager.
def get_adv_annotated_list(self=None, qs=None):
    """ Gets an annotated list from a tree branch, adding some advanced info
    along the way.  Can be used on a queryset (or a list) as a function."""
    result, info = [], {}
    start_depth, prev_depth, ddepth, rdepth = (None, -1, None, None)
    prev_siblings = []  # list of possible previous (or last) siblings

    if qs is None:
        qs = self.get_tree(self)

    for node in qs:
        depth = node.get_depth()
        if start_depth is None:
            start_depth = depth
        ddepth = depth - prev_depth  # depth difference (step)
        rdepth = depth - start_depth  # relative depth.
        open = (ddepth > 0)  # (depth > prev_depth)
        if open:
            # Ensure we have elements up to necessary depth.
            if len(prev_siblings) < rdepth + 1:
                prev_siblings.append(None)
        # shouldn't be needed, but can:
        #prev_siblings += [None] * (rdepth - len(prev_siblings) + 1)

        if prev_siblings[rdepth] == None:  # it's first here.
            prev_siblings[rdepth] = node
        else:  # ... that one wasn't last.
            prev_siblings[rdepth].next_sibling = node
            prev_siblings[rdepth] = node

        # Slightly inappropriate, but might be better than to use info.
        node.next_sibling = None  # might be reassigned later.

        if ddepth < 0:  # depth < prev_depth:
            info['close'] = range(0, -ddepth)
            # previous *deeper* nodes are not possible siblings.
            for v in range(prev_depth - start_depth, rdepth, -1):
                prev_siblings[v] = None
        # `is_last_sibling = not next_sibling`
        info = {'open': open, 'close': [], 'rdepth': rdepth}
        node.treeinfo = info
        result.append((node, info,))
        prev_depth = depth
    if start_depth > 0:
        info['close'] = range(0, prev_depth - start_depth + 1)
    return result


def get_flathelper_list(self=None, qs=None):
    """ Adds few more information to annotated list (retreived from
    specified node) to display "straight" branches as flat.

    Can be used on a queryset as a function.

    Can be made obsolete in the current form.  """
    # hack-helper for extra data. Will probably be removed later.
    if qs is None:
        from django.db.models import Count
        qs = self.get_tree(self).annotate(
          abuse=Count('sb_abusereport_set')).select_related(depth=2)[1:]
    annotated = get_adv_annotated_list(self, qs)
    #prev_node, prev_info = annotated[0]
    def is_alone(n, i):
        """ "node is the only direct child" (no siblings). depends on the
        data computed with later nodes in get_adv_anno... """
        return (getattr(n, "next_sibling", False) is None and i.get('open'))
    # Expecting to change mutable node and info in the list.
    # ! TODO: This could probably be one as a function on the model and
    #  called from the rendering.
    for node, info in annotated:  # don't process the root node.
        if is_alone(node, info):
            node.is_flat = True
            # node.is_flat = lambda self: is_alone(self, self.info)
    return annotated

# Provide many various additions.
# ? XXX: put them into Post model after all?
mp_tree.MP_Node.get_annotated_list = get_rly_annotated_list
mp_tree.MP_Node.get_adv_annotated_list = get_adv_annotated_list
mp_tree.MP_Node.get_flathelper_list = get_flathelper_list


from snapboard import managers
from snapboard.middleware import threadlocals

__all__ = [
    'SNAP_PREFIX', 'SNAP_MEDIA_PREFIX', 'SNAP_POST_FILTER',
    'NOBODY', 'ALL', 'USERS', 'CUSTOM', 'PERM_CHOICES', 'PERM_CHOICES_RESTRICTED',
    'PermissionError', 'is_user_banned', 'is_ip_banned',
    'Category', 'Invitation', 'Group', 'Thread', 'Post_revisions', 'Post', 'Moderator',
    'WatchList', 'AbuseReport', 'UserSettings', 'IPBan', 'UserBan',
    ]

_log = logging.getLogger('snapboard.models')

SNAP_PREFIX = getattr(settings, 'SNAP_PREFIX', '')
SNAP_MEDIA_PREFIX = getattr(settings, 'SNAP_MEDIA_PREFIX',
  getattr(settings, 'MEDIA_URL', ''))
SNAP_POST_FILTER = getattr(settings, 'SNAP_POST_FILTER', 'bbcode').lower()


(NOBODY, ALL, USERS, CUSTOM) = range(4)

PERM_CHOICES = (
    (NOBODY, _('Nobody')),
    (ALL, _('All')),
    (USERS, _('Users')),
    (CUSTOM, _('Custom')),
)

PERM_CHOICES_RESTRICTED = (
    (NOBODY, _('Nobody')),
    (ALL, _('All')),
    (USERS, _('Users')),
    (CUSTOM, _('Custom')),
)


class PermissionError(PermissionDenied):
    '''
    Raised when a user tries to perform a forbidden operation, as per the
    permissions defined by Category objects.
    '''
    pass


def is_user_banned(user):
    return user.id in settings.SNAP_BANNED_USERS


def is_ip_banned(ip):
    return ip in settings.SNAP_BANNED_IPS


class Group(models.Model):
    '''
    User-administerable group, be used to assign permissions to possibly
    several users.

    Administrators of the group need to be explicitely added to the users
    list to be considered members.
    '''

    name = models.CharField(_('name'), max_length=36)
    users = models.ManyToManyField(User, verbose_name=_('users'), related_name='sb_member_of_group_set')
    admins = models.ManyToManyField(User, verbose_name=_('admins'), related_name='sb_admin_of_group_set')

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')

    def __unicode__(self):
        return _('Group "%s"') % self.name

    def has_user(self, user):
        return self.users.filter(pk=user.pk).count() != 0

    def has_admin(self, user):
        return self.admins.filter(pk=user.pk).count() != 0


class Invitation(models.Model):
    '''
    Group admins create invitations for users to join their group.

    Staff with site admin access can assign users to groups without
    restriction.
    '''

    group = models.ForeignKey(Group, verbose_name=_('group'), related_name='sb_invitation_set')
    sent_by = models.ForeignKey(User, verbose_name=_('sent by'), related_name='sb_sent_invitation_set')
    sent_to = models.ForeignKey(User, verbose_name=_('sent to'), related_name='sb_received_invitation_set')
    sent_date = models.DateTimeField(_('sent date'), auto_now_add=True)
    response_date = models.DateTimeField(_('response date'), blank=True, null=True)
    accepted = models.NullBooleanField(_('accepted'), blank=True, null=True)

    class Meta:
        verbose_name = _('invitation')
        verbose_name_plural = _('invitations')

    def __unicode__(self):
        return _('Invitation for "%(group)s" sent by %(sent_by)s to %(sent_to)s.') % {
                'group': self.group.name,
                'sent_by': self.sent_by,
                'sent_to': self.sent_to }

    def notify_received(instance, **kwargs):
        '''
        Notifies of new invitations.
        '''
        if instance.accepted is None:
            send_notifications(
                [instance.sent_to],
                'group_invitation_received',
                {'invitation': instance})
    notify_received = staticmethod(notify_received)

    def notify_cancelled(instance, **kwargs):
        '''
        Notifies of cancelled invitations.
        '''
        if instance.accepted is None:
            send_notifications(
                [instance.sent_to],
                'group_invitation_cancelled',
                {'invitation': instance})
    notify_cancelled = staticmethod(notify_cancelled)

signals.post_save.connect(Invitation.notify_received, sender=Invitation)
signals.pre_delete.connect(Invitation.notify_cancelled, sender=Invitation)


class Category(models.Model):

    label = models.CharField(max_length=32, verbose_name=_('label'))
    description = models.CharField(max_length=255, blank=True,
      verbose_name=_('description'))

    view_perms = models.PositiveSmallIntegerField(_('view permission'),
        choices=PERM_CHOICES, default=ALL,
        help_text=_('Limits the category\'s visibility.'))
    read_perms = models.PositiveSmallIntegerField(_('read permission'),
        choices=PERM_CHOICES, help_text=_('Limits the ability to read the '\
        'category\'s contents.'), default=ALL)
    post_perms = models.PositiveSmallIntegerField(_('post permission'),
        choices=PERM_CHOICES_RESTRICTED, help_text=_('Limits the ability to '\
        'post in the category.'), default=USERS)
    new_thread_perms = models.PositiveSmallIntegerField(
        _('create thread permission'), choices=PERM_CHOICES_RESTRICTED,
        help_text=_('Limits the ability to create new threads in the '\
        'category. Only users with permission to post can create new threads,'\
        'unless a group is specified.'), default=USERS)

    view_group = models.ForeignKey(Group, verbose_name=_('view group'),
        blank=True, null=True, related_name='can_view_category_set')
    read_group = models.ForeignKey(Group, verbose_name=_('read group'),
        blank=True, null=True, related_name='can_read_category_set')
    post_group = models.ForeignKey(Group, verbose_name=_('post group'),
        blank=True, null=True, related_name='can_post_category_set')
    new_thread_group = models.ForeignKey(Group, verbose_name=_('create thread group'),
        blank=True, null=True, related_name='can_create_thread_category_set')

    objects = managers.CategoryManager()    # adds thread_count

    def __unicode__(self):
        return self.label

    def moderators(self):
        mods = Moderator.objects.filter(category=self.id)
        if mods.count() > 0:
            return ', '.join([m.user.username for m in mods])
        else:
            return None

    def can_view(self, user):
        flag = False
        if self.view_perms == ALL:
            flag = True
        elif self.view_perms == USERS:
            flag = user.is_authenticated()
        elif self.view_perms == CUSTOM:
            flag = user.is_superuser or (user.is_authenticated() and self.view_group.has_user(user))
        return flag

    def can_read(self, user):
        flag = False
        if self.read_perms == ALL:
            flag = True
        elif self.read_perms == USERS:
            flag = user.is_authenticated()
        elif self.read_perms == CUSTOM:
            flag = user.is_superuser or (user.is_authenticated() and self.read_group.has_user(user))
        return flag

    def can_post(self, user):
        flag = False
        if self.post_perms == ALL:
            flag = True # Anonymous supported.
        elif self.post_perms == USERS:
            flag = user.is_authenticated() and not getattr(user, "really_anonymous", False)
        elif self.post_perms == CUSTOM:
            flag = user.is_superuser or (user.is_authenticated() and self.post_group.has_user(user))
        return flag

    def can_create_thread(self, user):
        flag = False
        if self.new_thread_perms == ALL:
            flag = True # Anonymous supported.
        if self.new_thread_perms == USERS:
            flag = user.is_authenticated() and not getattr(user, "really_anonymous", False)
        elif self.new_thread_perms == CUSTOM:
            flag = user.is_superuser or (user.is_authenticated() and self.new_thread_group.has_user(user))
        return flag

    class Meta:
        verbose_name = _('category')
        verbose_name_plural = _('categories')


class Moderator(models.Model):
    category = models.ForeignKey(Category, verbose_name=_('category'))
    user = models.ForeignKey(User, verbose_name=_('user'), related_name='sb_moderator_set')

    def __unicode__(self):
        return u'%s' % (self.user.username,)

    class Meta:
        verbose_name = _('moderator')
        verbose_name_plural = _('moderators')


class Thread(models.Model):
    subject = models.CharField(max_length=160, verbose_name=_('subject'))
    category = models.ForeignKey(Category, verbose_name=_('category'))

    closed = models.BooleanField(default=False, verbose_name=_('closed'))

    # Category sticky - will show up at the top of category listings.
    csticky = models.BooleanField(default=False, verbose_name=_('category sticky'))

    # Global sticky - will show up at the top of home listing.
    gsticky = models.BooleanField(default=False, verbose_name=_('global sticky'))

    objects = models.Manager()  # needs to be explicit due to below
    view_manager = managers.ThreadManager()

    def __unicode__(self):
        return self.subject

    def get_url(self):
        return reverse('snapboard_thread', args=(self.id,))

    class Meta:
        verbose_name = _('thread')
        verbose_name_plural = _('threads')

    def count_posts(self, user, before=None):
        '''
        Returns the number of visible posts in the thread or, if ``before`` is
        a Post object, the number of visible posts in the thread that are
        older.
        '''
        # This partly does what Thread.objects.get_query_set() does, except
        # it takes into account the user and therefore knows what posts
        # are visible to him
        qs = self.post_set.filter(revision=None)
        if user.is_authenticated():
            qs = qs.filter(Q(user=user))
        if not getattr(user, 'is_staff', False):
            qs = qs.exclude(censor=True)
        if before:
            qs.filter(date__lt=before.date)
        return qs.count()


class Post_base(models.Model):
    """ An abstract class for two related models: post tree and old post
    revisions.  """
    # blank=True to get admin to work when the user field is missing
    user = models.ForeignKey(User, editable=False, blank=True, default=None,
      verbose_name=_('user'))
    ## Cannot really use related_name since there's two models that use this
    ## same field.
    #, related_name='sb_created_posts_set')
    thread = models.ForeignKey(Thread, verbose_name=_('thread'))
    text = models.TextField(verbose_name=_('text'))
    texth = models.TextField(blank=True, # null=True,
      verbose_name=_('cached rendered text'))
    date = models.DateTimeField(editable=False, auto_now_add=True,
      verbose_name=_('date'))
    ip = models.IPAddressField(verbose_name=_('ip address'),
      blank=True, null=True)

    class Meta:
        abstract = True

    @classmethod
    def make_from_post(cls, post):
        """ Create an object from another object, possibly of a slightly
        different class (like tree Post).  """
        data = {}
        for field in cls._meta.fields:
            if field.primary_key:
                # Have to make this to create new object, not find an
                # existing one.
                # Can explicitly use 'Post_base' instead, also.
                continue
            # Assuming that all default fields for cls are None and thus
            # skipping 'None's from attribute values.
            attrdata = getattr(post, field.name, None)
            if attrdata is not None:
                data[field.name] = attrdata
        print "New post: %r" % data
        return cls(**data)

    def __unicode__(self):
        return u''.join( (u'#', unicode(self.id), u': ', unicode(self.user), u' @ ',
         unicode(self.date)) )


class Post_revisions(Post_base):
    """ Plain list of posts linked by 'revision' relations. """

    # Related names here look somewhat confusing.
    # AFAIU, 'prev' points to the next newer edit of the post same as
    # 'revision', and 'rev' - to the next older version, same as 'previous'.
    ## But actually, is 'revision' necessary?
    previous = models.ForeignKey("self", related_name="prev",
      editable=False, null=True, blank=True)
    #revision = models.ForeignKey("self", related_name="rev",
    #  editable=False, null=True, blank=True)

    def get_newer(self):
        """ A simple helper that should get the next newer version from any
        of two models derived from Post_base.  """
        next_ver = self.prev_last.get()
        if next_ver:  # is Post.
            return next_ver
        else:  # is Post_revisions.
            return self.prev.get()

    class Meta:
        verbose_name = _('post revision')
        verbose_name_plural = _('post revisions')


def _make_id_n(alphabet="0123456789abcdefghijklmnopqrstuvwxyz"):
    """ class: ... """
    from treebeard.numconv import NumConv    
    id_n_re = r'(?:[#!])?(?P<thread_id>[' + alphabet + \
      r']+)/(?P<post_tlid>[' + alphabet + r']+)'
    id_n_re_c = re.compile(r'^' + id_n_re + r'$')
    id_n_re_f = r'(?:[#!])?[' + alphabet + r']+/[' + alphabet + ']+'
    id_n_numconv = NumConv(len(alphabet), alphabet)
    def id_form_n(self):
        """ Thread-local number + numconv alphabet.  """
        return u"%s/%s" % (
          id_n_numconv.int2str(self.thread_id),
          id_n_numconv.int2str(self.tlid))
    @classmethod
    def from_id_n(cls, idn):
        m = id_n_re_c.match(idn)
        assert bool(m), u"idn %r is malformed" % idn
        thr, tlid = m.groups()
        return cls.objects.get(thread=int(thr, 16), tlid=int(tlid, 16))
    return id_n_re, id_n_re_f, id_form_n, from_id_n


class Post(Post_base, mp_tree.MP_Node):
    """ Tree-aligned set of posts (of latest versions). """
    ## Moderation:
    ## ? XXX: Is it appropriate to apply it only to latest versions of
    ## posts? Moderating particular edits is doubtful.
    # (boolean set by mod.; true if abuse report deemed false)
    censor = models.BooleanField(default=False, verbose_name=_('censored'))  # moderator level access
    freespeech = models.BooleanField(default=False, verbose_name=_('protected'))  # superuser level access

    ## Revisions are in a different model here.
    previous = models.ForeignKey(Post_revisions, related_name="prev_last",
      editable=False, null=True, blank=True)

    tlid = models.IntegerField(null=True, blank=True, default=None,
      verbose_name=_('thread-local id'))
    #objects = models.Manager()  # needs to be explicit due to below
    #view_manager = managers.PostManager()

    # ! Tree
    # ! Incompatible with date.auto_now_add=True
    #node_order_by = ['date']

    # ! get_descendants_group_count could be useful.

    # IDs. id_form_X <-> from_id_X
    #      ( String  <-> Post  )
    def id_form_a(self):
        # Simple post number.
        return str(self.id)

    @classmethod
    def from_id_a(cls, ida):
        # throws ValueError if int() fails.
        # also, it might not exist.
        return cls.objects.get(id=int(ida))

    def id_form_b(self):
        chunks = lambda l, n: [l[i:i+n] for i in xrange(0, len(l), n)]
        #pad = lambda x: '%s%s' % ('0' * (Post.steplen - len(x)), x)
        l_str2int = lambda x: self._str2int(x)
        c = chunks(self.path, self.steplen)
        return "%s/%s(%d)" % (l_str2int(c[0]),
          ".".join([str(l_str2int(i)) for i in c[1:]]), len(c)-1)
        # ! ? better:
        #c = chunks(self.path[self.steplen:], self.steplen)
        #return "%s/%s(%d)" % (self.thread_id,
        #  ".".join([str(l_str2int(i)) for i in c]), len(c))

    @classmethod
    def from_id_b(cls, idb):
        # No format checking. Catch stuff.
        l_int2str = lambda x: cls._int2str(x).rjust(cls.steplen, '0')
        # disregard `(n)` part of id if it's there.
        idb2 = idb.split('(', 1)[0]
        threadid, npath = idb2.split('/', 1)
        # ! ? better:
        # thread_path = Post.objects.get(thread=threadid, depth=1).path
        anpath = [threadid] + npath.split(".")
        tpath = "".join([l_int2str(int(i)) for i in anpath])
        return cls.objects.get(path=tpath)

    id_t_re = r'(?:[#!])?(?P<thread_id>\d+)/(?P<post_tlid>\d+)'
    id_t_re_f = r'(?:[#!])?\d+/\d+'
    def id_form_t(self):
        """ Thread-local number.  """
        return u"%s/%s" % (self.thread_id, self.tlid)
    @classmethod
    def from_id_t(cls, idt):
        m = re.match(r'^' + cls.id_t_re + r'$', idt)
        assert bool(m), u"idt %r is malformed" % idt
        thr, tlid = m.groups()
        return cls.objects.get(thread=int(thr), tlid=int(tlid))

    id_z_re, id_z_re_f, id_form_z, from_id_z = _make_id_n()

    id_x_re = r'(?:[#!])?(?P<thread_id>[0-9A-Fa-f]+)/(?P<post_tlid>[0-9A-Fa-f]+)'
    id_x_re_c = re.compile(r'^' + id_x_re + r'$')
    id_x_re_f = r'(?:[#!])?[0-9A-Fa-f]+/[0-9A-Fa-f]+'
    def id_form_x(self):
        """ Thread-local number + hex.  """
        return u"%x/%x" % (self.thread_id, self.tlid)
    @classmethod
    def from_id_x(cls, idx):
        m = cls.id_x_re_c.match(idx)
        assert bool(m), u"idx %r is malformed" % idx
        thr, tlid = m.groups()
        return cls.objects.get(thread=int(thr, 16), tlid=int(tlid, 16))

    id_form_m = id_form_x
    from_id_m = from_id_x
    id_m_re = id_x_re
    id_m_re_f = id_x_re_f

    @classmethod
    def get_post_or_404(cls, id_m):
        try:
            return cls.from_id_m(id_m)
        except cls.DoesNotExist:
            raise Http404('No post %s found.' % id_m)

    # for (possibly) better maxwidth/maxdepth ratio.
    # *might* run out of root posts, though!
    # ! FIXME: put something like 5 or 6 here and increase the 'path' field
    #  length (or remove length limit completely if possible).
    steplen = 5
    #path = models.CharField(max_length=255, unique=True)


    def save(self, force_insert=False, force_update=False):
        # ? huh?
        #_log.debug('user = %s, ip = %s' % (threadlocals.get_current_ip(),
        #    threadlocals.get_current_user()))

        # hack to disallow admin setting arbitrary users to posts
        if getattr(self, 'user_id', None) is None:
            self.user_id = threadlocals.get_current_user().id

        # disregard any modifications to ip address
        self.ip = threadlocals.get_current_ip()

        # ! XXX: Not really appropriate to do it here?..
        from snapboard.templatetags.extras import render_filter
        self.texth = render_filter(self.text)
        
        super(Post, self).save(force_insert, force_update)
        ## Update the thread-local id afterwards.
        self.update_lid()

    def update_lid(self, force=False):
        """ Atomically (SQL-level) updates the local id to the next
        available number (next to the highest).
        Does not replace an existing lid unless `force`d; but does not
        update it on the object after setting!  """
        #from django.db import models, connection, transaction
        from django.db import connection, transaction
        lid_s = "tlid"

        if getattr(self, lid_s, None) and not force:
            return  # do not replace it with higher.

        table_n = connection.ops.quote_name(self._meta.db_table)
        lid_n = connection.ops.quote_name(lid_s)
        local_fields = ('thread',)  # fields that define 'local'.
        # ! It is also possible to include a filtered QS (i.e. with `WHERE`)
        #  for defining 'local' (or even replace a list of fields with it)

        local_sql_l = []
        local_values = []
        for field_name in local_fields:
            field = self._meta.get_field(field_name)
            # ? No need to supply connection? :
            # also, db_prep returns list, it seems.
            local_values.extend(field.get_db_prep_lookup('exact',
              getattr(self, field.column)))
            local_sql_l.append(
              ' '.join([connection.ops.quote_name(field.column), '=', '%s'])
              )
        local_sql_l.append(
          ' '.join([lid_n, "IS NOT NULL"])
          )
        local_sql = ' AND '.join(local_sql_l)  # combine them.

        # Written as space-joined lists for convenience (avoiding the
        #   escaping hell, even if not much of it).
        # Note: starting from 0.
        subsql = ' '.join(['SELECT (', lid_n, '+ 1 )', 'FROM', table_n, 'WHERE',
         local_sql, 'ORDER BY', lid_n, 'DESC LIMIT 1'])
        sql = ' '.join(['UPDATE', table_n, 'SET', lid_n, '=', 'COALESCE((',
          subsql, '), 0)', 'WHERE', self._meta.pk.column, '=', '%s'])
        values = local_values + [self.pk]
        connection.cursor().execute(sql, values)
        transaction.commit_unless_managed()
    update_lid.alters_data = True

    def update_fields(self, **kwargs):
        """ A small helper function for slightly more neat code.   """
        return self.__class__.objects.filter(pk=self.pk).update(**kwargs)
    update_fields.alters_data = True

    def notify(self, **kwargs):
        if not self.previous:
            all_recipients = set()
            posttree = self.get_ancestors()
            #recipients = set((wl.user for wl in WatchList.objects.filter(thread=self.thread) if wl.user not in all_recipients))
            recipients = []
            resources = {}  # Special feature, ha.
            for wl in WatchList.objects.select_related(depth=2).filter(
              post__in=posttree).order_by("snapboard_post.depth"):
                # Sorting is required to override resource requirement with
                # the one of the deepest post.
                if wl.user not in all_recipients:
                    # ! Actually, check post.user != wl.user.  Probably.
                    # !! TODO: Should automatically add watches for own posts, or something like that!
                    recipients.append(wl.user)
                if wl.xmppresource:
                    resources[wl.user] = wl.xmppresource
                else:
                    # we're sending it to a bare jid. Allow simple
                    # resourcification without specifying post.
                    cache.set('nt_%s' % wl.user.username, [self.id,
                      time.time()])
            recipients = set(recipients)
            if recipients:
                send_notifications(
                    recipients,
                    'new_post_in_watched_thread',
                    extra_context={'post': self},
                    xmppresources=resources
                )
                all_recipients = all_recipients.union(recipients)

    def get_absolute_url(self):
        return reverse('snapboard_thread_post', args=(self.id,))

    def get_edit_form(self):
        from forms import PostForm
        return PostForm(instance=self) #initial={'text': self.text})

    class Meta:
        verbose_name = _('post')
        verbose_name_plural = _('posts')
        unique_together = (('thread', 'tlid'),)
# ! XXX: h4x it up!
mp_tree.MP_Node.path = models.TextField(unique=True)
Post._meta.get_field('path').max_length = 90000

# Signals make it hard to handle the notification of private recipients
# ** Not sure if it would be better to use them now.
#if notification:
#    signals.post_save.connect(Post.notify, sender=Post)


class AbuseReport(models.Model):
    '''
    When an abuse report is filed by a registered User, the post is listed
    in this table.

    If the abuse report is rejected as false, the post.freespeech flag can be
    set to disallow further abuse reports on said thread.
    '''
    post = models.ForeignKey(Post, verbose_name=_('post'), related_name='sb_abusereport_set')
    submitter = models.ForeignKey(User, verbose_name=_('submitter'), related_name='sb_abusereport_set')

    class Meta:
        verbose_name = _('abuse report')
        verbose_name_plural = _('abuse reports')
        unique_together = (('post', 'submitter'),)


class WatchList(models.Model):
    """
    Keep track of who is watching what post tree.  Notify on change (sidebar).
    Note thet this can be implemented as many_to_many field on post (looks
    like it's what it actally is anyway), plus (probably) a
    notification-level abstract XMPP resource distinction.
    """
    user = models.ForeignKey(User, verbose_name=_('user'),
      related_name='sb_watchlist')
    post = models.ForeignKey(Post, verbose_name=_('post'),
      related_name='sb_watchinglist')
    # This can be implemented for all notification types, though:
    xmppresource = models.CharField(max_length=80, blank=True,
      verbose_name=_('xmpp resource'))

    class Meta:
        verbose_name = _('Watched post')
        verbose_name_plural = _('Watched posts')

    def __unicode__(self):
        return _('%s\'s watch of post %s') % (self.user, self.post.id)


class UserSettings(models.Model):
    '''
    User data tied to user accounts from the auth module.

    Real name, email, and date joined information are stored in the built-in
    auth module.

    After logging in, save these values in a session variable.
    '''
    user = models.OneToOneField(User, unique=True,
            verbose_name=_('user'), related_name='sb_usersettings')
    ppp = models.IntegerField(
            choices = ((5, '5'), (10, '10'), (20, '20'), (50, '50')),
            default = 20,
            help_text = _('Posts per page'), verbose_name=_('posts per page'))
    tpp = models.IntegerField(
            choices = ((5, '5'), (10, '10'), (20, '20'), (50, '50')),
            default = 20,
            help_text = _('Threads per page'), verbose_name=_('threads per page'))
#    notify_email = models.BooleanField(default=False, blank=True,
#            help_text = "Email notifications for watched discussions.", verbose_name=_('notify'))
    reverse_posts = models.BooleanField(
            default=False,
            help_text = _('Display newest posts first.'), verbose_name=_('new posts first'))
    frontpage_filters = models.ManyToManyField(Category,
            null=True, blank=True,
            help_text = _('Filter the list of all topics on these categories.'), verbose_name=_('front page categories'))

    class Meta:
        verbose_name = _('User settings')
        verbose_name_plural = _('User settings')

    def __unicode__(self):
        return _('%s\'s preferences') % self.user


## Hack up User and AnonymouseUser classes for convenience.
# Note that it monkey-patches the whole django.contrib.auth.models.User
# class (and AnonymouseUser too) in the python-instance-wide import.
User.really_anonymous = False
AnonymousUser.really_anonymous = False

DEFAULT_USER_SETTINGS = UserSettings()
def get_user_settings(user):
    if not user.is_authenticated():
        return DEFAULT_USER_SETTINGS
    try:
        return user.sb_usersettings
    except UserSettings.DoesNotExist:
        return DEFAULT_USER_SETTINGS
User.get_user_settings = get_user_settings
AnonymousUser.get_user_settings = get_user_settings


class UserBan(models.Model):
    '''
    This bans the user from posting messages on the forum. He can still log in.
    '''
    user = models.ForeignKey(User, unique=True, verbose_name=_('user'), db_index=True,
            related_name='sb_userban_set',
            help_text=_('The user may still browse the forums anonymously. '
            'Other functions may also still be available to him if he is logged in.'))
    reason = models.CharField(max_length=255, verbose_name=_('reason'),
        help_text=_('This may be displayed to the banned user.'))

    class Meta:
        verbose_name = _('banned user')
        verbose_name_plural = _('banned users')

    def __unicode__(self):
        return _('Banned user: %s') % self.user

    @classmethod
    def update_cache(cls, **kwargs):
        c = connection.cursor()
        c.execute('SELECT user_id FROM %s;' % cls._meta.db_table)
        settings.SNAP_BANNED_USERS = set((x for (x,) in c.fetchall()))

signals.post_save.connect(UserBan.update_cache, sender=UserBan)
signals.post_delete.connect(UserBan.update_cache, sender=UserBan)


class IPBan(models.Model):
    '''
    IPs in the list are not allowed to use the boards.
    Only IPv4 addresses are supported, one per record. (patch with IPv6 and/or address range support welcome)
    '''
    address = models.IPAddressField(unique=True, verbose_name=_('IP address'),
            help_text=_('A person\'s IP address may change and an IP address may be '
            'used by more than one person, or by different people over time. '
            'Be careful when using this.'), db_index=True)
    reason = models.CharField(max_length=255, verbose_name=_('reason'),
        help_text=_('This may be displayed to the people concerned by the ban.'))

    class Meta:
        verbose_name = _('banned IP address')
        verbose_name_plural = _('banned IP addresses')

    def __unicode__(self):
        return _('Banned IP: %s') % self.address

    @classmethod
    def update_cache(cls, **kwargs):
        c = connection.cursor()
        c.execute('SELECT address FROM %s;' % cls._meta.db_table)
        settings.SNAP_BANNED_IPS = set((x for (x,) in c.fetchall()))


# currently unused.
def cachefetch(key, default=None, timeout=0):
    """ Slightly advanced cache.get() that can use result of a function and
    an additional timout parameter in case of cache miss.  """
    data = cache.get(key)
    if data is None:
        if default is not None:
            if callable(f):
                data = default()
            else:
                data = default
            cache.set(key, data, timeout)
    # no data, no default - returns actual None.
    return data


signals.post_save.connect(IPBan.update_cache, sender=IPBan)
signals.post_delete.connect(IPBan.update_cache, sender=IPBan)
