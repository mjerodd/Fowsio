from django.db import models
from django.forms import Textarea
from django.utils.text import slugify

# Create your models here.

class Router(models.Model):
    vendor = models.CharField(max_length=30)
    role = models.CharField(max_length=30)
    model = models.CharField(max_length=100)
    template = models.FileField(upload_to="uploads/router_templates")
    slug = models.SlugField(unique=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.model)
        super().save(*args, **kwargs)


class Switch(models.Model):
    vendor = models.CharField(max_length=30)
    role = models.CharField(max_length=30)
    model = models.CharField(max_length=100)
    template = models.FileField(upload_to="uploads/switch_templates")
    slug = models.SlugField(unique=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.model)
        super().save(*args, **kwargs)


class Firewall(models.Model):
    vendor = models.CharField(max_length=30)
    role = models.CharField(max_length=30)
    model = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.model)
        super().save(*args, **kwargs)

