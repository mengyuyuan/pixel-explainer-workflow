import unittest
from types import SimpleNamespace
from tts import select_device


def backend(cuda=False, mps=False, broken=()):
    def ones(_count, device):
        if device in broken:
            raise RuntimeError('device cannot allocate')
        return SimpleNamespace(sum=lambda: SimpleNamespace(item=lambda: 1))
    return SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: cuda),
                           backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps)), ones=ones)


class DeviceSelectionTests(unittest.TestCase):
    def test_cuda_wins_when_both_gpu_backends_are_available(self):
        self.assertEqual(select_device(backend(cuda=True, mps=True))[0], 'cuda')

    def test_apple_gpu_is_used_before_cpu(self):
        self.assertEqual(select_device(backend(mps=True))[0], 'mps')

    def test_no_gpu_falls_back_to_cpu(self):
        device, reasons = select_device(backend())
        self.assertEqual(device, 'cpu')
        self.assertEqual(len(reasons), 2)

    def test_unusable_cuda_can_fall_back_to_another_gpu(self):
        self.assertEqual(select_device(backend(cuda=True, mps=True, broken=('cuda',)))[0], 'mps')

    def test_failed_gpu_probe_falls_back_to_cpu(self):
        device, reasons = select_device(backend(cuda=True, broken=('cuda',)))
        self.assertEqual(device, 'cpu')
        self.assertIn('probe failed', reasons[0])

    def test_explicit_device_does_not_silently_fall_back(self):
        with self.assertRaises(RuntimeError):
            select_device(backend(broken=('cuda:1',)), 'cuda:1')


if __name__ == '__main__':
    unittest.main()
