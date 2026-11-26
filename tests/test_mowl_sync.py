import datetime as dt
from pathlib import Path

import pytest

from mowl_sync import Journal, find_garmin_match, process, uploaded_activity_id
from test_merge_cycling_fit import make_fit


@pytest.fixture
def activity():
    return {'id': 1, 'name': 'MOWL Just Ride', 'start_date': '2026-11-23T05:54:44Z', 'elapsed_time': 1000}


def row(ident=55, start='2026-11-23T05:54:44', kind='indoor_cycling'):
    return {'activityId': ident, 'startTimeGMT': start, 'elapsedDuration': 1000, 'activityType': {'typeKey': kind}}


def test_match_requires_source_and_unambiguous_overlap(activity):
    assert find_garmin_match(activity, [row()])['activityId'] == 55
    assert find_garmin_match(activity, [row(start='2026-11-23T08:00:00')]) is None
    assert find_garmin_match(activity, [row(kind='running')]) is None
    with pytest.raises(ValueError, match='Multiple'):
        find_garmin_match(activity, [row(), row(56)])


def test_upload_response_requires_single_verified_success():
    assert uploaded_activity_id({'detailedImportResult': {'successes': [{'internalId': 123}], 'failures': []}}) == '123'
    for response in (True, {}, {'detailedImportResult': {'successes': [], 'failures': []}},
                     {'detailedImportResult': {'successes': [{'internalId': 1}], 'failures': [{}]}}):
        with pytest.raises(ValueError):
            uploaded_activity_id(response)


def test_upload_is_journaled_and_not_repeated(tmp_path, activity):
    start = dt.datetime(2026, 11, 23, 5, 54, 44, tzinfo=dt.timezone.utc)
    source = tmp_path / 'source.fit'
    make_fit(source, start, [(0, {'power': 100}), (10, {'power': 120})], 100)
    class API:
        calls = 0
        def upload_activity(self, path):
            self.calls += 1
            assert Path(path).exists()
            return {'detailedImportResult': {'successes': [{'internalId': 123}], 'failures': []}}
        def get_activity(self, ident):
            return {'activityId': int(ident)}
    api = API()
    journal = Journal(tmp_path / 'db')
    downloader = lambda activity, folder: source
    assert process(activity, None, api, downloader, journal, tmp_path / 'out', False) == 'planned'
    assert api.calls == 0
    assert process(activity, None, api, downloader, journal, tmp_path / 'out', True) == 'uploaded'
    assert process(activity, None, api, downloader, journal, tmp_path / 'out', True) == 'skipped'
    assert api.calls == 1


def test_failed_upload_is_not_retried(tmp_path, activity):
    start = dt.datetime(2026, 11, 23, 5, 54, 44, tzinfo=dt.timezone.utc)
    source = tmp_path / 'source.fit'
    make_fit(source, start, [(0, {}), (10, {})], 100)
    class API:
        def upload_activity(self, path):
            raise TimeoutError('response lost')
    journal = Journal(tmp_path / 'db')
    with pytest.raises(RuntimeError, match='may have happened'):
        process(activity, None, API(), lambda *_: source, journal, tmp_path / 'out', True)
    assert journal.get(1)[0] == 'uncertain'
    assert process(activity, None, API(), lambda *_: source, journal, tmp_path / 'out', True) == 'skipped'


def test_merge_path_uploads_mowl_and_garmin_data(tmp_path, activity):
    import io
    import zipfile
    from merge_cycling_fit import read_fit
    start = dt.datetime(2026, 11, 23, 5, 54, 44, tzinfo=dt.timezone.utc)
    mowl = tmp_path / 'mowl.fit'
    garmin = tmp_path / 'garmin.fit'
    make_fit(mowl, start, [(0, {'heart_rate': 90, 'power': 100}), (10, {'heart_rate': 91, 'power': 120})], 100)
    make_fit(garmin, start, [(0, {'heart_rate': 100}), (10, {'heart_rate': 101})], 110)
    class API:
        class ActivityDownloadFormat:
            ORIGINAL = 1
        def download_activity(self, ident, fmt):
            assert ident == '55'
            output = io.BytesIO()
            with zipfile.ZipFile(output, 'w') as archive:
                archive.writestr('original.fit', garmin.read_bytes())
            return output.getvalue()
        def upload_activity(self, path):
            records, session = read_fit(path)
            assert records[start]['heart_rate'] == 90
            assert records[start]['power'] == 100
            assert session['total_distance'] == 110
            return {'detailedImportResult': {'successes': [{'internalId': 123}], 'failures': []}}
        def get_activity(self, ident):
            return {'activityId': int(ident)}
    journal = Journal(tmp_path / 'db')
    assert process(activity, row(), API(), lambda *_: mowl, journal, tmp_path / 'out', True) == 'uploaded'
    assert journal.get(1) == ('uploaded', '55', '123')


