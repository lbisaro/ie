# Generated by Django 4.2.6 on 2023-10-22 13:49

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0026_alter_userprofile_key_expires'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='key_expires',
            field=models.DateTimeField(default=datetime.datetime(2023, 10, 24, 13, 49, 42, 203914, tzinfo=datetime.timezone.utc)),
        ),
    ]
