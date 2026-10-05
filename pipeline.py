"""Small cross-platform entry point; no private machine configuration required."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from settings import ROOT, load_config


def run(args):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True)


def prepare(voice):
    load_config()
    for program in ['ffmpeg', 'ffprobe']:
        if not shutil.which(program):
            raise RuntimeError(f'Install {program} and put it on PATH')
    for script in ['make_sprites.py', 'synthesize_sfx.py', 'build_scene.py']:
        run([sys.executable, ROOT / script])
    run([sys.executable, ROOT / 'mix_audio.py'] + (['--voice', voice] if voice else []))


def check(path):
    cfg = load_config()
    path = path.resolve(strict=True)
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)
    ], text=True))
    videos = [s for s in probe['streams'] if s['codec_type'] == 'video']
    audios = [s for s in probe['streams'] if s['codec_type'] == 'audio']
    if len(videos) != 1 or len(audios) != 1:
        raise ValueError('Expected exactly one video stream and one audio stream')
    v, a = videos[0], audios[0]
    expected_frames = round(900 / cfg['playbackRate'])
    if (v['width'], v['height'], v['r_frame_rate'], int(v.get('nb_frames', 0))) != (1920, 1080, '30/1', expected_frames):
        raise ValueError('Unexpected dimensions, frame rate, or frame count')
    expected_seconds = 30 / cfg['playbackRate']
    if abs(float(probe['format']['duration']) - expected_seconds) > .05:
        raise ValueError('Unexpected duration')
    if abs(float(a['duration']) - expected_seconds) > .05 or int(a['sample_rate']) != 48000:
        raise ValueError('Unexpected audio duration or sample rate')
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(path),
                              '-f', 'null', '-'], capture_output=True, text=True, check=True)
    if decoded.stderr.strip():
        raise ValueError(decoded.stderr)
    report = {'video': path.name, 'size': [1920, 1080], 'fps': 30, 'frames': expected_frames,
              'seconds': expected_seconds, 'audioSampleRate': 48000, 'fullDecode': 'passed',
              'normalSpeedReview': 'unverified', 'listening': 'unverified'}
    (ROOT / 'build').mkdir(exist_ok=True)
    (ROOT / 'build/technical-check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('prepare', help='Generate sprites, timeline and mixed audio')
    p.add_argument('--voice', type=Path)
    subs.add_parser('render', help='Lint and render the prepared example')
    p = subs.add_parser('check', help='Decode and check the rendered file; not a subjective review')
    p.add_argument('file', type=Path, nargs='?', default=ROOT / 'renders/elevator-sample.mp4')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.voice.resolve(strict=True) if args.voice else None)
    elif args.command == 'render':
        if not (ROOT / 'build/mix.wav').is_file() or not (ROOT / 'index.html').is_file():
            raise RuntimeError('Run python pipeline.py prepare first')
        npm = shutil.which('npm.cmd' if sys.platform == 'win32' else 'npm')
        if not npm:
            raise RuntimeError('Install Node.js 22+ and npm')
        run([npm, 'run', 'lint'])
        run([npm, 'run', 'render'])
    else:
        check(args.file)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
