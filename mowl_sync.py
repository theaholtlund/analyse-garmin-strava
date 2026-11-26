"""Synchronize MOWL rides to Garmin, with verified duplicate cleanup."""
import argparse
import datetime as dt
import gzip
import io
import zipfile
import fitdecode
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

from dotenv import load_dotenv

from merge_cycling_fit import merge, read_fit

log = logging.getLogger(__name__)
UTC = dt.timezone.utc
CYCLING_TYPES = {'indoor_cycling', 'virtual_ride', 'cycling'}


def timestamp(value):
    if not value:
        raise ValueError('Missing activity start time')
    parsed = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def activity_interval(activity):
    start = timestamp(activity['start_date'])
    duration = activity.get('elapsed_time')
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise ValueError('Missing activity elapsed time')
    return start, start + dt.timedelta(seconds=duration)


def find_garmin_match(activity, garmin_activities):
    start, end = activity_interval(activity)
    matches = []
    for row in garmin_activities:
        kind = row.get('activityType') or {}
        kind = kind.get('typeKey', '') if isinstance(kind, dict) else kind
        if kind not in CYCLING_TYPES or not row.get('activityId'):
            continue
        try:
            other_start = timestamp(row['startTimeGMT'])
            duration = float(row.get('elapsedDuration') or row.get('duration') or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if duration <= 0:
            continue
        other_end = other_start + dt.timedelta(seconds=duration)
        overlap = (min(end, other_end) - max(start, other_start)).total_seconds()
        shorter = min((end - start).total_seconds(), duration)
        if overlap >= .8 * shorter and abs((start - other_start).total_seconds()) <= 900:
            matches.append(row)
    if len(matches) > 1:
        raise ValueError('Multiple Garmin activities match; manual review required')
    return matches[0] if matches else None


class Journal:
    def __init__(self, path, checkpoint=None):
        self.root = Path(path).resolve().parent
        self.checkpoint = checkpoint
        self.db = sqlite3.connect(path, timeout=30)
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.execute('''CREATE TABLE IF NOT EXISTS mowl_sync (
            strava_id TEXT PRIMARY KEY, status TEXT NOT NULL, garmin_original_id TEXT,
            garmin_upload_id TEXT, detail TEXT, updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(mowl_sync)')}
        if 'artifact_dir' not in columns:
            self.db.execute('ALTER TABLE mowl_sync ADD COLUMN artifact_dir TEXT')
        self.db.commit()
        os.chmod(path, 0o600)

    def get(self, ident):
        return self.db.execute('SELECT status, garmin_original_id, garmin_upload_id FROM mowl_sync WHERE strava_id=?', (str(ident),)).fetchone()

    def reserve(self, ident, original, artifact_dir=None):
        # Reservation precedes upload. A crash or network error remains uncertain
        # and is never automatically retried, preventing accidental duplicates.
        try:
            self.db.execute("INSERT INTO mowl_sync (strava_id,status,garmin_original_id,artifact_dir) VALUES (?,?,?,?)", (str(ident), 'uploading', str(original) if original else None, str(Path(artifact_dir).resolve().relative_to(self.root)) if artifact_dir else None))
            self.db.commit()
        except sqlite3.IntegrityError:
            return False
        if self.checkpoint:
            self.checkpoint()
        return True

    def artifacts(self, ident):
        row = self.db.execute('SELECT artifact_dir FROM mowl_sync WHERE strava_id=?', (str(ident),)).fetchone()
        if not row or not row[0]:
            return None
        path = Path(row[0])
        if not path.is_absolute():
            return str(self.root / path)
        # Older local journals stored absolute paths from a different machine.
        parts = path.parts
        if 'mowl-sync' in parts:
            idx = len(parts) - 1 - list(reversed(parts)).index('mowl-sync')
            return str(self.root.joinpath(*parts[idx + 1:]))
        return str(path)

    def claim_cleanup(self, ident):
        cursor = self.db.execute("UPDATE mowl_sync SET status='cleanup_in_progress', updated=CURRENT_TIMESTAMP WHERE strava_id=? AND status IN ('uploaded','awaiting_strava')", (str(ident),))
        self.db.commit()
        if cursor.rowcount == 1 and self.checkpoint:
            self.checkpoint()
        return cursor.rowcount == 1

    def update(self, ident, status, uploaded=None, detail=None):
        self.db.execute('UPDATE mowl_sync SET status=?,garmin_upload_id=?,detail=?,updated=CURRENT_TIMESTAMP WHERE strava_id=?', (status, str(uploaded) if uploaded else None, detail, str(ident)))
        self.db.commit()
        if self.checkpoint:
            self.checkpoint()


def uploaded_activity_id(response):
    if not isinstance(response, dict):
        raise ValueError('Unexpected Garmin upload response')
    result = response.get('detailedImportResult')
    if not isinstance(result, dict) or result.get('failures'):
        raise ValueError('Garmin did not confirm a successful import')
    successes = result.get('successes')
    if not isinstance(successes, list) or len(successes) != 1 or not isinstance(successes[0], dict):
        raise ValueError('Garmin did not return exactly one imported activity')
    ident = successes[0].get('internalId') or successes[0].get('activityId')
    if not ident or not str(ident).isdigit():
        raise ValueError('Garmin did not return an activity ID')
    return str(ident)


def fit_bytes(path):
    downloaded = Path(path).read_bytes()
    if downloaded.startswith(b'\x1f\x8b'):
        return gzip.decompress(downloaded)
    if zipfile.is_zipfile(io.BytesIO(downloaded)):
        with zipfile.ZipFile(io.BytesIO(downloaded)) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith('.fit') and not n.startswith('__MACOSX/')]
            if len(names) != 1:
                raise ValueError('Expected exactly one FIT file in Strava ZIP')
            return archive.read(names[0])
    return downloaded


def fit_device_identity(path):
    """Return a strict device/session identity, or fail closed if incomplete."""
    file_id = None
    session = None
    with fitdecode.FitReader(io.BytesIO(fit_bytes(path))) as reader:
        for message in reader:
            if not isinstance(message, fitdecode.FitDataMessage):
                continue
            if message.name in ('file_id', 'session'):
                values = {f.name: f.value for f in message.fields if f.value is not None}
                if message.name == 'file_id':
                    if file_id is not None:
                        raise ValueError('Multiple FIT file identifiers')
                    file_id = values
                else:
                    if session is not None:
                        raise ValueError('Multiple FIT sessions')
                    session = values
    if not file_id or not session or file_id.get('manufacturer') != 'garmin':
        raise ValueError('Not a Garmin activity with one session')
    serial = file_id.get('serial_number')
    created = file_id.get('time_created')
    start = session.get('start_time')
    elapsed = session.get('total_elapsed_time')
    if not serial or not created or not start or not isinstance(elapsed, (int, float)) or elapsed <= 0:
        raise ValueError('Missing device or session identity')
    return serial, created, start, round(elapsed, 2)


def verify_uploaded_metrics(detail, fit_path):
    """Require important metrics in Garmin's imported activity before replacement."""
    _, session = read_fit(fit_path)
    summary = detail.get('summaryDTO') if isinstance(detail, dict) else None
    if not isinstance(summary, dict):
        raise ValueError('Garmin did not return imported activity metrics')
    checks = {
        'total_distance': ('distance', 2.0),
        'total_calories': ('calories', 1.0),
        'total_training_effect': ('trainingEffect', 0.051),
        'total_anaerobic_training_effect': ('anaerobicTrainingEffect', 0.051),
        'training_load_peak': ('activityTrainingLoad', 1.0),
        'max_power': ('maxPower', 1.0),
        'max_cadence': ('maxBikeCadence', 1.0),
    }
    for field, (key, tolerance) in checks.items():
        expected = session.get(field)
        if expected is None:
            continue
        value = summary.get(key)
        if not isinstance(value, (int, float)) or abs(value - expected) > tolerance:
            raise ValueError(f'Imported Garmin metric {key} was not preserved')
    if not isinstance(summary.get('distance'), (int, float)):
        raise ValueError('Imported Garmin distance is unavailable')


def process(activity, match, api, downloader, journal, root, apply):
    ident = str(activity['id'])
    if not ident.isdigit():
        raise ValueError('Invalid Strava activity ID')
    if journal.get(ident):
        log.warning('Strava %s: already in journal (%s); no retry', ident, journal.get(ident)[0])
        return 'skipped'
    if not apply:
        log.info('Strava %s: would %s', ident, 'merge with Garmin ' + str(match['activityId']) if match else 'upload MOWL original')
        return 'planned'
    parent = Path(root) / ident
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder = Path(tempfile.mkdtemp(prefix='attempt-', dir=parent))
    original = downloader(activity, folder)
    if not original:
        raise RuntimeError('Strava original download failed')
    # Strava may return a gzip or ZIP instead of a bare FIT.
    downloaded = fit_bytes(original)
    original_fit = folder / 'mowl-original.fit'
    original_fit.write_bytes(downloaded)
    original_fit.chmod(0o600)
    read_fit(original_fit)
    output = folder / 'to-garmin.fit'
    garmin_id = match['activityId'] if match else None
    if match:
        data = api.download_activity(str(garmin_id), api.ActivityDownloadFormat.ORIGINAL)
        garmin_file = folder / 'garmin-original.zip'
        garmin_file.write_bytes(data)
        garmin_file.chmod(0o600)
        merge(original_fit, garmin_file, output)
    else:
        shutil.copyfile(original_fit, output)
    output.chmod(0o600)
    read_fit(output)
    if not journal.reserve(ident, garmin_id, folder):
        log.warning('Strava %s: another run already reserved this activity', ident)
        return 'skipped'
    try:
        uploaded = uploaded_activity_id(api.upload_activity(str(output)))
        detail = api.get_activity(uploaded)
        if not isinstance(detail, dict) or str(detail.get('activityId')) != uploaded:
            raise ValueError('Uploaded Garmin activity could not be verified')
        journal.update(ident, 'uploaded', uploaded)
    except Exception as exc:
        journal.update(ident, 'uncertain', detail=str(exc)[:500])
        raise RuntimeError('Upload may have happened; journal blocks automatic retry. Check Garmin before resolving.') from exc
    log.warning('Uploaded Garmin %s. Original Garmin and Strava activities have NOT been deleted.', uploaded)
    return 'uploaded'


def cleanup_uploaded(activity, api, journal, root, days, marker):
    """Remove verified duplicates only after checking imported Garmin metrics."""
    from strava_browser import recent_rides, delete_confirmed_watch_copy
    from strava import download_multiple_activities
    import pandas as pd

    ident = str(activity['id'])
    state = journal.get(ident)
    if not state or state[0] not in ('uploaded', 'awaiting_strava'):
        return
    _, original_id, uploaded_id = state
    if not original_id:
        journal.update(ident, 'complete', uploaded_id)
        return
    artifact_dir = journal.artifacts(ident)
    if not artifact_dir or not uploaded_id or original_id == uploaded_id:
        raise RuntimeError('Missing original or uploaded Garmin identity; cannot clean up')
    folder = Path(artifact_dir)
    mowl_file, garmin_file, merged_file = (folder / n for n in ('mowl-original.fit', 'garmin-original.zip', 'to-garmin.fit'))
    identity = fit_device_identity(garmin_file)
    uploaded = api.get_activity(uploaded_id)
    if str(uploaded.get('activityId')) != uploaded_id:
        raise RuntimeError('Cannot verify uploaded Garmin activity')
    verify_uploaded_metrics(uploaded, merged_file)
    original = api.get_activity(original_id)
    if str(original.get('activityId')) != original_id:
        raise RuntimeError('Cannot verify original Garmin activity')
    start = (original.get('summaryDTO') or {}).get('startTimeGMT')
    if not start or abs((timestamp(start) - identity[2]).total_seconds()) > 1:
        raise RuntimeError('Original Garmin activity start does not match backup')
    mowl_records, _ = read_fit(mowl_file)
    ride_day = min(mowl_records).astimezone().date()
    candidates = [x for x in recent_rides(days, marker, include_all=True)
                  if str(x['id']) != ident and marker.casefold() not in x['name'].casefold()
                  and abs((dt.date.fromisoformat(x['date']) - ride_day).days) <= 1]
    matched = []
    if candidates:
        with tempfile.TemporaryDirectory(dir=folder) as tmp:
            files = download_multiple_activities(pd.DataFrame(candidates), download_dir=tmp)
            if len(files) != len(candidates) or any(not item for item in files):
                raise RuntimeError('Could not inspect every possible Strava duplicate')
            for row, path in zip(candidates, files):
                try:
                    is_same = fit_device_identity(path) == identity
                except (ValueError, OSError):
                    is_same = False
                if is_same:
                    backup = folder / f"strava-watch-{row['id']}.fit"
                    backup.write_bytes(fit_bytes(path))
                    backup.chmod(0o600)
                    matched.append((row['id'], backup))
    if not matched:
        journal.update(ident, 'awaiting_strava', uploaded_id,
                       'Waiting for matching Garmin copy on Strava')
        log.warning('Strava %s: watch copy not yet identified; retaining Garmin original', ident)
        return
    # Mutations are reserved before starting. If the process stops or a response
    # is unclear, automatic retries stop rather than risk deleting the wrong item.
    if not journal.claim_cleanup(ident):
        log.warning('Strava %s: cleanup already claimed by another run', ident)
        return
    try:
        for duplicate_id, backup in matched:
            delete_confirmed_watch_copy(duplicate_id, ident, mowl_file, backup, garmin_file)
        api.delete_activity(original_id)
        try:
            api.get_activity(original_id)
        except Exception as exc:
            if '404' not in str(exc):
                raise RuntimeError('Cannot verify deletion of original Garmin activity') from exc
        else:
            raise RuntimeError('Original Garmin activity is still accessible')
        journal.update(ident, 'complete', uploaded_id)
    except Exception as exc:
        journal.update(ident, 'cleanup_uncertain', uploaded_id, str(exc)[:500])
        raise RuntimeError('Cleanup may be incomplete; automatic retry blocked') from exc
    log.info('Strava %s: verified watch copies and replaced Garmin original', ident)


def main(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Upload and clean up; default is dry run')
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--after', help='Only activities starting at or after this UTC timestamp')
    parser.add_argument('--settle-minutes', type=int, default=30)
    args = parser.parse_args(argv)
    if args.days <= 0 or args.settle_minutes < 0:
        parser.error('Invalid days or waiting time')
    if args.apply and os.getenv('MOWL_CLOUD_STATE') != '1':
        parser.error('Uploading requires the encrypted GitHub journal')
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    log.setLevel(logging.INFO)
    marker = os.getenv('MOWL_STRAVA_MARKER', 'MOWL').strip()
    if not marker:
        raise ValueError('MOWL activity marker must not be empty')
    after = timestamp(args.after) if args.after else None
    root = Path('outputs/mowl-sync')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    cloud = None
    token_file = None
    prior_token = None
    if args.apply:
        from cloud_sync_state import CloudState
        cloud = CloudState(root, os.environ['GITHUB_REPOSITORY'], os.environ['GH_TOKEN'], os.environ['MOWL_STATE_KEY'])
        cloud.restore()
        token_file = root / 'garmin-tokens' / 'garmin_tokens.json'
        if not token_file.is_file():
            raise RuntimeError('Encrypted state does not contain Garmin tokens')
        prior_token = token_file.read_bytes()
    from strava import download_multiple_activities
    from strava_browser import recent_rides
    from garmin_connect import get_api
    import pandas as pd

    activities = recent_rides(args.days, marker)
    api = get_api()
    if cloud and token_file.read_bytes() != prior_token:
        cloud.checkpoint()
        prior_token = token_file.read_bytes()
    now = dt.datetime.now(UTC)
    rows = api.get_activities_by_date((now.date() - dt.timedelta(days=args.days + 1)).isoformat(), (now.date() + dt.timedelta(days=1)).isoformat())
    journal = Journal(root / 'journal.sqlite3', checkpoint=cloud.checkpoint if cloud else None)
    failures = 0
    for activity in activities:
        try:
            previous = journal.get(activity['id'])
            if previous:
                if args.apply and previous[0] in ('uploaded', 'awaiting_strava'):
                    cleanup_uploaded(activity, api, journal, root, args.days, marker)
                else:
                    log.info('Activity is already recorded as %s', previous[0])
                continue
            with tempfile.TemporaryDirectory(dir=root) as tmp:
                files = download_multiple_activities(pd.DataFrame([activity]), download_dir=tmp)
                if not files or not files[0]:
                    raise RuntimeError('Could not download MOWL original')
                fit = Path(tmp) / 'validated.fit'
                fit.write_bytes(fit_bytes(files[0]))
                records, _ = read_fit(fit)
                begin, finish = min(records), max(records)
                if now - begin > dt.timedelta(days=args.days) or (after and begin < after):
                    continue
                if now < finish + dt.timedelta(minutes=args.settle_minutes):
                    log.info('Waiting for Garmin synchronization')
                    continue
                detail = dict(activity, start_date=begin.isoformat(), elapsed_time=(finish - begin).total_seconds())
                match = find_garmin_match(detail, rows)
                outcome = process(detail, match, api, lambda *_: fit, journal, root, args.apply)
                if outcome == 'uploaded':
                    cleanup_uploaded(detail, api, journal, root, args.days, marker)
        except Exception:
            failures += 1
            log.exception('Could not process activity')
    if cloud and token_file.read_bytes() != prior_token:
        cloud.checkpoint()
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
