# Generated by Django 4.2 on 2023-10-06 17:33

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0018_userprofile_config_alter_userprofile_key_expires'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='config',
            field=models.TextField(default='[]'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='key_expires',
            field=models.DateTimeField(default=datetime.datetime(2023, 10, 8, 17, 33, 6, 350330, tzinfo=datetime.timezone.utc)),
        ),
    ]
