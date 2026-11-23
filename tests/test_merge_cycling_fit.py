from datetime import datetime, timedelta, timezone

import pytest
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import FileType, Manufacturer

from merge_cycling_fit import merge, read_fit


def make_fit(path, start, records, distance):
    builder = FitFileBuilder(auto_define=True)
    identity = FileIdMessage()
    identity.type = FileType.ACTIVITY
    identity.manufacturer = Manufacturer.DEVELOPMENT
    identity.product = 1
    identity.time_created = int(start.timestamp() * 1000)
    builder.add(identity)
    for offset, values in records:
        record = RecordMessage()
        record.timestamp = int((start + timedelta(seconds=offset)).timestamp() * 1000)
        for key, value in values.items():
            setattr(record, key, value)
        builder.add(record)
    session = SessionMessage()
    session.start_time = int(start.timestamp() * 1000)
    session.total_distance = distance
    session.total_calories = 342
    session.total_training_effect = 0.4
    builder.add(session)
    builder.build().to_file(str(path))


def test_merge_prefers_mowl_heart_rate_and_larger_total(tmp_path):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    mowl, garmin, output = (tmp_path / name for name in ('m.fit', 'g.fit', 'out.fit'))
    make_fit(mowl, start, [(0, {'heart_rate': 101, 'power': 100, 'distance': 0}),
                           (10, {'heart_rate': 0, 'power': 120, 'distance': 90})], 90)
    make_fit(garmin, start, [(0, {'heart_rate': 110}), (10, {'heart_rate': 111})], 100)
    merge(mowl, garmin, output)
    records, session = read_fit(output)
    assert records[start]['heart_rate'] == 101
    assert records[start + timedelta(seconds=10)]['heart_rate'] == 111
    assert session['avg_heart_rate'] == 106
    assert session['max_heart_rate'] == 111
    assert records[start]['power'] == 100
    assert records[start + timedelta(seconds=10)]['distance'] == 90
    assert session['total_distance'] == 100
    assert session['total_calories'] == 342
    assert session['total_training_effect'] == pytest.approx(0.4)
    assert session['avg_power'] == 110


def test_merge_rejects_unrelated_activities(tmp_path):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    mowl, garmin = (tmp_path / name for name in ('m.fit', 'g.fit'))
    make_fit(mowl, start, [(0, {}), (10, {})], 100)
    make_fit(garmin, start + timedelta(hours=1), [(0, {}), (10, {})], 100)
    with pytest.raises(ValueError, match='overlap'):
        merge(mowl, garmin, tmp_path / 'out.fit')
