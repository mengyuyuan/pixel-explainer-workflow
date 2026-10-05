import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('story',ROOT/'tools/story.py');story=importlib.util.module_from_spec(spec);spec.loader.exec_module(story)

class StoryTemplateTest(unittest.TestCase):
    def test_fresh_external_directory_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a project with spaces';story.init(p,'acting')
            self.assertEqual(story.config(p)['duration'],32)
            self.assertFalse(list(p.rglob('*.wav')))
            self.assertEqual(len(list((p/'assets').glob('*-acting.png'))),3)
            with self.assertRaises(ValueError):story.init(p,'capital')

    def test_capital_is_opt_in_and_invalid_timing_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'example';story.init(p,'capital');c=story.config(p)
            self.assertEqual(len(c['shots']),18);self.assertAlmostEqual(c['duration'],230.8)
            c['cues'][0]['end']=999;(p/'project.json').write_text(json.dumps(c),encoding='utf-8')
            with self.assertRaises(ValueError):story.config(p)

    def test_oversize_narration_is_rejected_not_truncated(self):
        import numpy as np
        import soundfile as sf
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'audio';story.init(p,'acting');(p/'build').mkdir()
            sf.write(p/'long.wav',np.zeros(48000*33),48000)
            r=subprocess.run([sys.executable,p/'audio.py','--voice',p/'long.wav'],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0);self.assertIn('exceeds project duration',r.stderr)
            self.assertFalse((p/'build/mix.wav').exists())

if __name__=='__main__':unittest.main()
