"""Create and render a portable pixel-story project from the public template."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(argv,cwd=None,env=None):
    subprocess.run([str(a) for a in argv],cwd=cwd,env=env,check=True)

def init(path,example):
    if path.exists():raise ValueError('Choose a new project directory; existing files will not be overwritten.')
    shutil.copytree(ROOT/'templates/pixel-story',path)
    if example=='capital':
        for name in ['scenes.js','project.json','sound-events.json']:shutil.copy2(ROOT/'examples/capital-story'/name,path/name)
    print(f'Created {path}. Edit project.json, scenes.js and sound-events.json for your story.')

def config(path):
    c=json.loads((path/'project.json').read_text(encoding='utf-8'))
    for key in ['width','height','fps']:
        if not isinstance(c[key],int) or c[key]<=0:raise ValueError(f'{key} must be a positive integer')
    if c['width']%2 or c['height']%2:raise ValueError('H.264 output dimensions must be even')
    if c['fps']>120 or c['duration']<=0:raise ValueError('Invalid duration or frame rate')
    if abs(c['duration']*c['fps']-round(c['duration']*c['fps']))>1e-5:raise ValueError('Duration must contain a whole number of frames')
    for item in c.get('cues',[]):
        if not 0<=item['start']<item['end']<=c['duration']:raise ValueError('Subtitle interval outside project')
    events=json.loads((path/'sound-events.json').read_text(encoding='utf-8'))
    for e in events:
        if not 0<=e['start']<c['duration'] or not -1<=e.get('pan',0)<=1:raise ValueError('Sound event outside timeline or invalid pan')
    return c

def prepare(path,voice=None):
    c=config(path)
    (path/'build').mkdir(exist_ok=True);(path/'vendor').mkdir(exist_ok=True)
    gsap=ROOT/'node_modules/gsap/dist/gsap.min.js'
    if not gsap.exists():raise ValueError('Run npm ci in the repository first.')
    shutil.copy2(gsap,path/'vendor/gsap.min.js')
    run([sys.executable,path/'prepare_sprites.py'])
    actors=json.loads((path/'assets/performers.json').read_text(encoding='utf-8'))
    (path/'performer-data.js').write_text('const PERFORMERS='+json.dumps(actors,ensure_ascii=False)+';',encoding='utf-8')
    atlas=json.loads((path/'assets/props-atlas.json').read_text(encoding='utf-8'))
    (path/'atlas-data.js').write_text('const ATLAS='+json.dumps({'props':atlas})+';',encoding='utf-8')
    (path/'film-data.js').write_text('const FILM='+json.dumps(c,ensure_ascii=False)+';',encoding='utf-8')
    html=(path/'index.html.in').read_text(encoding='utf-8')
    for k in ['width','height','fps','duration']:html=html.replace('{{'+k+'}}',str(c[k]))
    (path/'index.html').write_text(html,encoding='utf-8')
    run([sys.executable,path/'audio.py']+(['--voice',voice] if voice else []))
    print('Prepared. Narration is optional; supplied audio must fit the reviewed timeline.')

def render(path,output=None,temp_dir=None):
    c=config(path)
    if not (path/'index.html').exists():raise ValueError('Run prepare first.')
    binary=ROOT/'node_modules/.bin'/('hyperframes.cmd' if sys.platform=='win32' else 'hyperframes')
    output=output or path/'renders/film.mp4';output.parent.mkdir(parents=True,exist_ok=True)
    probes=[];encoder=None
    for enc in ['h264_nvenc','h264_qsv','h264_amf','h264_videotoolbox']:
        r=subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c=black:s={c["width"]}x{c["height"]}:r={c["fps"]}:d=0.1','-c:v',enc,'-f','null','-'],capture_output=True,text=True)
        probes.append({'encoder':enc,'success':r.returncode==0,'reason':r.stderr[-1500:]})
        if r.returncode==0:encoder=enc;break
    env=os.environ.copy()
    if temp_dir:temp_dir.mkdir(parents=True,exist_ok=True);env['TEMP']=env['TMP']=str(temp_dir)
    command=[binary,'render']+(['--gpu'] if encoder else [])+['--fps',c['fps'],'--quality','draft','--crf','16','--workers','1','--strict','--output',output]
    (path/'build/render-settings.json').write_text(json.dumps({'hardwareEncoderAvailable':encoder,'probes':probes,'gpuRequested':bool(encoder),'output':str(output),'note':'HyperFrames performs its own final encoder/browser GPU selection.'},indent=2),encoding='utf-8')
    run(command,cwd=path,env=env)

def check(path,video):
    c=config(path);video=video or path/'renders/film.mp4'
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
    v=next(s for s in data['streams'] if s['codec_type']=='video');a=next(s for s in data['streams'] if s['codec_type']=='audio')
    expected=(c['width'],c['height'],f'{c["fps"]}/1',round(c['duration']*c['fps']))
    actual=(v['width'],v['height'],v['r_frame_rate'],int(v['nb_frames']))
    if actual!=expected or abs(float(data['format']['duration'])-c['duration'])>.05:raise ValueError(f'Unexpected video properties: {actual}')
    if int(a['sample_rate'])!=48000:raise ValueError('Unexpected audio sample rate')
    run(['ffmpeg','-v','error','-xerror','-i',video,'-f','null','-'])
    report={'size':[c['width'],c['height']],'fps':c['fps'],'duration':c['duration'],'frames':actual[3],'fullDecode':'passed','normalSpeedReview':'unverified','listening':'unverified'}
    (path/'build/technical-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ['init','prepare','render','check']:
        s=sub.add_parser(name);s.add_argument('project',type=Path)
        if name=='init':s.add_argument('--example',choices=['acting','capital'],default='acting')
        if name=='prepare':s.add_argument('--voice',type=Path)
        if name in ['render','check']:s.add_argument('--output',type=Path)
        if name=='render':s.add_argument('--temp-dir',type=Path)
    a=parser.parse_args();p=a.project.resolve()
    if a.command=='init':init(p,a.example)
    elif a.command=='prepare':prepare(p,a.voice.resolve(strict=True) if a.voice else None)
    elif a.command=='render':render(p,a.output.resolve() if a.output else None,a.temp_dir.resolve() if a.temp_dir else None)
    else:check(p,a.output.resolve() if a.output else None)

if __name__=='__main__':
    try:main()
    except (ValueError,FileNotFoundError,subprocess.CalledProcessError) as e:print(f'Error: {e}',file=sys.stderr);sys.exit(1)
