"""Synthetic tracking demo: two objects move across a sequence of frames
(one steadily left-to-right, one appearing mid-sequence then leaving), and
a third spurious one-frame false detection is injected to prove it does
NOT get a persistent track (a real detector's occasional false positive
shouldn't spawn a stable-looking track).
"""

from tracker import IoUTracker


def make_moving_box(x_start, y, w=40, h=80, dx=15, frame=0):
    x = x_start + dx * frame
    return [x, y, x + w, y + h]


def build_synthetic_sequence(n_frames=8):
    frames = []
    for f in range(n_frames):
        boxes = [make_moving_box(50, 100, dx=15, frame=f)]  # object A: present every frame
        if 2 <= f <= 6:
            boxes.append(make_moving_box(300, 200, dx=-10, frame=f - 2))  # object B: frames 2-6 only
        if f == 4:
            boxes.append([500, 500, 510, 510])  # spurious one-frame false detection
        frames.append(boxes)
    return frames


def run_tracking_demo():
    tracker = IoUTracker()
    frames = build_synthetic_sequence()

    for frame_idx, detections in enumerate(frames):
        alive = tracker.step(detections)
        print(f"frame {frame_idx}: {len(detections)} detections -> "
              f"alive tracks: {[(tid, [round(c) for c in box]) for tid, box in sorted(alive.items())]}")

    print("\nTrack summary (id -> number of frames it appeared in):")
    for tid, track in sorted(tracker.tracks.items()):
        print(f"  track {tid}: {len(track.history)} frames")


if __name__ == "__main__":
    run_tracking_demo()
