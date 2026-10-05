#!/bin/bash
# Prepend a 1 s designed cover (with 1 s of silence, so the sync is unchanged), embed the cover as attached_pic, and
# export 16:9 / 4:3 / 3:4 cover PNGs. Keep the cover content inside x 240–1680 so the 4:3 crop works.
# Usage: add_cover.sh video.mp4 cover-16x9.png out.mp4 [cover-3x4.png]
set -e
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || { echo "$(basename "$0"): needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg; Debian/Ubuntu: apt install ffmpeg)"; exit 2; }
IN=$1; COVER=$2; OUT=$3; PORTRAIT=$4
[ -f "$IN" ] && [ -f "$COVER" ] || { echo "usage: add_cover.sh video.mp4 cover-16x9.png out.mp4 [cover-3x4.png]"; exit 1; }
W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$IN")
H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$IN")
FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$IN")
TMP=$(mktemp -d)
ffmpeg -v error -y -loop 1 -framerate "$FPS" -t 1 -i "$COVER" -i "$IN" -f lavfi -t 1 -i anullsrc=r=44100:cl=stereo \
  -filter_complex "[0:v]scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},fps=${FPS},format=yuv420p,setsar=1[c];[1:v]fps=${FPS},format=yuv420p,setsar=1[m];[c][m]concat=n=2:v=1:a=0[v];[1:a]aresample=44100,aformat=channel_layouts=stereo[s];[2:a][s]concat=n=2:v=0:a=1[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 18 -maxrate 16M -bufsize 32M -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart "$TMP/lead.mp4"
ffmpeg -v error -y -i "$TMP/lead.mp4" -i "$COVER" -map 0 -map 1 -c copy -c:v:1 png -disposition:v:1 attached_pic -movflags +faststart "$OUT"
DIR=$(dirname "$OUT")
cp "$COVER" "$DIR/cover-16x9.png"
ffmpeg -v error -y -i "$COVER" -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,crop=1440:1080:240:0" "$DIR/cover-4x3.png"
if [ -n "$PORTRAIT" ]; then cp "$PORTRAIT" "$DIR/cover-3x4.png"; else ffmpeg -v error -y -i "$COVER" -vf "scale=-2:1440,crop=1080:1440" "$DIR/cover-3x4.png"; fi
rm -rf "$TMP"
ffprobe -v error -show_entries format=duration,size -of compact "$OUT"
echo "covers: $DIR/cover-16x9.png $DIR/cover-4x3.png $DIR/cover-3x4.png"
