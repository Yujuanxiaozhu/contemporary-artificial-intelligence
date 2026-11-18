import unittest

import numpy as np
import torch

from train import CNN, Preprocess, batches, stratified_split, training_stats


class ExperimentTests(unittest.TestCase):
    def test_stratified_reproducible_disjoint_split(self):
        labels = np.repeat(np.arange(10), 5000)
        train, val = stratified_split(labels, 42)
        self.assertEqual(len(train), 45000)
        self.assertEqual(len(val), 5000)
        self.assertEqual(len(np.intersect1d(train, val)), 0)
        np.testing.assert_array_equal(np.bincount(labels[val]), np.full(10, 500))
        np.testing.assert_array_equal(stratified_split(labels, 42)[1], val)
        self.assertFalse(np.array_equal(stratified_split(labels, 43)[1], val))

    def test_statistics_use_only_training_indices(self):
        x = np.zeros((3, 32, 32, 3), dtype=np.uint8)
        x[1:] = 255
        mean, std = training_stats(x, [0, 1])
        np.testing.assert_allclose(mean, [0.5] * 3)
        np.testing.assert_allclose(std, [0.5] * 3)

    def test_preprocessing_crop_and_flip_matches_reference(self):
        x = torch.randint(256, (4, 32, 32, 3), dtype=torch.uint8)
        prep = Preprocess([0, 0, 0], [1, 1, 1], torch.device('cpu'))
        torch.testing.assert_close(prep(x), x.permute(0, 3, 1, 2).float() / 255)
        rng = torch.Generator().manual_seed(44)
        actual = prep(x, rng)
        rng.manual_seed(44)
        oy, ox = torch.randint(9, (2, 4), generator=rng).tolist()
        flips = (torch.rand(4, generator=rng) < 0.5).tolist()
        padded = torch.nn.functional.pad(x.permute(0, 3, 1, 2).float(), (4, 4, 4, 4), mode='reflect')
        ref = [im[:, yy:yy+32, xx:xx+32].flip(-1) if flip else im[:, yy:yy+32, xx:xx+32]
               for im, yy, xx, flip in zip(padded, oy, ox, flips)]
        torch.testing.assert_close(actual, torch.stack(ref) / 255)

    def test_shapes_and_batch_tail(self):
        self.assertEqual(CNN().eval()(torch.randn(2, 3, 32, 32)).shape, (2, 10))
        ids = torch.arange(11)
        parts = batches(ids, 5)
        self.assertEqual(list(map(len, parts)), [5, 6])
        torch.testing.assert_close(torch.cat(parts), ids)


if __name__ == '__main__':
    unittest.main()
