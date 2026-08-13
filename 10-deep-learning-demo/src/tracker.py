"""Minimal IoU-based multi-object tracker (SORT-style, without the Kalman
filter): each frame's detected boxes are matched to existing tracks by
maximum IoU (greedy, above a threshold); unmatched detections start new
tracks; tracks unmatched for more than `max_missed` consecutive frames are
dropped. This is the 'tracking' half of the resume's 'Object Detection &
Tracking (Coursework)' bullet — detection (train.py/model.py) finds boxes
per frame, this assigns persistent identity across frames.
"""

from dataclasses import dataclass, field
from torchvision.ops import box_iou
import torch

IOU_MATCH_THRESHOLD = 0.3
MAX_MISSED_FRAMES = 3


@dataclass
class Track:
    track_id: int
    box: list[float]
    missed_frames: int = 0
    history: list[list[float]] = field(default_factory=list)

    def update(self, box: list[float]):
        self.box = box
        self.missed_frames = 0
        self.history.append(box)

    def mark_missed(self):
        self.missed_frames += 1


class IoUTracker:
    def __init__(self, iou_threshold: float = IOU_MATCH_THRESHOLD, max_missed: int = MAX_MISSED_FRAMES):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self.tracks: dict[int, Track] = {}
        self._next_id = 1

    def step(self, detections: list[list[float]]) -> dict[int, list[float]]:
        """detections: list of [xmin, ymin, xmax, ymax]. Returns
        {track_id: box} for all currently-alive tracks after this frame."""
        if not self.tracks:
            for box in detections:
                self._create_track(box)
            return self._alive_boxes()

        if not detections:
            for track in self.tracks.values():
                track.mark_missed()
            self._prune()
            return self._alive_boxes()

        track_ids = list(self.tracks.keys())
        track_boxes = torch.tensor([self.tracks[tid].box for tid in track_ids])
        det_boxes = torch.tensor(detections)
        iou_matrix = box_iou(track_boxes, det_boxes)

        matched_tracks = set()
        matched_dets = set()

        # Greedy matching: repeatedly take the single highest-IoU pair
        # remaining, until no pair clears the threshold. Simpler than the
        # Hungarian algorithm and adequate for this small-scale demo.
        pairs = []
        for i in range(iou_matrix.shape[0]):
            for j in range(iou_matrix.shape[1]):
                pairs.append((iou_matrix[i, j].item(), i, j))
        pairs.sort(reverse=True)

        for iou_val, i, j in pairs:
            if iou_val < self.iou_threshold:
                break
            if i in matched_tracks or j in matched_dets:
                continue
            self.tracks[track_ids[i]].update(detections[j])
            matched_tracks.add(i)
            matched_dets.add(j)

        for i, tid in enumerate(track_ids):
            if i not in matched_tracks:
                self.tracks[tid].mark_missed()

        for j, box in enumerate(detections):
            if j not in matched_dets:
                self._create_track(box)

        self._prune()
        return self._alive_boxes()

    def _create_track(self, box: list[float]):
        track = Track(track_id=self._next_id, box=box)
        track.history.append(box)
        self.tracks[self._next_id] = track
        self._next_id += 1

    def _prune(self):
        dead = [tid for tid, t in self.tracks.items() if t.missed_frames > self.max_missed]
        for tid in dead:
            del self.tracks[tid]

    def _alive_boxes(self) -> dict[int, list[float]]:
        return {tid: t.box for tid, t in self.tracks.items()}
