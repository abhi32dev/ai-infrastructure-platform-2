import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tracker import IoUTracker


def test_single_object_keeps_same_id_across_frames():
    tracker = IoUTracker()
    frames = [[[10 + 5 * f, 10, 50 + 5 * f, 50]] for f in range(5)]
    ids_over_time = []
    for detections in frames:
        alive = tracker.step(detections)
        ids_over_time.append(set(alive.keys()))
    assert all(ids == {1} for ids in ids_over_time)


def test_new_object_gets_new_id():
    tracker = IoUTracker()
    tracker.step([[10, 10, 50, 50]])
    alive = tracker.step([[10, 10, 50, 50], [200, 200, 240, 240]])
    assert len(alive) == 2


def test_track_dropped_after_max_missed_frames():
    tracker = IoUTracker(max_missed=2)
    tracker.step([[10, 10, 50, 50]])
    tracker.step([])  # missed 1
    tracker.step([])  # missed 2
    alive = tracker.step([])  # missed 3 -> should be pruned now
    assert alive == {}


def test_spurious_one_frame_detection_does_not_grow_history():
    tracker = IoUTracker(max_missed=3)
    tracker.step([[10, 10, 50, 50]])            # real object, frame 0
    tracker.step([[15, 10, 55, 50]])             # real object, frame 1
    tracker.step([[20, 10, 60, 50], [500, 500, 510, 510]])  # + spurious detection, frame 2
    tracker.step([[25, 10, 65, 50]])             # spurious never re-detected, frame 3

    spurious_tracks = [t for t in tracker.tracks.values() if len(t.history) == 1]
    assert len(spurious_tracks) == 1
    assert spurious_tracks[0].box == [500, 500, 510, 510]


def test_non_overlapping_detection_does_not_match_existing_track():
    tracker = IoUTracker(iou_threshold=0.3)
    tracker.step([[10, 10, 50, 50]])
    # a box far away should NOT be matched to the existing track
    alive = tracker.step([[500, 500, 540, 540]])
    assert len(alive) == 2  # original track (now missed) + new track


# --- Negative / edge cases ---

def test_empty_first_frame_does_not_crash():
    tracker = IoUTracker()
    alive = tracker.step([])
    assert alive == {}


def test_track_recovers_identity_after_brief_occlusion():
    """Positive counterpart to test_track_dropped_after_max_missed_frames:
    an object that's briefly missing (within max_missed) but reappears
    should be re-matched to its EXISTING track, not assigned a new ID —
    that's the actual point of tolerating missed frames at all."""
    tracker = IoUTracker(max_missed=3)
    tracker.step([[10, 10, 50, 50]])           # frame 0: track 1 created
    tracker.step([])                            # frame 1: occluded, missed=1
    tracker.step([])                            # frame 2: occluded, missed=2
    alive = tracker.step([[13, 10, 53, 50]])    # frame 3: reappears, close to last known box
    assert list(alive.keys()) == [1]            # same track ID, not a new one


def test_two_detections_do_not_both_match_the_same_track():
    """Regression guard on the greedy matching: if two new detections
    both overlap one existing track, only ONE should claim it — the other
    must start a new track, never both updating (and silently
    overwriting) the same track object."""
    tracker = IoUTracker(iou_threshold=0.1)
    tracker.step([[10, 10, 50, 50]])
    # two detections, both overlapping the existing track region
    alive = tracker.step([[12, 10, 52, 50], [14, 10, 54, 50]])
    assert len(alive) == 2  # one matched the existing track, one started a new track