def test_cleanup_deletes_only_after_metrics_and_exact_fit_match(tmp_path, activity, monkeypatch):
    import mowl_sync
    import strava
    import strava_browser
    start = dt.datetime(2026, 11, 23, 5, 54, 44, tzinfo=dt.timezone.utc)
    folder = tmp_path / 'artifacts'
    folder.mkdir()
    for name in ('mowl-original.fit', 'garmin-original.zip', 'to-garmin.fit'):
        make_fit(folder / name, start, [(0, {'heart_rate': 100}), (10, {'heart_rate': 101})], 100)
    source = tmp_path / 'watch.fit'
    make_fit(source, start, [(0, {}), (10, {})], 100)
    identity = (123, start, start, 10)
    monkeypatch.setattr(mowl_sync, 'fit_device_identity', lambda path: identity)
    monkeypatch.setattr(strava_browser, 'recent_rides', lambda *a, **k: [
        {'id': 1, 'name': 'MOWL Just Ride', 'date': '2026-11-23'},
        {'id': 2, 'name': 'Morning Ride', 'date': '2026-11-23'}])
    monkeypatch.setattr(strava, 'download_multiple_activities', lambda *a, **k: [str(source)])
    removed = []
    monkeypatch.setattr(strava_browser, 'delete_confirmed_watch_copy', lambda duplicate, protected, *a: removed.append((duplicate, protected)))
    class API:
        deleted = False
        def get_activity(self, ident):
            if str(ident) == '55':
                if self.deleted:
                    raise RuntimeError('404 not found')
                return {'activityId': 55, 'summaryDTO': {'startTimeGMT': start.isoformat()}}
            return {'activityId': 123, 'summaryDTO': {'distance': 100, 'calories': 342, 'trainingEffect': 0.4}}
        def delete_activity(self, ident):
            assert ident == '55'
            self.deleted = True
    journal = Journal(tmp_path / 'db')
    journal.reserve('1', '55', folder)
    journal.update('1', 'uploaded', '123')
    api = API()
    mowl_sync.cleanup_uploaded(activity, api, journal, tmp_path, 2, 'MOWL')
    assert removed == [(2, '1')]
    assert api.deleted
    assert journal.get('1') == ('complete', '55', '123')


def test_cleanup_refuses_if_imported_metrics_missing(tmp_path, activity, monkeypatch):
    import mowl_sync
    start = dt.datetime(2026, 11, 23, 5, 54, 44, tzinfo=dt.timezone.utc)
    folder = tmp_path / 'artifacts'
    folder.mkdir()
    for name in ('mowl-original.fit', 'garmin-original.zip', 'to-garmin.fit'):
        make_fit(folder / name, start, [(0, {}), (10, {})], 100)
    monkeypatch.setattr(mowl_sync, 'fit_device_identity', lambda path: (123, start, start, 10))
    class API:
        def get_activity(self, ident):
            return {'activityId': 123, 'summaryDTO': {'distance': 100}}
        def delete_activity(self, ident):
            pytest.fail('Must not delete when metrics cannot be verified')
    journal = Journal(tmp_path / 'db')
    journal.reserve('1', '55', folder)
    journal.update('1', 'uploaded', '123')
    with pytest.raises(ValueError, match='calories'):
        mowl_sync.cleanup_uploaded(activity, API(), journal, tmp_path, 2, 'MOWL')
    assert journal.get('1')[0] == 'uploaded'
