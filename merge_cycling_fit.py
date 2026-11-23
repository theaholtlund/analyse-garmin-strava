"""Build an experimental local MOWL/Garmin FIT file. Never uploads or deletes."""
import argparse
import io
import zipfile
from statistics import mean
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import fitdecode
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.record_message import RecordMessage


def read_fit(path):
    data = Path(path).read_bytes()
    if zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            files = [n for n in archive.namelist() if n.lower().endswith('.fit') and not n.startswith('__MACOSX/')]
            if len(files) != 1:
                raise ValueError('ZIP must contain exactly one FIT file')
            data = archive.read(files[0])
    records, sessions = defaultdict(dict), []
    with fitdecode.FitReader(io.BytesIO(data)) as reader:
        for message in reader:
            if not isinstance(message, fitdecode.FitDataMessage):
                continue
            values = {field.name: field.value for field in message.fields if field.value is not None}
            if message.name == 'record' and values.get('timestamp'):
                timestamp = values.pop('timestamp')
                # FIT timestamps have second precision; later valid values win within a second.
                if values.get('heart_rate') == 0:
                    values.pop('heart_rate')
                records[timestamp].update(values)
            elif message.name == 'session':
                sessions.append(values)
    if not records or len(sessions) != 1:
        raise ValueError('Expected a single-session activity with timestamped records')
    return dict(records), sessions[0]


def merge(mowl_path, garmin_path, output):
    mowl, ms = read_fit(mowl_path)
    garmin, gs = read_fit(garmin_path)
    start, end = min(min(mowl), min(garmin)), max(max(mowl), max(garmin))
    overlap = (min(max(mowl), max(garmin)) - max(min(mowl), min(garmin))).total_seconds()
    shortest = min((max(mowl) - min(mowl)).total_seconds(), (max(garmin) - min(garmin)).total_seconds())
    if shortest <= 0 or overlap / shortest < .8:
        raise ValueError('Activities do not overlap sufficiently; refusing to merge')
    totals = [x for x in (ms.get('total_distance'), gs.get('total_distance')) if x is not None]
    if not totals:
        raise ValueError('No total distance in either activity')
    distance = max(totals)
    elapsed = max((end - start).total_seconds(), ms.get('total_elapsed_time') or 0, gs.get('total_elapsed_time') or 0)
    timers = [x for x in (ms.get('total_timer_time'), gs.get('total_timer_time')) if x is not None]
    timer = max(timers) if timers else None
    # Keep all Garmin messages, including unknown device-specific messages and
    # training metadata. Add MOWL measurements to each matching Garmin record.
    # Original timer events and lap boundaries remain Garmin's, not fabricated.
    raw = Path(garmin_path).read_bytes()
    if zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith('.fit') and not n.startswith('__MACOSX/')]
            raw = archive.read(names[0])
    original = FitFile.from_bytes(raw)
    builder = FitFileBuilder(auto_define=True)
    pending = iter(sorted(set(mowl) - set(garmin)))
    next_missing = next(pending, None)
    all_times = sorted(set(mowl) | set(garmin))
    distance_by_time = {}
    last_distance = None
    for t in all_times:
        value = mowl.get(t, {}).get('distance')
        if value is not None:
            last_distance = max(last_distance or 0, value)
        distance_by_time[t] = last_distance

    def set_field(message, name, value):
        field = message.get_field_by_name(name)
        if field is not None and not field.is_valid():
            field.growable = True
        setattr(message, name, value)

    def add_mowl_fields(point, t):
        values = mowl.get(t, {})
        if values.get('heart_rate'):
            set_field(point, 'heart_rate', values['heart_rate'])
        for field in ('power', 'cadence', 'enhanced_speed', 'grade', 'calories'):
            if values.get(field) is not None:
                set_field(point, field, values[field])
        if distance_by_time[t] is not None:
            set_field(point, 'distance', distance_by_time[t])

    def add_missing(t):
        point = RecordMessage()
        point.timestamp = round(t.timestamp() * 1000)
        add_mowl_fields(point, t)
        builder.add(point)

    heart_rates = [mowl.get(t, {}).get('heart_rate') or garmin.get(t, {}).get('heart_rate')
                   for t in all_times]
    heart_rates = [hr for hr in heart_rates if hr]
    power = [v['power'] for v in mowl.values() if v.get('power') is not None]
    cadence = [v['cadence'] for v in mowl.values() if v.get('cadence') not in (None, 0)]
    last_garmin_time = max(garmin)
    for item in original.records:
        message = item.message
        name = type(message).__name__
        if name == 'DefinitionMessage':
            continue
        if name == 'RecordMessage':
            t = datetime.fromtimestamp(message.timestamp / 1000, timezone.utc)
            while next_missing is not None and next_missing < t:
                add_missing(next_missing)
                next_missing = next(pending, None)
            add_mowl_fields(message, t)
            message.definition_message = None
            builder.add(message)
            if t == last_garmin_time:
                while next_missing is not None:
                    add_missing(next_missing)
                    next_missing = next(pending, None)
            continue
        if name == 'SessionMessage':
            set_field(message, 'total_elapsed_time', elapsed)
            set_field(message, 'total_distance', distance)
            if timer is not None: set_field(message, 'total_timer_time', timer)
            if heart_rates:
                set_field(message, 'avg_heart_rate', round(mean(heart_rates)))
                set_field(message, 'max_heart_rate', max(heart_rates))
            if power:
                set_field(message, 'avg_power', round(mean(power)))
                set_field(message, 'max_power', max(power))
            if cadence:
                set_field(message, 'avg_cadence', round(mean(cadence)))
                set_field(message, 'max_cadence', max(cadence))
        # A single Garmin lap spans the workout; keep its summary consistent.
        if name == 'LapMessage' and gs.get('num_laps') == 1:
            set_field(message, 'total_elapsed_time', elapsed)
            set_field(message, 'total_distance', distance)
            if heart_rates:
                set_field(message, 'avg_heart_rate', round(mean(heart_rates)))
                set_field(message, 'max_heart_rate', max(heart_rates))
            if power:
                set_field(message, 'avg_power', round(mean(power)))
                set_field(message, 'max_power', max(power))
            if cadence:
                set_field(message, 'avg_cadence', round(mean(cadence)))
                set_field(message, 'max_cadence', max(cadence))
        if name in ('SessionMessage', 'LapMessage'):
            message.definition_message = None
        builder.add(message)
    while next_missing is not None:
        add_missing(next_missing)
        next_missing = next(pending, None)
    builder.build().to_file(str(output))
    return {'start': str(start), 'end': str(end), 'elapsed_seconds': elapsed, 'timer_seconds': timer,
            'summary_distance_m': distance, 'mowl_last_distance_m': last_distance, 'records': len(set(mowl) | set(garmin))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mowl'); parser.add_argument('garmin'); parser.add_argument('output')
    args = parser.parse_args()
    print(merge(args.mowl, args.garmin, args.output))
    print('Experimental: summary distance may differ from the MOWL distance series; Garmin training data may not survive import.')


if __name__ == '__main__':
    main()
