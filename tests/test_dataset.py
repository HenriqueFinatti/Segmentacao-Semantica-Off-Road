"""Testes da preparação dos datasets (CaSSeD, máscaras e filtros). Rodar com: python -m unittest discover tests"""
import csv
import os
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from configs import paths
from configs.settings import Settings
from modules.dataset.cleaners.cassed_cleaner import CaSSeDCleaner
from modules.dataset.converters.cassed_converter import CaSSeDConverter, TRAILS
from modules.dataset.converters.freiburg_converter import FreiburgConverter
from modules.dataset.dataset_service import DatasetService
from modules.dataset.generators.mask_generator import MaskGenerator
from modules.training.dataset.off_road_dataset import OffRoadDataset

SMOOTH = (155, 155, 155)
ROUGH = (139, 87, 42)
FOREST = (59, 93, 4)
WATER = (195, 234, 254)

# Nomes do par imagem/rótulo como no CaSSeD real
FAKE_NAMES = {
    'Main_Trail': [('screenshot_rgba_0001.png', 'rgba_0001.png'), ('screenshot_rgba_0002.png', 'rgba_0002.png')],
    'Brown_field': [('image0000.png', 'rgb0000.png'), ('image0001.png', 'rgb0001.png')],
    'NorthFarm': [('1570151342.97.png', '1570151342.97.png'), ('1570151343.67.png', '1570151343.67.png')],
    'Powerline': [('1562093008.86.png', '1562093008.86.png')],
    'Fogdata': [('1574174638.04.png', '1574174638.04.png'), ('1574174641.41.png', '1574174641.41.png')],
}


def make_settings(**overrides):
    settings = Settings()
    settings.settings.update(overrides)
    return settings


def save(path, array):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(array.astype(np.uint8)).save(path)


