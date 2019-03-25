import unittest

from tensorflow.python.keras.models import Sequential
from tensorflow.python.keras.layers import Dense
import tensorflow.python.keras as keras

import numpy as np

# just do https://keras.io/ tutorial





class MyTestCase(unittest.TestCase):
    def test_first_tutorial(self):
        model = Sequential()

        model.add(Dense(units=32, activation='relu', input_dim=10))
        model.add(Dense(units=10, activation='softmax'))

        model.summary()

        model.compile(loss='categorical_crossentropy', optimizer='sgd', metrics=['accuracy'])

        data = np.random.random((1000, 10))

        labels = np.random.randint(10, size=(10, 1))

        one_hot_labels = keras.utils.to_categorical(labels, num_classes=10)

        model.fit(data, one_hot_labels, epochs=10, batch_size=32)

        print (model.predict(data))

        print(model.predict([.05,1,1,1,1,1,1,1,1,1]))

    def test_first_tutorial_mod(self):
        model = Sequential()

        model.add(Dense(units=32, activation='relu', input_dim=100))
        model.add(Dense(units=10, activation='softmax'))

        model.compile(loss='categorical_crossentropy', optimizer='sgd', metrics=['accuracy'])

        #Alternatively, you can feed batches to your model manually:
#        model.train_on_batch(x_batch, y_batch)

        #Evaluate your performance in one line:
#        loss_and_metrics = model.evaluate(x_test, y_test, batch_size=128)

        #Or generate predictions on new data:
#        classes = model.predict(x_test, batch_size=128)


if __name__ == '__main__':
    unittest.main()