from django.db import migrations, models
from django.db.models import Count


def reject_prediction_duplicates(apps, schema_editor):
    Prediction = apps.get_model("learning", "Prediction")
    duplicates = list(
        Prediction.objects.values("project_id", "source_draft_version")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .order_by("project_id", "source_draft_version")
    )
    if duplicates:
        pairs = "; ".join(
            f"project_id={row['project_id']}, source_draft_version={row['source_draft_version']}, count={row['count']}"
            for row in duplicates
        )
        raise RuntimeError(f"PREDICTION_AMBIGUOUS: {pairs}")


class Migration(migrations.Migration):
    dependencies = [("learning", "0003_reflection")]

    operations = [
        migrations.RunPython(reject_prediction_duplicates, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="prediction",
            constraint=models.UniqueConstraint(fields=("project", "source_draft_version"), name="unique_prediction_project_draft"),
        ),
    ]
