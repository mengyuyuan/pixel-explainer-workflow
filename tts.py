"""Optional VoxCPM launcher: usable CUDA first, then MPS, then CPU."""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def select_device(torch, requested='auto'):
    if requested != 'auto':
        # An explicit override should fail visibly, rather than change devices silently.
        torch.ones(1, device=requested).sum().item()
        return requested, []
    reasons = []
    for name, available in [
        ('cuda', lambda: torch.cuda.is_available()),
        ('mps', lambda: hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()),
    ]:
        try:
            if available():
                torch.ones(1, device=name).sum().item()
                return name, reasons
            reasons.append(f'{name}: unavailable in this PyTorch environment')
        except RuntimeError as exc:
            reasons.append(f'{name}: device probe failed ({type(exc).__name__})')
    return 'cpu', reasons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default='auto', help='auto (default), cuda, cuda:N, mps, or cpu')
    parser.add_argument('--probe', action='store_true', help='Report device only; no model is loaded')
    parser.add_argument('--model-path', type=Path)
    parser.add_argument('--text-file', type=Path, default=Path(__file__).parent/'narration.txt')
    parser.add_argument('--reference-audio', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent/'build/narration.wav')
    parser.add_argument('--control', default='')
    args = parser.parse_args()
    if args.device not in ('auto', 'cpu', 'mps', 'cuda') and not (args.device.startswith('cuda:') and args.device[5:].isdigit()):
        parser.error('device must be auto, cpu, mps, cuda, or cuda:N')
    try:
        import torch
    except ImportError:
        parser.error('Run this script in your VoxCPM/PyTorch environment; see docs/VOICE.md')
    device, reasons = select_device(torch, args.device)
    print(json.dumps({'device': device, 'policy': 'GPU first, CPU only when no usable GPU', 'probeNotes': reasons}), flush=True)
    if args.probe:
        return
    if not args.model_path or not args.model_path.is_dir():
        parser.error('--model-path must point to an existing local VoxCPM model')
    if args.reference_audio and not args.reference_audio.is_file():
        parser.error('--reference-audio does not exist')
    text = args.text_file.read_text(encoding='utf-8-sig').strip()
    if not text:
        parser.error('text file is empty')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'voxcpm.cli', 'clone' if args.reference_audio else 'design',
               '--device', device, '--model-path', str(args.model_path.resolve()), '--text', text,
               '--cfg-value', '2', '--inference-timesteps', '20', '--normalize', '--no-denoiser',
               '--local-files-only', '--output', str(args.output.resolve())]
    if args.reference_audio:
        command += ['--reference-audio', str(args.reference_audio.resolve())]
    if args.control:
        command += ['--control', args.control]
    # Model/data errors and OOM are reported. They are not disguised as absent hardware.
    subprocess.run(command, check=True)


if __name__ == '__main__':
    main()
