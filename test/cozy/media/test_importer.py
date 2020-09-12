from unittest.mock import MagicMock, call

import pytest
from peewee import SqliteDatabase

from cozy.ext import inject
from cozy.model.library import Library


@pytest.fixture(autouse=True)
def setup_inject(peewee_database_storage):
    inject.clear_and_configure(lambda binder: binder
                               .bind(SqliteDatabase, peewee_database_storage)
                               .bind_to_constructor("FilesystemMonitor", MagicMock())
                               .bind_to_constructor(Library, MagicMock()))

    yield
    inject.clear()


def test_external_paths_are_excluded_when_offline(mocker):
    from cozy.media.importer import Importer
    from cozy.db.storage import Storage

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("cozy.control.filesystem_monitor.FilesystemMonitor.is_storage_online", autospec=True,
                 return_value=False)

    importer = Importer()
    paths_to_import = importer._get_configured_storage_paths()

    internal_storages_in_db = Storage.select().where(Storage.external is not False)
    internal_storage_paths = [storage.path for storage in internal_storages_in_db]
    assert len(internal_storage_paths) == len(paths_to_import)
    assert all([a == b for a, b in zip(internal_storage_paths, paths_to_import)])


def test_paths_not_existing_are_excluded(mocker):
    from cozy.media.importer import Importer

    mocker.patch("os.path.exists", return_value=False)

    importer = Importer()
    paths_to_import = importer._get_configured_storage_paths()

    assert len(paths_to_import) == 0


def test_all_existing_paths_are_included(mocker):
    from cozy.media.importer import Importer
    from cozy.db.storage import Storage

    mocker.patch("os.path.exists", return_value=True)

    importer = Importer()
    paths_to_import = importer._get_configured_storage_paths()

    internal_storages_in_db = Storage.select()
    internal_storage_paths = [storage.path for storage in internal_storages_in_db]

    assert len(internal_storage_paths) == len(paths_to_import)
    assert all([a == b for a, b in zip(internal_storage_paths, paths_to_import)])


def test_import_file_returns_false_for_directory(mocker):
    from cozy.media.importer import Importer

    mocker.patch("os.path.isfile", return_value=False)

    importer = Importer()
    imported = importer.import_file(MagicMock())

    assert not imported


def test_filter_unchanged_files_returns_only_new_or_changed_files(mocker):
    from cozy.media.importer import Importer

    example_chapters = []

    mocker.patch("cozy.model.library.Library.chapters")
    mocker.patch("os.path.getmtime", return_value=100)

    importer = Importer()


def test_scan_emits_start_event(mocker):
    from cozy.media.importer import Importer, ScanStatus

    importer = Importer()
    spy = mocker.spy(importer, "emit_event_main_thread")
    importer.scan()

    spy.assert_has_calls(calls=[call("scan", ScanStatus.STARTED), call("scan", ScanStatus.SUCCESS)])


def test_scan_returns_file_names_that_could_not_be_imported(mocker):
    from cozy.media.importer import Importer

    files = {"1", "2"}

    mocker.patch("multiprocessing.pool.ThreadPool.map", return_value=files)
    mocker.patch("cozy.model.library.Library.insert_many")

    importer = Importer()
    not_imported = importer._execute_import(files)

    assert not_imported == files


def test_scan_returns_none_for_non_audio_files(mocker):
    from cozy.media.importer import Importer

    def iterator():
        for item in [None, None]:
            yield item

    mocker.patch("multiprocessing.pool.ThreadPool.map", return_value=iterator())
    mocker.patch("cozy.model.library.Library.insert_many")

    importer = Importer()
    not_imported = importer._execute_import(["a"])

    assert not_imported == set()
