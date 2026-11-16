from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('competitions', '0002_bulkimportbatch')]
    operations = [
        migrations.AddField(
            model_name='bulkimportbatch', name='operation_details_json',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
