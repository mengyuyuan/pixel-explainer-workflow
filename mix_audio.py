"""Mix authored SFX with an optional, locally supplied narration file."""
import argparse
import json
import subprocess
from pathlib import Path
import soundfile as sf
from settings import ROOT, load_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--voice', type=Path, help='External narration; never copied into the repository')
    args = parser.parse_args()
    cfg = load_config()
    rate = cfg['playbackRate']
    duration = 30 / rate
    out = ROOT / 'build'
    out.mkdir(exist_ok=True)
    command = ['ffmpeg', '-y', '-nostdin', '-hide_banner', '-loglevel', 'error']
    if args.voice:
        voice = args.voice.resolve(strict=True)
        probe = json.loads(subprocess.check_output([
            'ffprobe', '-v', 'error', '-select_streams', 'a:0',
            '-show_entries', 'format=duration:stream=duration', '-of', 'json', str(voice)
        ], text=True))
        if not probe.get('streams'):
            raise ValueError('The voice file has no audio stream')
        seconds = probe['streams'][0].get('duration', probe.get('format', {}).get('duration'))
        if seconds is None or float(seconds) <= 0:
            raise ValueError('Cannot determine the voice duration')
        if float(seconds) + cfg['voiceOffsetSeconds'] > 30.001:
            raise ValueError('Narration plus offset exceeds the 30-second source timeline; edit timing before rendering')
        command += ['-i', str(voice), '-i', str(out / 'sfx-source.wav')]
        filters = (
            '[0:a:0]aformat=sample_rates=48000:channel_layouts=mono,'
            f"adelay={cfg['voiceOffsetSeconds'] * 1000},apad,atrim=0:30,"
            f"volume={cfg['voiceGainDB']}dB,pan=stereo|c0=c0|c1=c0,atempo={rate}[v];"
            f"[1:a:0]volume={cfg['sfxGainDB']}dB,atempo={rate}[s];"
            f'[v][s]amix=inputs=2:normalize=0,apad,atrim=0:{duration}[a]'
        )
    else:
        command += ['-i', str(out / 'sfx-source.wav')]
        filters = f"[0:a:0]volume={cfg['sfxGainDB']}dB,atempo={rate},apad,atrim=0:{duration}[a]"
    command += ['-filter_complex', filters, '-map', '[a]', '-ar', '48000',
                '-c:a', 'pcm_s24le', str(out / 'mix.wav')]
    subprocess.run(command, check=True)
    samples, _ = sf.read(out / 'mix.wav')
    peak = float(abs(samples).max())
    if peak >= .999:
        raise ValueError('Mix has insufficient headroom; lower sfxGainDB or voiceGainDB before rendering')
    events = json.loads((out / 'sound-events-source.json').read_text(encoding='utf-8'))
    for event in events['events']:
        event['start'] /= rate
        event['end'] /= rate
        event['rmsDBFS'] += cfg['sfxGainDB']
    events.update(playbackRate=rate, duration=duration, voiceProvided=bool(args.voice),
                  mixPeakLinear=peak, listening='unverified')
    (out / 'sound-events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Mixed {duration:g}s; narration={bool(args.voice)}; peak={peak:.4f}')
    if args.voice:
        print('The example subtitle/scene timing is fixed. Review and realign it to your own narration.')
    else:
        print('SFX-only demo: subtitles remain visible; no narration is included.')


if __name__ == '__main__':
    main()
