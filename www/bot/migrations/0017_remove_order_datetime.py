# Generated by Django 4.2.6 on 2023-10-15 02:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0016_alter_bot_max_drawdown_alter_bot_quote_qty_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='datetime',
        ),
    ]
