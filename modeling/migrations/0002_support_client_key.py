from django.db import migrations, models


def backfill_support_client_keys(apps, schema_editor):
    Support = apps.get_model("modeling", "Support")
    for support in Support.objects.order_by("pk"):
        support.client_key = f"support-{support.pk}"
        support.save(update_fields=["client_key"])


class Migration(migrations.Migration):
    dependencies = [("modeling", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="support",
            name="client_key",
            field=models.CharField(max_length=128, null=True),
        ),
        migrations.RunPython(backfill_support_client_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="support",
            name="client_key",
            field=models.CharField(max_length=128),
        ),
        migrations.AddConstraint(
            model_name="support",
            constraint=models.UniqueConstraint(fields=("project", "client_key"), name="unique_support_client_key"),
        ),
    ]
