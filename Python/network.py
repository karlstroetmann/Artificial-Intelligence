import random
import numpy as np

def rndMatrix(rows, cols):
    """
    Return a matrix of dimension (rows, cols).

    This matrix is filled with random numbers that have a Gaussian distribution
    with mean 0 and variation 1 / rows.
    """
    return np.random.randn(rows, cols) / np.sqrt(cols)

def sigmoid(x):
    "Compute the sigmoid function."
    return 1.0 / (1.0 + np.exp(-x))

def sigmoid_prime(x):
    "Compute the derivative of the sigmoid function."
    s = sigmoid(x)
    return s * (1 - s)

class Network(object):
    def __init__(self, hiddenSize):
        """
        Create a neural network with one hidden layer of size hiddenSize.
        The number of inputs is 28 * 28, the number of outputs is 10.
        """
        self.mInputSize  = 28 * 28
        self.mHiddenSize = hiddenSize
        self.mOutputSize = 10
        self.mBiasesH    = np.zeros((self.mHiddenSize, 1))   # biases hidden layer
        self.mBiasesO    = np.zeros((self.mOutputSize, 1))   # biases output layer
        self.mWeightsH   = rndMatrix(self.mHiddenSize, self.mInputSize)  # weights hidden layer
        self.mWeightsO   = rndMatrix(self.mOutputSize, self.mHiddenSize) # weights output layer
        
    def feedforward(self, x):
        """
        Compute the output of the NN if the input is the vector x.
        """
        AH = sigmoid(self.mWeightsH @ x  + self.mBiasesH) # hidden layer
        AO = sigmoid(self.mWeightsO @ AH + self.mBiasesO) # output layer
        return AO
    
    def sgd(self, training_data, epochs, mbs, eta, test_data):
        """
        Train the neural network using mini-batch stochastic gradient descent.  

          epochs: number of epochs
          mbs:    minibatch size
          eta:    learning rate

        The training_data is a list of tuples of the form (x, y) where x is an 
        input and y is the desired output. Concretely, x is a vector of size
        784 and y is a vector of size 10.
        """
        n_test = len(test_data)
        n      = len(training_data)
        for j in range(epochs):
            random.shuffle(training_data)
            mini_batches = [training_data[k : k+mbs] for k in range(0, n, mbs)]
            for mini_batch in mini_batches:
                self.update_mini_batch(mini_batch, eta)    
            print(f"Epoch {j}: {self.evaluate(test_data)} / {n_test}")

    def update_mini_batch(self, mini_batch, eta):
        nabla_BH = np.zeros((self.mHiddenSize, 1))  # gradient of biases  of hidden layer
        nabla_BO = np.zeros((self.mOutputSize, 1))  # gradient of biases  of output layer
        nabla_WH = np.zeros((self.mHiddenSize, self.mInputSize))  # gradient of weights of hidden layer
        nabla_WO = np.zeros((self.mOutputSize, self.mHiddenSize)) # gradient of weights of output layer
        for x, y in mini_batch:
            dltNbl_BH, dltNbl_BO, dltNbl_WH, dltNbl_WO = self.backprop(x, y)
            nabla_BH += dltNbl_BH
            nabla_BO += dltNbl_BO
            nabla_WH += dltNbl_WH
            nabla_WO += dltNbl_WO      
        alpha = eta / len(mini_batch)
        self.mBiasesH  -= alpha * nabla_BH
        self.mBiasesO  -= alpha * nabla_BO
        self.mWeightsH -= alpha * nabla_WH
        self.mWeightsO -= alpha * nabla_WO
    
    def backprop(self, x, y):
        """
        Backpropagation to calculate the gradient for the cost function
          x: training inputs
          y: correct result for inputs x
        """
        # feedforward pass
        ZH = self.mWeightsH @ x  + self.mBiasesH
        AH = sigmoid(ZH)
        ZO = self.mWeightsO @ AH + self.mBiasesO
        AO = sigmoid(ZO)
        # backwards pass, output layer
        epsilonO = (AO - y) # * sigmoid_prime(ZO)
        nabla_BO = epsilonO
        nabla_WO = epsilonO @ AH.transpose()
        # backwards pass, hidden layer
        epsilonH = (self.mWeightsO.transpose() @ epsilonO) * sigmoid_prime(ZH)
        nabla_BH = epsilonH
        nabla_WH = epsilonH @ x.transpose()
        return (nabla_BH, nabla_BO, nabla_WH, nabla_WO)
    
    # Returns sum of correct guesses after feedforwarding
    def evaluate(self, test_data):
        """
        Return the number of test inputs for which the neural
        network outputs the correct result. Note that the neural
        network's output is assumed to be the index of whichever
        neuron in the final layer has the highest activation.
        """
        test_results = [(np.argmax(self.feedforward(x)), y) for (x, y) in test_data]
        return sum(int(x == y) for (x, y) in test_results)
