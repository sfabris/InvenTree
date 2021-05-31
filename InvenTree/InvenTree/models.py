"""
Generic models which provide extra functionality over base Django model types.
"""

from __future__ import unicode_literals

import os

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from mptt.models import MPTTModel, TreeForeignKey

from .validators import validate_tree_name


def rename_attachment(instance, filename):
    """
    Function for renaming an attachment file.
    The subdirectory for the uploaded file is determined by the implementing class.

        Args:
        instance: Instance of a PartAttachment object
        filename: name of uploaded file

    Returns:
        path to store file, format: '<subdir>/<id>/filename'
    """

    # Construct a path to store a file attachment for a given model type
    return os.path.join(instance.getSubdir(), filename)


class InvenTreeAttachment(models.Model):
    """ Provides an abstracted class for managing file attachments.

    Attributes:
        attachment: File
        comment: String descriptor for the attachment
        user: User associated with file upload
        upload_date: Date the file was uploaded
    """
    def getSubdir(self):
        """
        Return the subdirectory under which attachments should be stored.
        Note: Re-implement this for each subclass of InvenTreeAttachment
        """

        return "attachments"

    def __str__(self):
        return os.path.basename(self.attachment.name)

    attachment = models.FileField(upload_to=rename_attachment, verbose_name=_('Attachment'),
                                  help_text=_('Select file to attach'))

    comment = models.CharField(blank=True, max_length=100, verbose_name=_('Comment'), help_text=_('File comment'))

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        verbose_name=_('User'),
        help_text=_('User'),
    )

    upload_date = models.DateField(auto_now_add=True, null=True, blank=True, verbose_name=_('upload date'))

    @property
    def basename(self):
        return os.path.basename(self.attachment.name)

    class Meta:
        abstract = True


class InvenTreeTree(MPTTModel):
    """ Provides an abstracted self-referencing tree model for data categories.

    - Each Category has one parent Category, which can be blank (for a top-level Category).
    - Each Category can have zero-or-more child Categor(y/ies)

    Attributes:
        name: brief name
        description: longer form description
        parent: The item immediately above this one. An item with a null parent is a top-level item
    """

    class Meta:
        abstract = True

        # Names must be unique at any given level in the tree
        unique_together = ('name', 'parent')

    class MPTTMeta:
        order_insertion_by = ['name']

    name = models.CharField(
        blank=False,
        max_length=100,
        validators=[validate_tree_name],
        verbose_name=_("Name"),
        help_text=_("Name"),
    )

    description = models.CharField(
        blank=True,
        max_length=250,
        verbose_name=_("Description"),
        help_text=_("Description (optional)")
    )

    # When a category is deleted, graft the children onto its parent
    parent = TreeForeignKey('self',
                            on_delete=models.DO_NOTHING,
                            blank=True,
                            null=True,
                            verbose_name=_("parent"),
                            related_name='children')

    @property
    def item_count(self):
        """ Return the number of items which exist *under* this node in the tree.

        Here an 'item' is considered to be the 'leaf' at the end of each branch,
        and the exact nature here will depend on the class implementation.

        The default implementation returns zero
        """
        return 0

    def getUniqueParents(self):
        """ Return a flat set of all parent items that exist above this node.
        If any parents are repeated (which would be very bad!), the process is halted
        """

        return self.get_ancestors()

    def getUniqueChildren(self, include_self=True):
        """ Return a flat set of all child items that exist under this node.
        If any child items are repeated, the repetitions are omitted.
        """

        return self.get_descendants(include_self=include_self)

    @property
    def has_children(self):
        """ True if there are any children under this item """
        return self.getUniqueChildren(include_self=False).count() > 0

    def getAcceptableParents(self):
        """ Returns a list of acceptable parent items within this model
        Acceptable parents are ones which are not underneath this item.
        Setting the parent of an item to its own child results in recursion.
        """

        contents = ContentType.objects.get_for_model(type(self))

        available = contents.get_all_objects_for_this_type()

        # List of child IDs
        childs = self.getUniqueChildren()

        acceptable = [None]

        for a in available:
            if a.id not in childs:
                acceptable.append(a)

        return acceptable

    @property
    def parentpath(self):
        """ Get the parent path of this category

        Returns:
            List of category names from the top level to the parent of this category
        """

        return [a for a in self.get_ancestors()]

    @property
    def path(self):
        """ Get the complete part of this category.

        e.g. ["Top", "Second", "Third", "This"]

        Returns:
            List of category names from the top level to this category
        """
        return self.parentpath + [self]

    @property
    def pathstring(self):
        """ Get a string representation for the path of this item.

        e.g. "Top/Second/Third/This"
        """
        return '/'.join([item.name for item in self.path])

    def __str__(self):
        """ String representation of a category is the full path to that category """

        return "{path} - {desc}".format(path=self.pathstring, desc=self.description)


@receiver(pre_delete, sender=InvenTreeTree, dispatch_uid='tree_pre_delete_log')
def before_delete_tree_item(sender, instance, using, **kwargs):
    """ Receives pre_delete signal from InvenTreeTree object.

    Before an item is deleted, update each child object to point to the parent of the object being deleted.
    """

    # Update each tree item below this one
    for child in instance.children.all():
        child.parent = instance.parent
        child.save()
