import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from music_generation_claim_audit import audit
from music_generation_claim_audit.__main__ import main
from music_generation_claim_audit.phrases import MUSICGENERATION, NOMUSICGENERATION, GENERIC_NAMES, DEDICATED_CLASSES

class OracleTests(unittest.TestCase):
    def test_phrases(self):
        self.assertEqual(MUSICGENERATION, ['music generation', 'music-generation', 'musicgeneration', 'generate music', 'generates music', 'generating music', 'generated music', 'compose music', 'composes music', 'composing music', 'music composition', 'ai music', 'ai-generated music', 'ai generated music', 'music composer', 'music composers', 'music generation model', 'music generation models', 'music generator', 'music generators', 'song generation', 'generate songs', 'generates songs', 'song generator', 'melody generation', 'generate melodies', 'melody generator', 'music synthesis', 'synthesize music', 'music synthesizer', 'text to music', 'text-to-music', 'music from text', 'music creation', 'create music', 'creates music', 'music creation tool', 'music generation api', 'music generation feature', 'music generation support', 'supports music generation', 'music generation capability', 'music generation tool', 'music generation system', 'music generation engine', 'music generation framework', 'music generation library', 'music generation pipeline', 'music generation algorithm', 'music generation function'])
        self.assertEqual(NOMUSICGENERATION, ['does not generate music', 'do not generate music', "doesn't generate music", "don't generate music", 'no music generation', 'without music generation', 'never generates music', 'does not support music generation', 'music generation not supported', 'music generation unsupported', 'no music generation support', 'lacks music generation', 'missing music generation', 'music generation disabled', 'no music generation model', 'without music generation support', 'does not provide music generation', 'no automatic music generation', 'music generation not available', 'no music generation capability', 'does not perform music generation', 'never performs music generation', 'does not compose music', 'without a music generation model'])
    def test_generic_names(self):
        self.assertEqual(GENERIC_NAMES, ['generate_music', 'music_generate', 'compose_music', 'music_compose', 'create_music', 'music_create', 'generate_song', 'song_generate', 'compose_song', 'song_compose', 'generate_melody', 'melody_generate', 'compose_melody', 'melody_compose', 'synthesize_music', 'music_synthesize', 'generate_track', 'track_generate', 'create_song', 'generate_tune', 'compose_tune', 'generate_music_track', 'music_track_generate', 'create_melody'])
    def test_dedicated_classes(self):
        self.assertEqual(DEDICATED_CLASSES, ['MusicgenForConditionalGeneration', 'MusicGen', 'MusicGenerator', 'MusicComposer', 'MusicLM', 'RiffusionPipeline', 'StableAudioPipeline'])

class EvidenceTests(unittest.TestCase):
    pass

