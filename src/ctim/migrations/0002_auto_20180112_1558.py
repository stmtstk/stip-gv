# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2018-01-12 06:58
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ctim', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ctirsconfig',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='ctim.GVAuthUser'),
        ),
    ]
