#!/usr/bin/env python3
"""Native USDX import worker; reuse the installed singing_coach pipeline.

The UI receives atomic, small JSON snapshots, never model work on its render thread.
SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from coach_bridge import digest, export_reference, export_target, header
from coach_lyrics import align_words, build_lyrics, read_lyrics, render_lrc

AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"}
MAX_STATE_BYTES = 262144


class Cancelled(RuntimeError):
    """A cooperative cancellation, including a reaped model child."""


def cancel_path(state):
    return Path(state).with_suffix(".cancel")


def save_state(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {"schema_version": 1, "task_id": path.stem, **value}
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8"
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return value


def read_state(path):
    path = Path(path)
    if path.stat().st_size > MAX_STATE_BYTES:
        raise ValueError("invalid_state")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("invalid_state")
    return value


def run_child(command, log_path, cancelled, emit, timeout=3600, *, phase=None):
    """Own, terminate and reap exactly the child created by this worker."""
    with Path(log_path).open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        )
        started, previous_phase = time.monotonic(), ""
        try:
            while process.poll() is None:
                if cancelled():
                    raise Cancelled("cancelled")
                if time.monotonic() - started > timeout:
                    raise TimeoutError("model_timeout")
                directory = Path(log_path).parent
                current_phase = phase or (
                    "pitch"
                    if all(
                        (directory / n).is_file()
                        for n in ("vocals.wav", "instrumental.wav")
                    )
                    else "separating"
                )
                if current_phase != previous_phase:
                    emit(phase=current_phase)
                    previous_phase = current_phase
                time.sleep(0.2)
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            raise
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)


@contextmanager
def engine_lock(data_root):
    """Serialize native import workers; OS release also handles a crashed owner."""
    data_root.mkdir(parents=True, exist_ok=True)
    with (data_root / ".usdx-import.lock").open("a+b") as lock:
        lock.seek(0)
        if lock.read(1) == b"":
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError("engine_busy") from error
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


class CoachEngine:
    """Adapter to the existing installation, not a second separation algorithm."""

    def __init__(self, root, data_root=None):
        root = Path(root).resolve()
        if not (root / "src/singing_coach/reference.py").is_file():
            raise ValueError("engine_missing")
        sys.path.insert(0, str(root / "src"))
        from singing_coach.reference import ReferenceService, runtime_python
        from singing_coach.storage import SongStore

        self.root = root
        self.data_root = Path(data_root).resolve() if data_root else root / "data"
        self.store = SongStore(self.data_root)
        self.store.prepare()
        self.runtime = runtime_python()
        self.service = ReferenceService(self.data_root, recover=False)

    def prepare(self, audio, emit, cancelled):
        fingerprint = digest(audio)
        song = next(
            (
                s
                for s in self.store.list()
                if s.sha256 == fingerprint
                and (source := self.store.source_path(s)) is not None
                and digest(source) == fingerprint
            ),
            None,
        )
        if song is None:
            with audio.open("rb") as stream:
                song = self.store.import_file(stream, audio.name)
            if song.sha256 != fingerprint:
                raise ValueError("source_changed_during_import")
        if cancelled():
            raise Cancelled("cancelled")
        source = self.store.source_path(song)
        job, created = self.service.create(song.song_id, source)
        if created:
            if not self.runtime.is_file():
                job.status, job.phase, job.error = (
                    "failed",
                    "failed",
                    "audio_runtime_missing",
                )
                self.service.save(job)
                raise ValueError("audio_runtime_missing")

            def runner(source, directory, models):
                run_child(
                    [
                        str(self.runtime),
                        str(self.root / "tools/audio_worker.py"),
                        str(source),
                        str(directory),
                        str(models),
                    ],
                    directory / "worker.log",
                    cancelled,
                    emit,
                )

            self.service.runner = runner
            self.service.execute(job, source)
        if cancelled():
            raise Cancelled("cancelled")
        current = self.service.read(job.job_id)
        if current is not None and current.status in {"queued", "running"}:
            raise RuntimeError("reference_busy")
        verified, _ = self.verify(job.job_id)
        return verified

    def verify(self, job_id):
        job = self.service.read(job_id)
        if job is None or not self.service.valid(job):
            raise ValueError(job.error if job and job.error else "reference_invalid")
        return job.model_dump(mode="json"), self.service.root / job.job_id

    def confirm(self, job):
        current = self.service.read(job["job_id"])
        if current is None or not self.service.valid(current):
            raise ValueError("reference_changed")
        current.review_status = "reviewed"
        self.service.save(current)

    def prepare_lyrics(self, job, directory, emit, cancelled):
        return build_lyrics(
            self.root, self.data_root, job, directory, run_child, emit, cancelled
        )


def prepare(audio, state, engine):
    audio, state = Path(audio).resolve(), Path(state)
    cancelled = cancel_path(state).exists
    if cancelled():
        raise Cancelled("cancelled")
    if audio.suffix.casefold() not in AUDIO_SUFFIXES:
        raise ValueError("unsupported_audio")
    if not audio.is_file() or not 0 < audio.stat().st_size <= 500_000_000:
        raise ValueError("invalid_audio_size")
    current = {
        "status": "running",
        "phase": "importing",
        "error_code": "",
        "source_path": str(audio),
        "data_root": str(engine.data_root.resolve()),
    }

    def emit(**changes):
        current.update(changes)
        save_state(state, current)

    emit()
    job = engine.prepare(audio, emit, cancelled)
    if cancelled():
        raise Cancelled("cancelled")
    job, directory = engine.verify(job["job_id"])
    pitch = json.loads((directory / "pitch.json").read_text(encoding="utf-8"))
    notes = pitch["notes"]
    if not notes:
        raise ValueError("no_reliable_vocal_notes")
    lyrics_path = engine.prepare_lyrics(job, directory, emit, cancelled)
    if cancelled():
        raise Cancelled("cancelled")
    emit(phase="aligning")
    lyrics_hash = digest(lyrics_path)
    lyrics = read_lyrics(
        lyrics_path, job, job["duration_seconds"], expected_hash=lyrics_hash
    )
    _, alignment = align_words(notes, lyrics["words"], job["duration_seconds"])
    stride = max(1, math.ceil(len(notes) / 512))
    emit(
        status="ready",
        phase="ready",
        job_id=job["job_id"],
        song_id=job["song_id"],
        vocals_path=str((directory / "vocals.wav").resolve()),
        note_count=job["note_count"],
        duration_seconds=job["duration_seconds"],
        voiced_coverage=job["voiced_coverage"],
        lyrics_path=str(lyrics_path.resolve()),
        lyrics_sha256=lyrics_hash,
        lyrics_preview="".join(w["text"] for w in lyrics["words"])[:52],
        lyric_word_count=alignment["word_count"],
        low_confidence_word_count=alignment["low_confidence_word_count"],
        freestyle_word_count=alignment["freestyle_word_count"],
        chart_note_count=alignment["chart_note_count"],
        preview=[
            [n["start_seconds"], n["end_seconds"], n["midi"]] for n in notes[::stride]
        ],
    )
    return read_state(state)


def existing_export(target, job, title, artist, lyrics, lyrics_hash):
    """Recover a completed atomic publish, but never overwrite a different pack."""
    try:
        manifest = json.loads((target / "coach.json").read_text(encoding="utf-8"))
        text = (target / "song.txt").read_text(encoding="utf-8")
        if (
            manifest["reference_revision"] != job["job_id"]
            or manifest["source_sha256"] != job["source_sha256"]
            or manifest["review_status"] != "reviewed"
            or manifest.get("lyrics") != "asr_dtw_word_alignment"
            or "#TITLE:" + title not in text.splitlines()
            or "#ARTIST:" + artist not in text.splitlines()
        ):
            return False
        files = manifest["files"]
        audio = "audio" + Path(job["source_path"]).suffix.casefold()
        expected = {**job["artifacts"], audio: job["source_sha256"]}
        expected["lyrics.json"] = lyrics_hash
        expected["lyrics.lrc"] = hashlib.sha256(
            render_lrc(lyrics["words"]).encode("utf-8")
        ).hexdigest()
        if set(files) != {*expected, "song.txt"} or any(
            files[n] != sha for n, sha in expected.items()
        ):
            return False
        return all(
            Path(n).name == n
            and (target / n).is_file()
            and digest(target / n) == expected
            for n, expected in files.items()
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def publish(state, songs_root, title, artist, confirmation, engine):
    state, songs_root = Path(state), Path(songs_root).resolve()
    current = read_state(state)
    if (
        current.get("status") not in {"ready", "published"}
        or not confirmation
        or confirmation != current.get("job_id")
    ):
        raise ValueError("confirmation_required")
    if current.get("data_root") != str(engine.data_root.resolve()):
        raise ValueError("reference_changed")
    title, artist = header(title), header(artist) or "Unknown"
    if not title or len(title) > 120 or len(artist) > 120:
        raise ValueError("invalid_metadata")
    job, directory = engine.verify(confirmation)
    if not current.get("lyrics_path") or not current.get("lyrics_sha256"):
        raise ValueError("lyrics_required")
    lyrics_path = Path(current["lyrics_path"])
    lyrics = read_lyrics(
        lyrics_path,
        job,
        job["duration_seconds"],
        expected_hash=current["lyrics_sha256"],
    )
    target = export_target(job, songs_root, current["lyrics_sha256"])
    if target.exists():
        if not existing_export(
            target, job, title, artist, lyrics, current["lyrics_sha256"]
        ):
            raise FileExistsError("song_pack_exists")
    else:
        engine.confirm(job)
        save_state(state, {**current, "status": "running", "phase": "publishing"})
        target = export_reference(
            directory,
            songs_root,
            title,
            artist,
            lyrics_path=lyrics_path,
            require_lyrics=True,
            lyrics_sha256=current["lyrics_sha256"],
        )
    return save_state(
        state,
        {
            **current,
            "status": "published",
            "phase": "complete",
            "error_code": "",
            "output_path": str(target.resolve()),
            "song_file": str((target / "song.txt").resolve()),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "publish"))
    parser.add_argument("--coach-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--songs-root", type=Path)
    parser.add_argument("--title", default="")
    parser.add_argument("--artist", default="Unknown")
    parser.add_argument("--confirm-reference", default="")
    parser.add_argument(
        "--request", type=Path, help="UTF-8 metadata file from the native form"
    )
    args = parser.parse_args()
    previous = {}
    try:
        if args.action == "publish":
            previous = read_state(args.state)
        else:
            save_state(args.state, {"status": "running", "phase": "starting"})
        engine = CoachEngine(args.coach_root, args.data_root)
        with engine_lock(engine.data_root):
            if args.action == "prepare" and args.audio:
                prepare(args.audio, args.state, engine)
            elif args.action == "publish" and args.songs_root:
                if args.request:
                    form = read_state(args.request)
                    if not all(
                        isinstance(form.get(k), str)
                        for k in ("title", "artist", "confirmation")
                    ):
                        raise ValueError("invalid_request")
                    args.title, args.artist, args.confirm_reference = (
                        form[k] for k in ("title", "artist", "confirmation")
                    )
                publish(
                    args.state,
                    args.songs_root,
                    args.title,
                    args.artist,
                    args.confirm_reference,
                    engine,
                )
            else:
                raise ValueError("missing_arguments")
    except (
        OSError,
        ValueError,
        RuntimeError,
        ImportError,
        subprocess.SubprocessError,
    ) as error:
        cancelled = isinstance(error, Cancelled) or cancel_path(args.state).exists()
        code = "cancelled" if cancelled else str(error).split(":", 1)[0][:300]
        save_state(
            args.state,
            {
                **previous,
                "status": "cancelled"
                if cancelled
                else "ready"
                if previous.get("job_id")
                else "failed",
                "phase": "ready" if previous.get("job_id") else "failed",
                "error_code": code,
            },
        )
        print("IMPORT_ERROR: " + code, file=sys.stderr)
        return 2 if cancelled else 1
    print("IMPORT_OK: " + args.action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
