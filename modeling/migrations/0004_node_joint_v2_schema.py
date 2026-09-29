import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0003_project_draft_schema_version"),
        ("modeling", "0003_alter_connection_geometry_node_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DraftMigrationAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(max_length=16)),
                ("source_draft_version", models.PositiveIntegerField()),
                ("source_hash", models.CharField(max_length=64)),
                ("source_payload_json", models.JSONField()),
                ("node_mapping_json", models.JSONField(default=dict)),
                ("legacy_exceptions_json", models.JSONField(default=dict)),
                ("reason_code", models.CharField(blank=True, max_length=100)),
                ("target_draft_version", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="draft_migration_audits", to="projects.project")),
            ],
        ),
        migrations.CreateModel(
            name="MemberJointIncidence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="joint_incidences", to="modeling.physicalmember")),
                ("node", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="member_joint_incidences", to="modeling.geometrynode")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="member_joint_incidences", to="projects.project")),
            ],
        ),
        migrations.AddField(
            model_name="support",
            name="target_node",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="supports", to="modeling.geometrynode"),
        ),
        migrations.AddField(
            model_name="nodeload",
            name="target_node",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="node_loads", to="modeling.geometrynode"),
        ),
        migrations.AddConstraint(
            model_name="memberjointincidence",
            constraint=models.UniqueConstraint(fields=("member", "node"), name="unique_member_joint_incidence"),
        ),
    ]
