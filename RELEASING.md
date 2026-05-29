# Releasing Hindu Kush Areal Typology

1. Update the input files in `raw/`
2. Update the derived raw formats running
   ```shell
   cldfbench download lexibank_liljegrenhindukush.py
   ```
3. Re-create the CLDF datasets
   ```shell
   cldfbench lexibank.makecldf lexibank_liljegrenhindukush.py --glottolog-version v5.3 --concepticon-version v3.4.0 --clts-version v2.3.0
   ```
4. Make sure the CLDF is valid:
   ```shell
   pytest
   ```
5. Re-create the coverage map:
   ```shell
   cldfbench cldfviz.map --language-properties Family --format svg --output map.svg cldf/ --width 15 --padding-left 3 --padding-right 3 --padding-top 3 --padding-bottom 3
   ```
6. Re-create the CLDF README:
   ```shell
   cldfbench cldfreadme lexibank_liljegrenhindukush.py
   ```
