"""Shared timeline and mix settings. Source choreography is 30 seconds."""
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load_config():
    cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    bounds={'playbackRate':(.5,2),'sfxGainDB':(-40,12),'voiceGainDB':(-40,0),'voiceOffsetSeconds':(0,10)}
    if set(cfg)!=set(bounds): raise ValueError('config.json contains missing or unknown settings')
    for key,(lo,hi) in bounds.items():
        v=cfg[key]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:
            raise ValueError(f'{key} must be a finite number in [{lo}, {hi}]')
    # A video has whole frames. Reject ambiguous durations instead of silently rounding.
    if abs(900/cfg['playbackRate']-round(900/cfg['playbackRate']))>1e-6:
        raise ValueError('playbackRate must give a whole frame count at 30 fps (900 / rate)')
    return cfg
