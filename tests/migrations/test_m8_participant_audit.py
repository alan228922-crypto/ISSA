import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone


@pytest.mark.django_db(transaction=True)
def test_audit_addfield_preserves_legacy_and_reverses():
    # 缺少 migration 是产品 RED；实际 forward/reverse 在隔离测试 DB 验证。
    executor = MigrationExecutor(connection)
    target = ('competitions', '0003_bulkimportbatch_operation_details')
    assert target in executor.loader.graph.nodes
    old = [('competitions', '0002_bulkimportbatch')]
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate(old)
        apps = executor.loader.project_state(old).apps
        User = apps.get_model('accounts', 'User')
        Event = apps.get_model('competitions', 'CompetitionEvent')
        Batch = apps.get_model('competitions', 'BulkImportBatch')
        actor = User.objects.create(username='legacy', role='MANAGER')
        now = timezone.now()
        event = Event.objects.create(name='Legacy', event_code='LEGACY', competition_date=now.date(),
                                     starts_at=now, ends_at=now, purge_at=now, status='DRAFT')
        batch = Batch.objects.create(actor=actor, event=event, source_filename='old.csv', row_count=2,
                                     success=True, created_account_count=2)
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        Batch = executor.loader.project_state([target]).apps.get_model('competitions', 'BulkImportBatch')
        migrated = Batch.objects.get(pk=batch.pk)
        assert migrated.operation_details_json == {}
        assert (migrated.actor_id, migrated.row_count, migrated.created_account_count) == (actor.pk, 2, 2)
        executor.migrate(old)
        Batch = executor.loader.project_state(old).apps.get_model('competitions', 'BulkImportBatch')
        assert Batch.objects.get(pk=batch.pk).created_account_count == 2
    finally:
        MigrationExecutor(connection).migrate(latest)
