# Generated by Django 4.2.6 on 2023-10-15 02:42

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0023_alter_userprofile_key_expires'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='key_expires',
            field=models.DateTimeField(default=datetime.datetime(2023, 10, 17, 2, 42, 48, 79335, tzinfo=datetime.timezone.utc)),
        ),
    ]