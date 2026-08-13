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
