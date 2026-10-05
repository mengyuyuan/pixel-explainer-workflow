from pathlib import Path
import json,math,subprocess,argparse
import numpy as np
import soundfile as sf
from scipy.signal import butter,sosfiltfilt
P=Path(__file__).parent;SR=48000
film=json.loads((P/'project.json').read_text(encoding='utf-8'));D=film['duration'];N=round(SR*D)
rng=np.random.default_rng(10603);fx=np.zeros((N,2),np.float64);events=[]
def env(a,attack=.003,release=.03):
 a=a.copy();n=len(a);ai=min(n//3,round(attack*SR));ri=min(n//2,round(release*SR))
 if ai:a[:ai]*=np.linspace(0,1,ai)**2
 if ri:a[-ri:]*=np.linspace(1,0,ri)**2
 return a
def tone(f,d,kind='triangle'):
 n=round(d*SR);f=np.linspace(*f,n) if isinstance(f,tuple) else np.full(n,f);ph=np.cumsum(f)/SR
 if kind=='pulse':y=np.where((ph%1)<.25,1.,-.333333)
 else:y=2/np.pi*np.arcsin(np.sin(2*np.pi*ph))
 return env(y,.003,min(.05,d*.6))
def chip_noise(d,hold=8,cutoff=3000):
 n=round(d*SR);a=np.repeat(rng.choice([-1.,-.5,0,.5,1.],size=math.ceil(n/hold)),hold)[:n]
 return sosfiltfilt(butter(2,cutoff,fs=SR,output='sos'),a)
def layers(items,d):
 z=np.zeros(round(d*SR))
 for t,a,g in items:
  i=round(t*SR);n=min(len(a),len(z)-i)
  if n>0:z[i:i+n]+=a[:n]*g
 return z
def sfx(kind):
 if kind=='discovery':
  return layers([(0,tone(523.25,.09,'pulse'),.65),(.10,tone(783.99,.10,'pulse'),.65),(.22,tone(1046.5,.16,'pulse'),.65)],.39)
 if kind=='flip':
  return env(layers([(0,env(chip_noise(.028,5,4800),.002,.017),1),(.053,env(chip_noise(.020,6,3800),.002,.014),.6),(.116,tone((180,78),.06),.7)],.19))
 if kind=='loom':
  return env(chip_noise(.075,18,1800),.001,.050)*.75+tone((float(rng.uniform(125,175)),72),.075)*.9
 if kind=='cloth':
  a=chip_noise(.36,16,1600);return env(a,.085,.16)*(1+np.sin(np.arange(len(a))/SR*2*np.pi*19)*.12)
 if kind=='step':
  return tone((112,56),.065)*.8+env(chip_noise(.065,24,1200),.001,.044)*.25
 if kind=='fail':
  a=tone((240,64),.32,'pulse');return env(a,.007,.16)
 if kind=='rewind':
  a=chip_noise(.29,6,3700);t=np.arange(len(a))/SR;return env(a*(.18+.82*(np.sin(2*np.pi*(14*t+12*t*t))>0)),.026,.105)
 if kind=='tick':return env(chip_noise(.026,4,4200),.001,.018)
 if kind=='gear':return layers([(0,tone((140,55),.09),.8),(.007,env(chip_noise(.065,4,4800),.002,.040),.45),(.068,tone(440,.036,'pulse'),.13)],.12)
 if kind=='upgrade':return layers([(0,tone(261.63,.32,'pulse'),.5),(.048,tone(392,.27,'pulse'),.35),(.096,tone(523.25,.23,'pulse'),.4)],.36)
 if kind=='ruler':return layers([(0,env(chip_noise(.15,10,2200),.025,.06),.7),(.143,tone((160,80),.076),.6)],.24)
 if kind=='stitch':return env(chip_noise(.037,9,1900),.003,.025)
 if kind=='paper':return layers([(0,env(chip_noise(.052,6,3300),.008,.028),.8),(.07,env(chip_noise(.071,8,2900),.012,.042),.5)],.15)
 if kind=='confirm':return layers([(0,tone(659.25,.10),.7),(.08,tone(987.77,.13),.35)],.22)
 if kind=='outro':return layers([(0,tone(392,.12),.5),(.13,tone(523.25,.15),.6),(.28,tone(659.25,.20),.4)],.51)
 raise KeyError(kind)
def add(kind,t,db=-24,pan=0,why=''):
 a=sfx(kind);a=sosfiltfilt(butter(2,4500,fs=SR,output='sos'),a)
 a*=10**(db/20)/max(float(np.sqrt(np.mean(a*a))),1e-8)
 # The brief noise transients retain their dynamics; do not force every event to one peak.
 i=round(t*SR);n=min(len(a),N-i)
 if n<=0:return
 theta=(pan+1)*np.pi/4;fx[i:i+n]+=a[:n,None]*np.array([np.cos(theta),np.sin(theta)])[None,:]
 events.append({'kind':kind,'start':round(t,4),'end':round(t+n/SR,4),'rmsDBFS':db,'pan':pan,'role':why,'source':'Original pulse/triangle/quantized-noise synthesis','listening':'unverified'})

parser=argparse.ArgumentParser();parser.add_argument('--voice',type=Path);args=parser.parse_args()
for event in json.loads((P/'sound-events.json').read_text(encoding='utf-8')):
 add(event['kind'],event['start'],event.get('rmsDBFS',-25),event.get('pan',0),event.get('role',''))
voice=np.zeros((N,2),dtype=np.float64)
if args.voice:
 source=args.voice.resolve(strict=True)
 converted=P/'build/voice-converted.wav'
 subprocess.run(['ffmpeg','-v','error','-i',str(source),'-ar',str(SR),'-ac','2','-c:a','pcm_f32le','-y',str(converted)],check=True)
 decoded,sr=sf.read(converted,dtype='float64',always_2d=True)
 if len(decoded)>N:raise ValueError('Narration exceeds project duration. Retiming is required; audio will not be truncated.')
 voice[:len(decoded)]=decoded
mix=voice*10**(film.get('voiceGainDB',0)/20)+fx*10**(film.get('effectsGainDB',0)/20)
sf.write(P/'build/mix-float.wav',mix,SR,subtype='FLOAT')
subprocess.run(['ffmpeg','-v','error','-i',str(P/'build/mix-float.wav'),'-af','alimiter=limit=0.84:level=false:latency=true:attack=5:release=60','-c:a','pcm_s24le','-y',str(P/'build/mix.wav')],check=True)
(P/'build/mix-float.wav').unlink()
report={'duration':D,'voiceProvided':bool(args.voice),'events':events,'listening':'unverified','externalAudio':bool(args.voice)}
(P/'build/sound-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'events':len(events),'voiceProvided':bool(args.voice),'duration':D}))
