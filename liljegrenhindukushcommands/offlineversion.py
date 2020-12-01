"""

"""
import json
import pathlib
import itertools
import subprocess
import collections
from urllib.request import urlretrieve

from lexibank_liljegrenhindukush import Dataset


def register(parser):
    parser.add_argument('concept')
    parser.add_argument('outdir')


def run(args):
    ds = Dataset()
    data = {
        'concepts': collections.OrderedDict(),
        'languages': {},
        'forms': collections.defaultdict(dict),
    }
    cldf = ds.cldf_reader()
    audio = {r['ID']: r for r in cldf['media.csv'] if r['mimetype'] == 'audio/mpeg'}

    outdir = pathlib.Path(args.outdir)
    if not outdir.exists():
        outdir.mkdir()
    audiodir = outdir / 'audio'
    if not audiodir.exists():
        audiodir.mkdir()

    for p in cldf['ParameterTable']:
        if p['ID'] == args.concept:
            data['concepts'][p['ID']] = p

    langs = []
    for p in cldf.iter_rows('LanguageTable', 'latitude', 'longitude'):
        for c in ['Latitude', 'Longitude']:
            if c in p:
                del p[c]
        langs.append(p)
        p['latitude'] = float(p['latitude'])
        p['longitude'] = float(p['longitude'])
        data['languages'][p['ID']] = p

    OSMTiles(langs, outdir / 'tiles', 4, 10).download()
    return

    #
    # download map tiles - but first check if they are there, by computing tile-list first!
    #
    #downloadosmtiles --lat=33.57:38.334 --lon=69.36:77.253 --zoom=6:10 --dumptilelist=tiles.txt
    #downloadosmtiles --lat=33.57:38.334 --lon=69.36:77.253 --zoom=6:10 --destdir=tiles

    # read tilelist and check against existing

    audios = []
    for form in cldf['FormTable']:
        if form['Parameter_ID'] != args.concept:
            continue
        for aid in form['Audio_Files']:
            if aid in audio:
                spec = data['forms'][form['Parameter_ID']][form['Language_ID']] = {
                    'form': form['Form'],
                    'url': cldf.get_row_url('media.csv', audio[aid]),
                    'path': 'audio/{}_{}.mp3'.format(form['Parameter_ID'], form['Language_ID']),
                }
                # retrieve URLs conditionally!
                urlretrieve(spec['url'], str(audiodir / '{}_{}.mp3'.format(form['Parameter_ID'], form['Language_ID'])))
                audios.append('<audio id="audio-{}" controls><source src="{}" type="audio/mpeg"></audio>'.format(form['Language_ID'], spec['path']))
                break

    outdir.joinpath('data.json').write_text('data = {};'.format(json.dumps(data)))
    html = """
<html>
<head>
    <meta charset="utf-8">
    <script src="data.json"> </script>
    <script src="jquery-3.5.1.min.js"> </script>

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"
   integrity="sha512-xodZBNTC5n17Xt2atTPuE1HxjVMSvLVW9ocqUKLsCC5CXdbqCmblAshOMAS6/keqq/sMZMZ19scR4PsZChSR7A=="
   crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"
   integrity="sha512-XQoYMqMTK8LvdxXYG3nZ448hOEQiglfqkJs1NOQV44cWnUrBc8PkAOcXy20w0vlaXaVUearIOBhiXZ5V3ynxwA=="
            crossorigin=""> </script>
    <style>
        #map {{ height: 500px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="audio" style="visibility: hidden">
    {}
    </div>

    <script src="map.js"> </script>

</body>
</html>
""".format('\n'.join(audios))
    outdir.joinpath('index.html').write_text(html, encoding='utf8')



class OSMTiles:
    """
    Use downloadosmtiles to selectively (and cumulatively) download OSM map tiles.
    """
    def __init__(self, langs, destdir, minzoom, maxzoom):
        self.destdir = pathlib.Path(destdir)
        if not self.destdir.exists():
            self.destdir.mkdir()
        self.tile_selection = [
            '--lat={}:{}'.format(
                min(r['latitude'] for r in langs), max(r['latitude'] for r in langs)),
            '--lon={}:{}'.format(
                min(r['longitude'] for r in langs), max(r['longitude'] for r in langs)),
            '--zoom={}:{}'.format(minzoom, maxzoom),
        ]

    def _call(self, *opts):
        return subprocess.check_call(['downloadosmtiles'] + list(opts))

    def download(self):
        # First compute the list of required tiles:
        tilelist = self.destdir / 'tilelist.txt'
        self._call('--dumptilelist={}'.format(str(tilelist)), *self.tile_selection)

        # Now check whih ones we are missing:
        missing_tiles = collections.defaultdict(list)
        for zoom, tiles in itertools.groupby(self.iter_tiles(tilelist), lambda xyz: xyz[2]):
            for x, y, z in tiles:
                if not self.destdir.joinpath(z, x, '{}.png'.format(y)).exists():
                    missing_tiles[z].append((x, y, z))

        if missing_tiles:
            # Note: We handcraft the rather simple yaml format of tilelists, rather than requiring
            # pyyaml.
            yaml = ['---']
            for zoom, tiles in sorted(missing_tiles.items(), key=lambda i: int(i[0])):
                yaml.append('{}:'.format(zoom))
                for tile in tiles:
                    yaml.append('  - xyz:')
                    yaml.extend(['      - {}'.format(i) for i in tile])
            tilelist.write_text('\n'.join(yaml), encoding='utf8')
            self._call(
                '--destdir={}'.format(str(self.destdir)),
                '--loadtilelist={}'.format(str(tilelist)))

    @staticmethod
    def iter_tiles(p):
        """
        Read a tilelist as written by downloadosmtiles.

        :param p:
        :return:
        """
        xyz, index = [None, None, None], -1
        for line in p.read_text(encoding='utf8').split('\n'):
            line = line.strip()
            if line == '---':
                continue
            if line.startswith('-'):
                if line.endswith('xyz:'):
                    if index > 0:
                        yield xyz
                        index = -1
                else:
                    index += 1
                    xyz[index] = line[1:].strip()
        if index > 0:
            yield xyz
