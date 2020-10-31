"""
Upload audio files to CDSTAR
"""
from cdstarcat import Catalog
from cdstarcat.cli_util import add_cdstar

from lexibank_liljegrenhindukush import Dataset


def register(parser):
    add_cdstar(parser)


def run(args):
    ds = Dataset()
    with Catalog(
        ds.raw_dir / 'cdstar.json', 
        cdstar_url=args.url,
        cdstar_user=args.user,
        cdstar_pwd=args.pwd,
    ) as cat:
        for fname, created, obj in cat.create(
            ds.raw_dir / 'Hindukush data' / 'Audio files',
            lambda p: dict(
                path='{}/{}'.format(p.parent.name, p.name),
                collection=ds.id,
            )
        ):
            if created:
                args.log.info('{} -> {}'.format(fname, obj.id))

