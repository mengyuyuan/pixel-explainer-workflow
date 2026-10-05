#!/bin/bash
# QA a rendered MP4 the way the preview can't: probe streams, scan every frame for black/blank frames, and extract a
# contact sheet of frames pulled one by one with ffmpeg -ss (renders can differ from HyperFrames snapshots).
# Usage: qa_video.sh video.mp4 [out_dir] [n_frames=12]
set -e
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || { echo "$(basename "$0"): needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg; Debian/Ubuntu: apt install ffmpeg)"; exit 2; }
V=$1; OUT=${2:-qa}; N=${3:-12}
[ -f "$V" ] || { echo "usage: qa_video.sh video.mp4 [out_dir] [n_frames]"; exit 1; }
mkdir -p "$OUT"
echo "== streams"; ffprobe -v error -show_entries format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate:stream_disposition=attached_pic -of compact "$V"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
echo "== black / blank frames (Y average < 20)"
ffmpeg -v error -i "$V" -map 0:v:0 -vf "scale=64:36,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-" -f null - 2>/dev/null \
  | awk -F= '/YAVG/{v=$2+0; n++; if(min==""||v<min)min=v; if(v<20){low++; if(low<=5) printf "  dark frame #%d (Y=%.1f)\n", n-1, v}} END{printf "  frames %d · min Y %.1f · dark frames %d\n", n, min, low+0}'
echo "== first frame (should be a designed cover, not black)"
ffmpeg -v error -y -ss 0 -i "$V" -map 0:v:0 -frames:v 1 "$OUT/first-frame.png" && echo "  $OUT/first-frame.png"
echo "== contact sheet ($N frames, each extracted separately)"
rm -f "$OUT"/f-*.png
for i in $(seq 0 $((N - 1))); do
  T=$(python3 -c "print(round($DUR * ($i + 0.5) / $N, 3))")
  ffmpeg -v error -y -ss "$T" -i "$V" -map 0:v:0 -frames:v 1 -vf "scale=480:-2" "$OUT/f-$(printf %02d $i).png"
done
COLS=4; ffmpeg -v error -y -i "$OUT/f-%02d.png" -filter_complex "tile=${COLS}x$(( (N + COLS - 1) / COLS ))" -frames:v 1 "$OUT/contact-sheet.png"
echo "  $OUT/contact-sheet.png  (look at it: subtitles, AI label, faces, no leaked frames)"
echo "== loudness"; ffmpeg -hide_banner -nostats -i "$V" -map 0:a:0 -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume" | sed 's/^.*\] /  /' || echo "  (no audio)"
