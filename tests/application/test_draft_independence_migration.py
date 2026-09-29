"""The participation migration must keep existing editable intent."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError

from tests.application.test_physical_draft import context, valid_payload


@pytest.mark.django_db(transaction=True)
def test_existing_connection_participants_survive_through_migration(context):
    from modeling.models import Connection
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["nodes"].append({"client_key": "n3", "x_mm": 0, "y_mm": 100, "label": "上"})
    payload["physical_members"].append({
        "client_key": "m2", "start_node_client_key": "n1", "end_node_client_key": "n3",
        "material_id": material.id, "section_id": section.id, "label": "", "is_active": True,
    })
    payload["connections"][0]["participating_member_client_keys"] = ["m1", "m2"]
    save_physical_draft(actor=owner, project=project, payload=payload)
    connection_id = Connection.objects.get(project=project, client_key="c1").pk

    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        MigrationExecutor(connection).migrate([("modeling", "0002_support_client_key")])
        old = MigrationExecutor(connection)
        OldConnection = old.loader.project_state([("modeling", "0002_support_client_key")]).apps.get_model("modeling", "Connection")
        assert list(OldConnection.objects.get(pk=connection_id).participating_members.order_by("client_key").values_list("client_key", flat=True)) == ["m1", "m2"]

        MigrationExecutor(connection).migrate([("modeling", "0003_alter_connection_geometry_node_and_more")])
        current = MigrationExecutor(connection)
        Slot = current.loader.project_state([("modeling", "0003_alter_connection_geometry_node_and_more")]).apps.get_model("modeling", "ConnectionParticipation")
        assert list(Slot.objects.filter(connection_id=connection_id).order_by("position").values_list("member__client_key", flat=True)) == ["m1", "m2"]
    finally:
        MigrationExecutor(connection).migrate(latest)


@pytest.mark.django_db(transaction=True)
def test_migration_rollback_refuses_to_silently_discard_participation_gap(context):
    from modeling.models import ConnectionParticipation
    from modeling.services import save_physical_draft

    owner, project, material, section = context
    payload = valid_payload(material, section)
    payload["connections"][0]["participating_member_client_keys"] = [None]
    save_physical_draft(actor=owner, project=project, payload=payload)
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        with pytest.raises(IrreversibleError, match="participation gap"):
            MigrationExecutor(connection).migrate([("modeling", "0002_support_client_key")])
        assert ConnectionParticipation.objects.filter(connection__project=project, member__isnull=True).exists()
    finally:
        MigrationExecutor(connection).migrate(latest)
