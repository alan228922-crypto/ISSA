from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0003_project_draft_schema_version")]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="draft_schema_version",
            field=models.CharField(default="physical-draft-v2", max_length=32),
        ),
    ]
