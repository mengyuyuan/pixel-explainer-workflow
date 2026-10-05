import pathlib,json,numpy as np,soundfile as sf
from scipy.signal import butter,sosfiltfilt
p=pathlib.Path(__file__).parent;a=p/'build';a.mkdir(exist_ok=True);SR=48000;N=30*SR
fx=np.zeros((N,2),np.float64);events=[];rng=np.random.default_rng(105)
def osc(freq,duration,kind='triangle'):
 n=round(duration*SR);f=np.linspace(*freq,n) if isinstance(freq,tuple) else np.full(n,freq)
 phase=np.cumsum(f)/SR;y=np.zeros(n)
 if kind=='triangle':
  for k in [1,3,5,7]:y+=(-1)**((k-1)//2)*np.sin(2*np.pi*k*phase)/k**2
 elif kind=='pulse':
  for k in [1,3,5,7]:y+=np.sin(2*np.pi*k*phase)/k
 else:y=np.sin(2*np.pi*phase)
 return y
def envelope(x,attack=.008,release=.08):
 n=len(x);ai=min(round(attack*SR),n//2);ri=min(round(release*SR),n//2);y=x.copy()
 if ai:y[:ai]*=np.sin(np.linspace(0,np.pi/2,ai))**2
 if ri:y[-ri:]*=np.cos(np.linspace(0,np.pi/2,ri))**2
 return y
def put(name,t,x,db,pan=0,role='contact'):
 x=sosfiltfilt(butter(2,3200,fs=SR,output='sos'),x)
 rms=float(np.sqrt(np.mean(x*x)));gain=10**(db/20)/max(rms,1e-8);x*=gain
 # Constant-energy pan: unity center perceived loudness, no single-channel peak jump.
 pan=np.linspace(*pan,len(x)) if isinstance(pan,tuple) else np.full(len(x),pan)
 stereo=x[:,None]*np.stack([np.sqrt((1-pan)/2),np.sqrt((1+pan)/2)],axis=1)
 st=round(t*SR);fx[st:st+len(x)]+=stereo
 events.append({'id':name,'start':t,'end':t+len(x)/SR,'source':'original deterministic 8-bit synthesis following upstream SKILL.md section 7','role':role,'rmsDBFS':db,'pan':pan[[0,-1]].tolist(),'audition':'unverified'})
def blip(freq,d=.12):return envelope(osc(freq,d,'triangle'),.005,min(.09,d*.65))
def step(i):
 d=.085;n=round(d*SR);tt=np.arange(n)/SR
 y=.85*osc((145+i*12,72),d,'triangle')+.13*rng.standard_normal(n)
 return envelope(y*np.exp(-tt*33),.003,.035)
for i,t in enumerate(np.arange(.62,2.56,.28)):
 put(f'foot-in-{i}',float(t),step(i%2),-27,pan=-.35+.1*i,role='foot landing synchronized to 7 Hz walk poses')
put('door-slide-close',2.75,envelope(osc((230,110),.72,'pulse')*(.75+.25*np.sin(np.arange(round(.72*SR))/SR*2*np.pi*24)),.12,.19),-28,pan=(0,.2),role='sliding door body')
put('door-latch',3.49,blip((250,130),.15),-24,role='door contact')
put('discover-shaft',4.47,envelope(np.concatenate([blip(330,.12),blip(494,.18)]),.006,.08),-25,role='new view discovery')
put('cable-reveal',6.40,envelope(osc((155,440),.62),.06,.22),-27,pan=(-.2,.25),role='diagram reveal gesture')
put('counterweight-lock',9.20,blip((240,150),.18),-26,pan=.4,role='counterweight identification lands')
def motor(d):
 tt=np.arange(round(d*SR))/SR;u=tt/d
 freq=95+90*np.sin(np.pi*u)**2;phase=np.cumsum(freq)/SR
 y=np.sin(2*np.pi*phase)+.22*np.sin(6*np.pi*phase)
 ticks=(np.sin(2*np.pi*(9*tt+2*tt**2))*.5+.5)**6
 y=(y+.20*ticks*osc(390,d,'pulse'))*(.7+.3*np.sin(np.pi*u))
 return envelope(y,.22,.4)
put('lift-opposed-travel',10.10,motor(2.05),-27.5,pan=(-.2,.1),role='acceleration, mechanical travel, deceleration')
for i,t in enumerate([13.54,13.74,13.94,14.14]):put(f'weight-pair-{i}',t,blip((392+i*35,330+i*25),.15),-26,role='actual contact of opposing units')
put('residual-remains',14.56,blip(294,.23),-27,pan=-.2,role='remaining difference reading point')
put('camera-to-motor',17.52,envelope(osc((160,310),.67),.08,.3),-28,pan=(0,.35),role='same machine camera reveal')
put('friction',20.35,envelope(osc((175,145),.36,'pulse')*.65+.10*rng.standard_normal(round(.36*SR)),.045,.16),-29,pan=.25,role='brief friction illustration')
put('controlled-speed',21.43,motor(1.75),-26.5,pan=(.2,-.15),role='motor speed ramp and release')
put('arrive',25.76,np.concatenate([blip(523.25,.19),np.zeros(round(.06*SR)),blip(392,.32)]),-24,role='arrival before exit')
put('door-open',25.86,envelope(osc((110,220),.53,'triangle'),.1,.20),-28,role='opening door body')
for i,t in enumerate([26.4,26.68,26.96,27.24,27.52]):put(f'foot-out-{i}',t,step(i%2),-27,pan=.1-i*.1,role='exit footsteps')
sf.write(a/'sfx-source.wav',fx,SR,subtype='PCM_24')
(a/'sound-events-source.json').write_text(json.dumps({'sourceDuration':30,'sampleRate':SR,'music':False,'events':events,'listening':'unverified'},ensure_ascii=False,indent=2),encoding='utf-8')
print('Synthesized',len(events),'8-bit events')
