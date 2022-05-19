import shutil
from pathlib import Path
import subprocess
import collections

import cldfbench
import pylexibank
from clldutils.misc import slug
from bs4 import BeautifulSoup as bs
from csvw.metadata import URITemplate

import attr

INDO_EUROPEAN_SUBGROUPS = {
    'indo1321': 'Indo-Aryan',
    'iran1269': 'Iranian',
    'nuri1243': 'Nuristani',
}

BIB = """@misc{hindukush,
    title = {Language contact and relatedness in the Hindukush region},
    howpublished = {Project hosted by Stockholm University and funded by Vetenskapsrådet (the Swedish Research Council), grant number 421-2014-631.}
}"""


def title_and_desc(p):
    text = p.read_text(encoding='utf8').split('| Feature value |')[0].strip()
    lines = [l.strip() for l in text.split('\n')]
    if len(lines) < 2:
        assert p.stem == 'README'
        return None, None
    assert lines[1] == ''
    return bs(lines[0], 'html5lib').text, '\n'.join(lines[2:])


@attr.s
class Concept(pylexibank.Concept):
    domain = attr.ib(default=None)


@attr.s
class Lexeme(pylexibank.Lexeme):
    Audio_Files = attr.ib(default=None)


@attr.s
class Language(pylexibank.Language):
    SubGroup = attr.ib(default=None)
    Location = attr.ib(default=None)
    Elicitation = attr.ib(default=None)
    Consultant = attr.ib(default=None)


