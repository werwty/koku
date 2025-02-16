# Generated by Django 2.2 on 2019-04-22 14:15

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('rates', '0004_auto_20190301_1850'),
    ]

    operations = [
        migrations.CreateModel(
            name='RateMap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider_uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('rate', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rates.Rate')),
            ],
            options={
                'ordering': ['-id'],
                'unique_together': {('provider_uuid', 'rate')},
            },
        ),
        migrations.RunSQL(
            """
            INSERT INTO rates_ratemap (provider_uuid, rate_id)
            SELECT provider_uuid, id 
            FROM rates_rate;
            """
        ),
        migrations.AlterUniqueTogether(
            name='rate',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='rate',
            name='provider_uuid',
        ),
    ]
