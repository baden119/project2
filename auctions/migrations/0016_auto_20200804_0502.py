# Generated by Django 3.0.8 on 2020-08-04 05:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0015_auto_20200731_0635'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bid',
            old_name='comment_datetime',
            new_name='bid_datetime',
        ),
        migrations.AlterField(
            model_name='bid',
            name='listing',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bid', to='auctions.Listing'),
        ),
    ]
