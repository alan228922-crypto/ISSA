from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0002_projectoperationalpurgeaudit")]

    operations = [
        migrations.AddField(
            model_name="project",
            name="draft_schema_version",
            field=models.CharField(default="physical-draft-v1", max_length=32),
        ),
    ]
