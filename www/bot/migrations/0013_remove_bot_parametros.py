# Generated by Django 4.2 on 2023-10-04 23:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0012_remove_bot_interval_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bot',
            name='parametros',
        ),
    ]