POSITIVE = {
    'generic_expression_base': 'factory().generate_music()',
    'generic_subscript_base': 'clients[0].generate_music()',
    'pipeline_assigned': 'from transformers import pipeline\np = pipeline("text-to-audio", model="facebook/musicgen-small")\np("song")',
    'pipeline_chained': 'import transformers as tf\ntf.pipeline("text-to-audio", "MUSIC-model")("song")',
    'pipeline_alias': 'from transformers import pipeline as build\np=build("text-to-audio", model="music")\np("x")',
    'dedicated_assigned': 'from vendor import MusicGen as MG\np=MG()\np.generate("x")',
    'dedicated_chained': 'MusicGen()("x")',
    'dedicated_attribute': 'import vendor as v\nv.MusicGen().run()',
    'audiocraft_assigned': 'from audiocraft.models import AudioGen as AG\np=AG()\np("x")',
    'audiocraft_chained': 'import audiocraft as ac\nac.models.AudioGen().run()',
    'magenta_assigned': 'from magenta.models import Melody as M\np=M()\np.generate()',
    'magenta_chained': 'import magenta as mg\nmg.models.Melody().generate()',
    'suno_assigned_generate': 'from vendor import SunoClient as S\np=S()\np.generate()',
    'suno_assigned_create': 'p=SunoApi()\np.create()',
    'suno_chained_generate': 'SunoAPI().generate()',
    'suno_chained_create': 'import suno as s\ns.Suno().create()',
}
NEGATIVE = {
    'imports': 'import transformers, audiocraft, magenta, suno, torch, tensorflow',
    'audio_pipeline': 'from transformers import pipeline\np=pipeline("text-to-audio", model="audioldm")\np("x")',
    'audio_pipeline_lone': 'from transformers import pipeline\npipeline("text-to-audio", model="audioldm")',
    'audio_pipeline_missing_model': 'from transformers import pipeline\npipeline("text-to-audio")("x")',
    'audio_ldm': 'from diffusers import AudioLDMPipeline\np=AudioLDMPipeline()\np("x")',
    'tts': 'import bark\nbark.generate_audio("x")',
    'speech_synthesis': 'import tortoise\ntortoise.tts("x")',
    'speech_recognition': 'import speech\nspeech.recognize("x")',
    'transcription': 'x.transcribe_music()',
    'chords': 'x.detect_chords()',
    'beats': 'x.track_beats()',
    'tempo': 'x.detect_tempo()',
    'pitch': 'x.detect_pitch()',
    'key': 'x.detect_key()',
    'genre': 'x.classify_genre()',
    'instruments': 'x.recognize_instruments()',
    'mood': 'x.recognize_mood()',
    'fingerprint': 'x.fingerprint()',
    'separation': 'x.separate_sources()',
    'suppression': 'x.suppress_noise()',
    'lone_generate': 'x.generate()',
    'dedicated_lone': 'MusicGen()',
    'audiocraft_lone': 'from audiocraft.models import AudioGen\nAudioGen()',
    'magenta_lone': 'from magenta.models import Melody\nMelody()',
    'suno_lone': 'Suno()',
    'magenta_wrong_method': 'from magenta.models import Melody\nMelody().run()',
    'suno_wrong_method': 'Suno().run()',
    'literal': '"music generation"\n# generate music\ns="generate music"',
    'reference': 'from vendor import generate_music\ngenerate_music',
    'unimported_bare': 'generate_music()',
    'subprocess': 'import subprocess\nsubprocess.run(["music-generation", "song"])',
    'generic_shadow': 'from vendor import generate_music\ndef generate_music(): pass\ngenerate_music()',
    'dedicated_shadow': 'from vendor import MusicGen\nclass MusicGen: pass\nMusicGen().generate()',
    'pipeline_shadow': 'from transformers import pipeline\ndef pipeline(*args, **kw): pass\npipeline("text-to-audio", model="music")("x")',
    'audiocraft_shadow': 'from audiocraft.models import AudioGen\nclass AudioGen: pass\nAudioGen().run()',
    'magenta_shadow': 'from magenta.models import Melody\nclass Melody: pass\nMelody().generate()',
    'suno_shadow': 'from vendor import Suno\nclass Suno: pass\nSuno().create()',
}

def evidence_test(source, expected):
    def test(self):
        self.assertEqual(audit.has_evidence(source), expected, source)
    return test

for label, source in POSITIVE.items():
    setattr(EvidenceTests, 'test_positive_' + label, evidence_test(source, True))
for label, source in NEGATIVE.items():
    setattr(EvidenceTests, 'test_reject_' + label, evidence_test(source, False))
for name in GENERIC_NAMES:
    setattr(EvidenceTests, 'test_generic_attribute_' + name, evidence_test('unrelated.' + name + '()', True))
    setattr(EvidenceTests, 'test_generic_import_' + name, evidence_test('from vendor import ' + name + '\n' + name + '()', True))
    setattr(EvidenceTests, 'test_generic_alias_' + name, evidence_test('from vendor import ' + name + ' as action\naction()', True))
for name in DEDICATED_CLASSES:
    setattr(EvidenceTests, 'test_class_' + name, evidence_test(name + '().run()', True))

class MatchingTests(unittest.TestCase):
    def test_denial_span(self):
        self.assertEqual(audit.match_claims('does not generate music'), ([], ['does not generate music']))
    def test_longest_model(self):
        self.assertEqual(audit.match_claims('music generation model')[0], ['music generation model'])
    def test_longest_generate(self):
        self.assertEqual(audit.match_claims('generate music')[0], ['generate music'])
    def test_case(self):
        self.assertEqual(audit.match_claims('MUSIC GENERATION')[0], ['music generation'])
    def test_collision(self):
        self.assertEqual(audit.match_claims('Beethoven was a famous music composer')[0], ['music composer'])
    def test_fence(self):
        self.assertEqual(audit.match_claims('```text\nmusic generation\n```\n'), ([], []))
    def test_inline(self):
        self.assertEqual(audit.match_claims('`music generation`')[0], ['music generation'])
    def test_no_normalization(self):
        self.assertEqual(audit.match_claims('generate-music'), ([], []))
    def test_repeat(self):
        self.assertEqual(audit.match_claims('generate music; generate music')[0], ['generate music'] * 2)

