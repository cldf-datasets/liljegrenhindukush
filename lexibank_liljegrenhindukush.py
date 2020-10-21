from pathlib import Path
import subprocess

from csvw.metadata import URITemplate
import cldfbench
import pylexibank

import attr


@attr.s
class Lexeme(pylexibank.Lexeme):
    audio = attr.ib(default=None)


class Dataset(pylexibank.Dataset):
    dir = Path(__file__).parent
    id = "liljegrenhindukush"
    lexeme_class = Lexeme

    # define the way in which forms should be handled
    form_spec = pylexibank.FormSpec(
        brackets={"(": ")"},  # characters that function as brackets
        separators=";/,",  # characters that split forms e.g. "a, b".
        missing_data=('?', '-'),  # characters that denote missing data.
        strip_inside_brackets=True   # do you want data removed in brackets or not?
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

    @property
    def _data_dir(self):
        return self.raw_dir / 'Hindukush data'

    def cmd_download(self, args):
        self.raw_dir.xlsx2csv(self._data_dir / 'MultipleFeaturesHK-20200918-forRobert.xlsx')
        for p in self.raw_dir.glob('*.docx'):
            subprocess.check_call([
                'pandoc',
                '-o', p.stem + '.md',
                '-t', 'markdown-simple_tables-multiline_tables-grid_tables',
                p.name], cwd=str(self.raw_dir))

    def cmd_makecldf(self, args):
        """
        Convert the raw data to a CLDF dataset.
        """
        with self.cldf_writer(args) as writer:
            for lang in self.raw_dir.read_csv(self._data_dir / 'DataSampleHK.csv', dicts=True):
                writer.add_language(**dict(
                    ID=lang['Project code'].replace(' (', '_').replace(')', ''),
                    Name=lang['Language'],
                    #Description=lang['Location'],
                    Glottocode=lang['Glottocode'].split('>')[1].split('<')[0],
                    ISO639P3code=lang['ISO 639-3'].split('>')[1].split('<')[0],
                ))
            cmap = writer.add_concepts(lookup_factory=lambda c: c.english.split('(')[0].strip())
            for i, row in enumerate(self.raw_dir.read_csv(self._data_dir / '40list.csv', dicts=True)):
                """
                Language, ISO, Family, lng, lat, 
                """
                lid = row['ISO'].replace(' (', '_').replace(')', '')
                lang = [l for l in writer.objects['LanguageTable'] if l['ID'] == lid][0]
                lang['Latitude'] = row['lat']
                lang['Longitude'] = row['lng']
                for j, col in enumerate(list(row.keys())[5:45], start=1):
                    audio_path = self._data_dir / 'Audio files' / lang['Name'] / '{}_40_{}.wav'.format(lid, str(j).rjust(2, '0'))
                    writer.add_form(
                        Language_ID=lid,
                        Parameter_ID=cmap[col],
                        Value=row[col],
                        Form=row[col],
                        audio=audio_path.name if audio_path.exists() else None,
                    )

            writer.cldf['FormTable', 'audio'].valueUrl = URITemplate(
                'https://github.com/cldf-datasets/liljegrenhindukush/blob/master/raw/Hindukush%20data/Audio%20files/Ashkun/{audio}?raw=true')
            LanguageTable = writer.cldf['LanguageTable']

        with self.cldf_writer(args, cldf_spec='structure', clean=False) as writer:
            descs = {
                p.stem.split('-')[0]: p.read_text(encoding='utf8').split('| Feature value |')[0]
                for p in self.raw_dir.glob('*.md')
            }
            writer.cldf.add_component(LanguageTable)  # we reuse the one from above!
            writer.cldf.add_component('CodeTable')
            for i, row in enumerate(self.raw_dir.read_csv(
                    'MultipleFeaturesHK-20200918-forRobert.MultipleFeatures.csv', dicts=True)):
                """
                Language, ISO, Family, lng, lat, 
                """
                if not any(v for v in row.values()):
                    break
                lid = row['ISO'].replace(' (', '_').replace(')', '')
                if i == 0:
                    for col in list(row.keys())[4:]:
                        writer.objects['ParameterTable'].append(dict(
                            ID=col,
                            Name=col,
                            Description=descs.get(col),
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
                        ))
