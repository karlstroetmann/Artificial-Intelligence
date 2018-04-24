import matplotlib.pyplot as plt 
import numpy             as np
from math import *

def sigmoid(t):
    """
    compute the sigmoid function
    """
    return 1 / (1 + np.exp(-t))

def sigmoidPrime(t):
    """
    compute the derivative of the sigmoid function
    """
    return sigmoid(t) * (1 - sigmoid(t))

def gauss(t):
    """
    compute the sigmoid function
    """
    s = sqrt(1/3) * pi
    return np.exp(-t*t/(2*s*s)) / sqrt(2 * pi) / s

def plotSigmoid():
    n = 1000
    x = np.linspace(-8.0, 8.0, num = n)
    y = sigmoid(x)
    z = np.zeros((n,1))
    plt.margins(0.02)
    plt.plot(x, y)
    plt.plot(x, z)
    plt.xlabel("x")
    plt.ylabel("y")
    plt.title("The sigmoid function.")
    plt.show()
                
def plotSigmoidPrime():
    n = 1000
    x = np.linspace(-8.0, 8.0, num = n)
    y = sigmoidPrime(x)
    g = gauss(x)
    z = np.zeros((n,1))
    plt.margins(0.02)
    plt.plot(x, y)
    plt.plot(x, g)
    plt.plot(x, z)
    plt.xlabel("x")
    plt.ylabel("y")
    plt.title("The derivative of the sigmoid function.")
    plt.show()
    
plotSigmoid()
plotSigmoidPrime()


    