class FakeRoot(unittest.TestCase):
    """Redireciona raw/, dataset/ e results/ para uma pasta temporária."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = self.folder.name
        self.patch = mock.patch.multiple(
            paths,
            ROOT=root,
            DATASET_DIR=os.path.join(root, 'dataset'),
            CASSED_RAW_DIR=os.path.join(root, 'raw', 'CaSSed_Dataset'),
            CASSED_SOURCE_FILE=os.path.join(root, 'results', 'dataset', 'cassed_origem.csv'),
        )
        self.patch.start()

        for split in ['train', 'test']:
            for sub in ['mask', 'original', 'original_segmentation']:
                os.makedirs(paths.dataset_dir(split, sub), exist_ok=True)

    def tearDown(self):
        self.patch.stop()
        self.folder.cleanup()


class CaSSeDConverterTest(FakeRoot):

    def make_fake_cassed(self):
        # Cada par recebe um número próprio nos pixels, para conferir que imagem e rótulo continuam juntos
        self.pair_ids = {}
        pair_id = 1
        for trail, names in FAKE_NAMES.items():
            trail_dir = os.path.join(paths.CASSED_RAW_DIR, 'Real_World_data', trail)
            for image_name, annotation_name in names:
                save(os.path.join(trail_dir, 'raw_images', image_name), np.full((6, 8, 3), pair_id))
                save(os.path.join(trail_dir, 'annotations', annotation_name), np.full((6, 8, 3), pair_id))
                self.pair_ids[(trail, image_name)] = pair_id
                pair_id += 1

    def read_value(self, path):
        return int(np.array(Image.open(path))[0, 0, 0])

    def test_converts_pairs_with_matching_names_and_trail_split(self):
        self.make_fake_cassed()
        rows = CaSSeDConverter(make_settings()).convert()

        total = sum(len(names) for names in FAKE_NAMES.values())
        self.assertEqual(len(rows), total)
        self.assertEqual([row['arquivo'] for row in rows], [f'CaSSeD_{i}' for i in range(total)])

        for row in rows:
            expected_split = 'test' if row['trilha'] in ('Main_Trail', 'Powerline') else 'train'
            self.assertEqual(row['split'], expected_split)

            image = os.path.join(paths.dataset_dir(row['split'], 'original'), row['arquivo'] + '.png')
            annotation = os.path.join(paths.dataset_dir(row['split'], 'original_segmentation'), row['arquivo'] + '.png')
            expected_id = self.pair_ids[(row['trilha'], row['imagem_original'])]
            self.assertEqual(self.read_value(image), expected_id)
            self.assertEqual(self.read_value(annotation), expected_id)

        # Arquivos foram movidos, não copiados
        for trail in FAKE_NAMES:
            self.assertEqual(os.listdir(os.path.join(paths.CASSED_RAW_DIR, 'Real_World_data', trail, 'raw_images')), [])

        with open(paths.CASSED_SOURCE_FILE, encoding='utf-8') as f:
            self.assertEqual(len(list(csv.DictReader(f))), total)

    def test_numbering_follows_trail_order_and_file_names(self):
        self.make_fake_cassed()
        rows = CaSSeDConverter(make_settings()).convert()

        expected = [(trail, image) for trail in TRAILS for image, _ in FAKE_NAMES[trail]]
        self.assertEqual([(row['trilha'], row['imagem_original']) for row in rows], expected)

    def test_rerun_replaces_previous_conversion(self):
        stale = os.path.join(paths.dataset_dir('train', 'mask'), 'CaSSeD_99.png')
        other = os.path.join(paths.dataset_dir('train', 'original'), 'Freiburg_Forest_0.jpg')
        save(stale, np.zeros((2, 2)))
        save(other, np.zeros((2, 2, 3)))

        self.make_fake_cassed()
        CaSSeDConverter(make_settings()).convert()

        self.assertFalse(os.path.exists(stale))
        self.assertTrue(os.path.exists(other))

    def test_missing_annotation_moves_nothing(self):
        self.make_fake_cassed()
        os.remove(os.path.join(paths.CASSED_RAW_DIR, 'Real_World_data', 'Brown_field', 'annotations', 'rgb0001.png'))

        with self.assertRaisesRegex(ValueError, 'rgb0001.png'):
            CaSSeDConverter(make_settings()).convert()

        self.assertEqual(os.listdir(paths.dataset_dir('train', 'original')), [])
        self.assertEqual(os.listdir(paths.dataset_dir('test', 'original')), [])

    def test_size_mismatch_is_reported(self):
        self.make_fake_cassed()
        save(os.path.join(paths.CASSED_RAW_DIR, 'Real_World_data', 'Fogdata', 'annotations', '1574174638.04.png'),
             np.zeros((12, 16, 3)))

        with self.assertRaisesRegex(ValueError, 'tamanhos diferentes'):
            CaSSeDConverter(make_settings()).convert()

    def test_unknown_test_trail_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Main_trail'):
            CaSSeDConverter(make_settings(CaSSeD_Test_Trails=['Main_trail']))


class CaSSeDCleanerTest(FakeRoot):

    def test_deletes_unused_folders_and_keeps_trails(self):
        real = os.path.join(paths.CASSED_RAW_DIR, 'Real_World_data')
        for folder in ['ROSBAGS', 'Train', 'Test', 'Main_Trail']:
            save(os.path.join(real, folder, 'x.png'), np.zeros((2, 2)))
        save(os.path.join(paths.CASSED_RAW_DIR, 'Synthetic_Data', 'images', 'x.png'), np.zeros((2, 2)))
        open(os.path.join(paths.CASSED_RAW_DIR, 'readme.rtf'), 'w').close()

        CaSSeDCleaner().delete_unused_data()

        self.assertEqual(sorted(os.listdir(paths.CASSED_RAW_DIR)), ['Real_World_data'])
        self.assertEqual(os.listdir(real), ['Main_Trail'])

    def test_accepts_copy_without_unused_folders(self):
        save(os.path.join(paths.CASSED_RAW_DIR, 'Real_World_data', 'Fogdata', 'raw_images', 'x.png'), np.zeros((2, 2)))
        CaSSeDCleaner().delete_unused_data()
        self.assertTrue(os.path.isdir(os.path.join(paths.CASSED_RAW_DIR, 'Real_World_data', 'Fogdata')))

    def test_missing_dataset_has_clear_error(self):
        with self.assertRaisesRegex(FileNotFoundError, 'CaSSed_Dataset'):
            CaSSeDCleaner().delete_unused_data()


class MaskGeneratorTest(unittest.TestCase):

    def test_any_trail_colour_within_tolerance_is_trail(self):
        annotation = np.array([[SMOOTH, ROUGH, (138, 87, 42), (155, 155, 154)],
                               [FOREST, WATER, (100, 100, 100), (0, 0, 0)]], dtype=np.uint8)

        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, 'CaSSeD_0.png')
            output = os.path.join(folder, 'mask.png')
            Image.fromarray(annotation).save(source)

            settings = make_settings()
            config = settings.get_dataset_labels()['CaSSeD']
            pct = MaskGenerator(settings).generate_binary_mask(source, output, config)
            mask = np.array(Image.open(output))

        np.testing.assert_array_equal(mask, [[1, 1, 1, 1], [0, 0, 0, 0]])
        self.assertAlmostEqual(pct, 50.0)

    def test_single_colour_datasets_still_work(self):
        settings = make_settings()
        labels = settings.get_dataset_labels()
        self.assertEqual(labels['Freiburg_Forest']['colors'].shape, (1, 3))
        self.assertEqual(labels['CaSSeD']['colors'].shape, (2, 3))


class DatasetFilterTest(unittest.TestCase):
    IMAGES = ['CaSSeD_0.png', 'Freiburg_Forest_0.jpg', 'Synthetic_Offroad_0.png', 'Other_0.png']

    def filtered(self, settings):
        dataset = OffRoadDataset('unused', settings, images=[])
        return dataset.filter_enabled_datasets(self.IMAGES)

    def test_keeps_only_enabled_datasets(self):
        settings = make_settings(Freiburg_Forest=True, Synthetic_Offroad=False, CaSSeD=True)
        self.assertEqual(self.filtered(settings), ['CaSSeD_0.png', 'Freiburg_Forest_0.jpg'])

    def test_no_dataset_enabled_is_an_error(self):
        settings = make_settings(Freiburg_Forest=False, Synthetic_Offroad=False, CaSSeD=False)
        with self.assertRaisesRegex(ValueError, 'CaSSeD'):
            self.filtered(settings)

    def test_missing_switch_is_an_error(self):
        settings = make_settings()
        del settings.settings['CaSSeD']
        with self.assertRaisesRegex(KeyError, 'CaSSeD'):
            settings.get_enabled_datasets()


class FreiburgConverterTest(FakeRoot):

    def test_does_not_rename_cassed_files(self):
        save(os.path.join(paths.dataset_dir('test', 'original'), 'CaSSeD_0.png'), np.zeros((2, 2, 3)))
        save(os.path.join(paths.dataset_dir('test', 'original_segmentation'), 'CaSSeD_0.png'), np.zeros((2, 2, 3)))
        save(os.path.join(paths.dataset_dir('test', 'original'), 'b.jpg'), np.zeros((2, 2, 3)))
        save(os.path.join(paths.dataset_dir('test', 'original_segmentation'), 'b.png'), np.zeros((2, 2, 3)))

        FreiburgConverter(make_settings()).rename_freiburg_files()

        self.assertEqual(sorted(os.listdir(paths.dataset_dir('test', 'original'))), ['CaSSeD_0.png', 'Freiburg_Forest_0.jpg'])
        self.assertEqual(sorted(os.listdir(paths.dataset_dir('test', 'original_segmentation'))), ['CaSSeD_0.png', 'Freiburg_Forest_0.png'])


class DownloadAllDatasetsTest(FakeRoot):
    STEPS = ['download_freiburg', 'clean_freiburg', 'download_synthetic', 'clean_synthetic', 'clean_cassed',
             'create_final_dataset_folder', 'convert_freiburg', 'convert_synthetic', 'convert_cassed',
             'generate_dataset_masks', 'post_download_clean']

    def run_with_mocked_steps(self):
        service = DatasetService(make_settings())
        recorder = mock.Mock()
        for step in self.STEPS:
            setattr(service, step, getattr(recorder, step))

        service.download_all_datasets()
        return [name for name, _, _ in recorder.mock_calls]

    def test_cassed_runs_with_the_other_datasets(self):
        os.makedirs(paths.CASSED_RAW_DIR)
        self.assertEqual(self.run_with_mocked_steps(), self.STEPS)

    def test_missing_cassed_fails_before_any_download(self):
        with self.assertRaisesRegex(FileNotFoundError, 'CaSSed_Dataset'):
            self.run_with_mocked_steps()


if __name__ == '__main__':
    unittest.main()