class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(['audit', str(self.root)] + list(args))
        return code, out.getvalue(), err.getvalue()
    def test_good(self):
        self.write('README.md', 'generate music')
        self.write('app.py', POSITIVE['pipeline_assigned'])
        code, out, _ = self.cli()
        self.assertEqual(code, 0)
        self.assertIn('PASS', out)
    def test_bad(self):
        self.write('README.md', 'MUSIC GENERATION')
        code, out, _ = self.cli()
        self.assertEqual(code, 2)
        self.assertIn('HIGH documented-music-generation-claim-false', out)
    def test_denial(self):
        self.write('README.md', 'does not generate music')
        self.write('app.py', POSITIVE['suno_chained_generate'])
        code, out, _ = self.cli()
        self.assertEqual(code, 2)
        self.assertIn('HIGH documented-no-music-generation-claim-false', out)
    def test_denial_without_source(self):
        self.write('README.md', 'does not generate music')
        self.assertIn('PASS', self.cli()[1])
    def test_test_only(self):
        self.write('tests/fixture.md', 'music generation')
        code, out, _ = self.cli()
        self.assertEqual(code, 0)
        self.assertIn('MEDIUM', out)
        self.assertEqual(self.cli('--fail-on', 'medium')[0], 2)
    def test_no_claim(self):
        self.write('README.md', 'A useful tool')
        self.assertEqual(self.cli()[0], 0)
        self.assertIn('PASS', self.cli()[1])
    def test_json(self):
        self.write('README.md', 'music generation')
        code, out, _ = self.cli('--json')
        self.assertEqual(code, 2)
        finding = json.loads(out)[0]
        self.assertEqual(finding['verdict'], 'HIGH')
        self.assertTrue(finding['message'])
    def test_version(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as result:
            main(['--version'])
        self.assertEqual(result.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), '0.1.0')
    def test_ignore(self):
        self.write('docs/skip.md', 'music generation')
        self.assertEqual(self.cli()[0], 2)
        self.assertEqual(self.cli('--ignore', 'docs/skip')[0], 0)
    def test_ignore_evidence(self):
        self.write('README.md', 'music generation')
        self.write('src/app.py', POSITIVE['suno_chained_generate'])
        self.assertEqual(self.cli('--ignore', 'src/')[0], 2)
    def test_verbose(self):
        self.write('README.md', 'Neutral')
        self.assertIn('scanned README.md', self.cli('--verbose')[2])
    def test_split_modules(self):
        self.write('README.md', 'music generation')
        self.write('a.py', 'p=MusicGen()')
        self.write('b.py', 'p.generate()')
        self.assertEqual(self.cli()[0], 2)
    def test_virtualenv_excluded(self):
        self.write('README.md', 'music generation')
        self.write('customenv/pyvenv.cfg', '')
        self.write('customenv/a.py', POSITIVE['suno_chained_generate'])
        self.assertEqual(self.cli()[0], 2)
    def test_docs_scope(self):
        self.write('other.md', 'music generation')
        self.assertEqual(self.cli()[0], 0)
        self.write('docs/deep/page.md', 'music generation')
        self.assertEqual(self.cli()[0], 2)
    def test_io_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['audit', str(self.root / 'missing')]), 1)
    def test_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            main(['audit', '--unknown'])
        self.assertEqual(result.exception.code, 1)
    def test_invalid_source(self):
        self.write('bad.py', 'def broken(')
        self.assertEqual(self.cli()[0], 1)
    def test_readme_self_audit(self):
        readme = Path(__file__).resolve().parents[1] / 'README.md'
        self.assertEqual(audit.match_claims(readme.read_text(encoding='utf-8')), ([], []))
        self.write('README.md', readme.read_text(encoding='utf-8'))
        self.assertEqual(self.cli()[0], 0)
        self.assertIn('PASS', self.cli()[1])

if __name__ == '__main__':
    unittest.main()
