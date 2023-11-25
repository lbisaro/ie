# Generated by Django 4.2 on 2023-10-06 18:48

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0019_alter_userprofile_config_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='config',
            field=models.TextField(default='{}'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='key_expires',
            field=models.DateTimeField(default=datetime.datetime(2023, 10, 8, 18, 48, 47, 727278, tzinfo=datetime.timezone.utc)),
        ),
    ]