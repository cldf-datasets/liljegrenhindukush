
def test_valid(cldf_dataset, cldf_logger):
    assert cldf_dataset.validate(log=cldf_logger)
#
# FIXME: validate both CLDF datasets!
#