# Generated by Django 4.2 on 2023-10-05 00:04

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0016_alter_userprofile_key_expires'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='key_expires',
            field=models.DateTimeField(default=datetime.datetime(2023, 10, 7, 0, 4, 25, 301084, tzinfo=datetime.timezone.utc)),
        ),
    ]