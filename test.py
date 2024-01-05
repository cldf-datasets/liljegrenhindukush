from pycldf import Dataset


def test_valid(cldf_dataset, cldf_sqlite_database, cldf_logger):
    gram = Dataset.from_metadata(cldf_dataset.directory / 'StructureDataset-metadata.json')
    assert gram.validate(log=cldf_logger)

    assert cldf_dataset.validate(log=cldf_logger)

    # make sure all mediafiles are referenced!
    assert cldf_sqlite_database.query("select count(*) from mediatable where cldf_id not in (select mediatable_cldf_id from formtable_mediatable)")[0][0] == 0