class Dataset(pylexibank.Dataset):
    dir = Path(__file__).parent
    id = "liljegrenhindukush"
    lexeme_class = Lexeme
    language_class = Language
    concept_class = Concept

    form_spec = pylexibank.FormSpec(
        brackets={"(": ")", '[': ']'},  # characters that function as brackets
        separators=";/,",  # characters that split forms e.g. "a, b".
        replacements=[(" ", "_")],
        missing_data=('?', '---'),  # characters that denote missing data.
        strip_inside_brackets=True  # do you want data removed in brackets or not?
    )

    def cldf_specs(self):
        return {
            None: pylexibank.Dataset.cldf_specs(self),
            'structure': cldfbench.CLDFSpec(
                dir=self.cldf_dir,
                module='StructureDataset',
                data_fnames={'ParameterTable': 'features.csv'},
                writer_cls=cldfbench.CLDFWriter,
            ),
        }

    def cmd_download(self, args):
        self.raw_dir.xlsx2csv(self._data_dir / 'MultipleFeaturesHK.xlsx')
        for p in self._data_dir.joinpath('Features').glob('*.docx'):
            shutil.copy(str(p), self.raw_dir / p.name)
            subprocess.check_call([
                'pandoc',
                '-o', p.stem + '.md',
                '-t', 'markdown-simple_tables-multiline_tables-grid_tables',
                p.name], cwd=str(self.raw_dir))
            self.raw_dir.joinpath(p.name).unlink()
        for p in self._data_dir.joinpath('Site').glob('*.docx'):
            shutil.copy(str(p), self.dir / 'doc' / p.name)
            subprocess.check_call([
                'pandoc',
                '-o', p.stem + '.md',
                '-t', 'markdown-simple_tables-multiline_tables-grid_tables',
                p.name], cwd=str(self.dir / 'doc'))
            self.dir.joinpath('doc', p.name).unlink()

    @property
    def _data_dir(self):
        return self.raw_dir / 'Hindukush data'

    def cmd_makecldf(self, args):
        features = list(self.raw_dir.read_csv('MultipleFeaturesHK.MultipleFeatures.csv', dicts=True))
        gl_by_id = {l.id: l for l in args.glottolog.api.languoids()}
        lerrata = {r['Name']: r['Glottocode'] for r in self.etc_dir.read_csv('languages.csv', dicts=True)}
        coords = {r['ISO']: (r['Coord1'], r['Coord2']) for r in features}
        with self.cldf_writer(args) as writer:
            writer.cldf.add_component(
                'MediaTable',
                'objid',
                'fname',
                {'name': 'size', 'datatype': 'integer'},
            )
            writer.cldf.remove_columns('MediaTable', 'Download_URL')
            writer.cldf['MediaTable', 'ID'].valueUrl = URITemplate("https://cdstar.shh.mpg.de/bitstreams/{objid}/{fname}")
            for lang in self.raw_dir.read_csv(self._data_dir / 'DataSampleHK.csv', dicts=True):
                gc = lerrata.get(lang['Language'], lang['Glottocode'].split('>')[1].split('<')[0])
                glang = gl_by_id[gc]
                sg = None
                for k, v in INDO_EUROPEAN_SUBGROUPS.items():
                    if k in [l[1] for l in glang.lineage]:
                        sg = v
                        break
                writer.add_language(**dict(
                    ID=lang['Project code'].replace(' (', '_').replace(')', ''),
                    Name=lang['Language'],
                    Latitude=coords[lang['Project code']][1],
                    Longitude=coords[lang['Project code']][0],
                    Glottocode=gc,
                    Glottolog_Name=glang.name,
                    ISO639P3code=lang['ISO 639-3'].split('>')[1].split('<')[0],
                    Family=glang.lineage[0][0] if glang.lineage else None,
                    SubGroup=sg,
                    Location=lang['Location'],
                    Elicitation=lang['Elicitation'],
                    Consultant=lang['Consultant code'],
                ))
            lids = set(l['ID'] for l in writer.objects['LanguageTable'])
            audio = collections.defaultdict(lambda: collections.defaultdict(list))
            for objid, spec in self.raw_dir.read_json('cdstar.json').items():
                lang, fname = spec['metadata']['path'].split('/')
                if '_' not in fname:
                    assert fname == 'comments.txt', fname
                    continue
                lid, fname = fname.split('_', maxsplit=1)
                lid = {'aae-at': 'aee-at'}.get(lid, lid)
                lid = lid.replace('-', '_')
                assert lid in lids, spec['metadata']['path'].split('/')
                for bs in spec['bitstreams']:
                    writer.objects['MediaTable'].append(dict(
                        ID=bs['checksum'],
                        Name='{}_{}'.format(objid, bs['bitstreamid']),
                        objid=objid,
                        fname=bs['bitstreamid'],
                        Media_Type=bs['content-type'],
                        size=bs['filesize'],
                    ))
                    akey = fname.split('.')[0]
                    if akey[-1] in 'abcde':
                        akey = akey[:-1]
                    audio[lid][akey].append(bs['checksum'])

            writer.add_sources(BIB)
            cmap = writer.add_concepts(lookup_factory=lambda c: ('40list', c.english.split('(')[0].strip().lower()))
            for row in self.etc_dir.read_csv('concepts.csv', dicts=True):
                cid = '{}-{}'.format(row['Category'], slug(row['Gloss']))
                cmap[(row['Category'], row['Gloss'].lower())] = cid
                writer.add_concept(
                    ID=cid,
                    Name=row['Gloss'],
                    Concepticon_ID=row['CONCEPTICON_ID'],
                    domain=row['Category'],
                )
            for cat in ['40list', 'Kinship', 'Numerals']:
                for i, row in enumerate(self.raw_dir.read_csv(self._data_dir / '{}.csv'.format(cat), dicts=True)):
                    lid = row['ISO'].replace(' (', '_').replace(')', '')
                    if cat == '40list':
                        for j, col in enumerate(list(row.keys())[5:45], start=1):
                            audio_key = '40_{}'.format(str(j).rjust(2, '0'))
                            writer.add_lexemes(
                                Language_ID=lid,
                                Parameter_ID=cmap[(cat, col.lower())],
                                Value=row[col],
                                Audio_Files=audio.get(lid, {}).get(audio_key, []),
                                Source=['hindukush'],
                            )
                    else:
                        for j, col in enumerate(list(row.keys())[5:], start=1):
                            writer.add_lexemes(
                                Language_ID=lid,
                                Parameter_ID=cmap[(cat, col.lower())],
                                Value=row[col],
                                Source=['hindukush'],
                            )

            writer.cldf['FormTable', 'Audio_Files'].separator = ' '
            writer.cldf.add_foreign_key('FormTable', 'Audio_Files', 'media.csv', 'ID')
            writer.cldf.properties['dc:description'] = \
                self.dir.joinpath('doc', 'HKAT-Wordlist.md').read_text(encoding='utf8')
            LanguageTable = writer.cldf['LanguageTable']

        with self.cldf_writer(args, cldf_spec='structure', clean=False) as writer:
            writer.cldf.sources.add(BIB)
            descs = {p.stem.split('-')[0]: title_and_desc(p) for p in self.raw_dir.glob('*.md')}
            categories = {r['Prefix']: r['Category'] for r in self.etc_dir.read_csv('features.csv', dicts=True)}
            writer.cldf.add_component(LanguageTable)  # we reuse the one from above!
            writer.cldf.add_component('CodeTable')
            writer.cldf.add_columns('ParameterTable', 'Category')
            for i, row in enumerate(features):
                if not any(v for v in row.values()):
                    break
                lid = row['ISO'].replace(' (', '_').replace(')', '')
                if i == 0:
                    for col in list(row.keys())[4:]:
                        writer.objects['ParameterTable'].append(dict(
                            ID=col,
                            Name=descs.get(col, (None, None))[0] or col,
                            Category=categories.get(col[:2]) or col[:2],
                            Description=descs.get(col, (None, None))[1],
                        ))
                        for code, desc in [
                            ('1', 'present'),
                            ('0', 'absent'),
                            ('?', 'indeterminate'),
                        ]:
                            writer.objects['CodeTable'].append(dict(
                                ID='{}-{}'.format(col, code if code != '?' else 'x'),
                                Name=code,
                                Description=desc,
                                Parameter_ID=col,
                            ))
                for col in list(row.keys())[4:]:
                    if row[col]:
                        writer.objects['ValueTable'].append(dict(
                            ID='{}-{}'.format(lid, col),
                            Language_ID=lid,
                            Parameter_ID=col,
                            Code_ID='{}-{}'.format(col, row[col] if row[col] != '?' else 'x'),
                            Value=row[col],
                            Source=['hindukush'],
                        ))
            writer.cldf.properties['dc:description'] = \
                self.dir.joinpath('doc', 'HKAT-Features.md').read_text(encoding='utf8')
