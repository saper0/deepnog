import logging
from pathlib import Path
import pytest
from tempfile import TemporaryDirectory
import torch
from deepnog.utils import count_parameters, get_logger, get_weights_path, load_nn, set_device

GPU_AVAILABLE = torch.cuda.is_available()
TEST_STR = 'krawutzi'
PWD = Path(__file__).parent.absolute()
WEIGHTS_PATH = PWD/'parameters/test_deepencoding.pthsmall'


def test_set_device():
    device = 'tpu'
    msg = f'Unknown device "{device}". Try "auto".'
    with pytest.raises(ValueError, match=msg):
        set_device(device)


def test_auto_device():
    device = set_device('auto')
    assert isinstance(device, torch.device)
    assert str(device) in ['cpu', 'cuda'], f'Unrecognized device: {device}'


def test_cpu_device():
    device = 'cpu'
    assert isinstance(set_device(device), torch.device)


@pytest.mark.skipif(not GPU_AVAILABLE, reason='GPU is not available')
def test_gpu_device_available():
    device = 'gpu'
    assert isinstance(set_device(device), torch.device)


@pytest.mark.skipif(GPU_AVAILABLE, reason='GPU is available')
def test_gpu_device_unavailable():
    device = 'gpu'
    msg = 'could not access any CUDA-enabled GPU'
    with pytest.raises(RuntimeError, match=msg):
        set_device(device)


@pytest.mark.xfail(reason=("BUG: pytest logging capture does not work. "
                           "Look out for 4 logging lines manually..."))
def test_logger(caplog):
    """ Test that only the correct msg levels are logged according to verbose"""
    with caplog.at_level(logging.DEBUG, logger=__name__):
        for verbose in [True, False]:
            logger = get_logger(__name__, verbose=verbose)
            logger.info(TEST_STR)
            logger.warning(TEST_STR)
        logger = get_logger(__name__, verbose=0)
        logger.error(TEST_STR)
        logger.warning(TEST_STR)
        logger = get_logger(__name__, verbose=1)
        logger.warning(TEST_STR)
        logger.info(TEST_STR)
        logger = get_logger(__name__, verbose=2)
        logger.info(TEST_STR)
        logger.debug(TEST_STR)
        logger = get_logger(__name__, verbose=3)
        logger.debug(TEST_STR)
        lvls = (logging.INFO, logging.WARNING, logging.INFO,
                logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)
        assert len(caplog.record_tuples), 'No logging output was captured'
        for i, record in enumerate(caplog.record_tuples):
            assert record == (__name__, lvls[i], TEST_STR)


def test_get_weights():
    with TemporaryDirectory(prefix='deepnog_test_data_dir_') as tmpdir:
        p = get_weights_path(database='testdb',
                             level='1',
                             architecture='do_not_delete',
                             data_home=tmpdir,
                             download_if_missing=True,
                             verbose=3)
        assert Path(p).is_file()


def test_get_weights_impossible():
    with TemporaryDirectory(prefix='deepnog_test_data_dir_') as tmpdir:
        with pytest.raises(IOError, match='Data not found'):
            _ = get_weights_path(database='testdb',
                                 level='1',
                                 architecture='do_not_delete',
                                 data_home=tmpdir,
                                 download_if_missing=False,
                                 verbose=3)


@pytest.mark.parametrize("architecture", ['deepencoding', ])
@pytest.mark.parametrize("weights", [WEIGHTS_PATH, ])
def test_count_params(architecture, weights):
    """ Test loading of neural network model. """
    cuda = torch.cuda.is_available()
    device = torch.device('cuda' if cuda else 'cpu')
    model_dict = torch.load(weights, map_location=device)
    model = load_nn(architecture, model_dict, phase='infer', device=device)
    n_params_tuned = count_parameters(model, tunable_only=True)
    n_params_total = count_parameters(model, tunable_only=False)
    assert n_params_total == n_params_tuned
