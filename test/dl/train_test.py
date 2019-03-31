import unittest
import numpy as np
from dl.train import Train

class MyTestCase(unittest.TestCase):

    def test_create_model(self):
        train = Train()

        train.create_model()


    def test_train(self):
        train = Train()

        train.do_train('/tmp/2019/**/*.tfrecords')

    def test_np_array(self):
        x1 = np.ndarray((100, 50))
        x2 = np.ndarray((100, 50))
        x3 = np.ndarray((100, 50))
        x4 = np.ndarray((100, 50))

        z = np.stack([x1, x2, x3, x4])

        print(z.shape)
        self.assertEqual(z.shape, (4, 100, 50))

        array = np.array([1, 2, 3, 4])
        print(array)



    def test_something(self):
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
