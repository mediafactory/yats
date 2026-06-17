from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('yats', '0027_auto_20210211_1723'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='dashboard_config',
            field=models.TextField(blank=True, null=True),
        ),
    ]
