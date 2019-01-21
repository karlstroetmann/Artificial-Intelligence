# %load mnist_loader.py
"""
mnist_loader
~~~~~~~~~~~~
A library to load the MNIST image data.  For details of the data
structures that are returned, see the doc strings for ``load_data``
and ``load_data_wrapper``.  In practice, ``load_data_wrapper`` is the
function usually called by our neural network code.
"""

#### Libraries
# Standard library
import pickle
import gzip

# Third-party libraries
import numpy as np

def load_data():
    """
    Return a tuple 
        (training_data, validation_data, test_data). 
     
        * training_data: list containing 50,000 pairs (x, y).  
          x is a 784-dimensional numpy.ndarray containing the input image. 
          y is a 10-dimensional numpy.ndarray representing the unit vector 
            corresponding to the correct digit for x.

        * validation_data and
        * test_data are lists containing 10,000 pairs (x, y).  In each case, 
          x is a 784-dimensional numpy.ndarry containing the input image, 
          and y is the corresponding classification, i.e., the digit value 
          corresponding to x.

    Note that this means we're using slightly different formats for
    the training data and the validation / test data.  These formats
    turn out to be the most convenient for use in our neural network
    code.
    """
    with gzip.open('mnist.pkl.gz', 'rb') as f:
        tr_d, va_d, te_d = pickle.load(f, encoding="latin1")
    training_inputs   = [np.reshape(x, (784, 1)) for x in tr_d[0]]
    training_results  = [vectorized_result(y) for y in tr_d[1]]
    training_data     = zip(training_inputs, training_results)
    validation_inputs = [np.reshape(x, (784, 1)) for x in va_d[0]]
    validation_data   = zip(validation_inputs, va_d[1])
    test_inputs       = [np.reshape(x, (784, 1)) for x in te_d[0]]
    test_data         = zip(test_inputs, te_d[1])
    training_data     = list(training_data)
    validation_data   = list(validation_data)
    test_data         = list(test_data)
    return (training_data, validation_data, test_data)

def vectorized_result(j):
    """Return a 10-dimensional unit vector with a 1.0 in the jth
    position and zeroes elsewhere.  This is used to convert a digit
    (0...9) into a corresponding desired output from the neural
    network."""
    e = np.zeros((10, 1), dtype=np.float32)
    e[j] = 1.0
    return e
