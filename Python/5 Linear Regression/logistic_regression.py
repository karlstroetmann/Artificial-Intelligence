import numpy as np
import csv
import gradient_ascent

def sigmoid(t):
    "compute the sigmoid of t"
    return 1.0 / (1.0 + np.exp(-t))

def logSigmoid(t):
    "compute the sigmoid of t, avoid overflow"
    if t > -100:
        return -np.log(1.0 + np.exp(-t))
    else:
        return t

def ll(X, y, w):
    """
    given the matrix X and the observations y,
    return the log likelihood for the weight vector w
    """
    return np.sum([logSigmoid(y[i] * (X[i] @ w)) for i in range(len(X))])

def gradLL(X, y, w):
    """
    Compute the gradient ofthe log-likelihood with respect to w 
    """
    Gradient = []
    for j in range(len(X[1])):
        L = [y[i]*X[i][j]*sigmoid(-y[i] * (X[i] @ w)) for i in range(len(X))]
        Gradient.append(sum(L))
    return np.array(Gradient)

def logisticRegressionFile(name):
    with open(name) as file:
        reader = csv.reader(file, delimiter=',', skipinitialspace=True)
        count  = 0  # line count
        Pass   = []
        Hours  = []
        for row in reader:
            if count != 0:  # skip header
                Pass .append(float(row[0]))
                Hours.append(float(row[1]))
            count += 1
    y = np.array(Pass)
    x = np.array(Hours)
    n = len(y)
    X = np.reshape(x, (n,1))
    X = np.append(np.ones((n, 1)), X, axis=-1)
    y = 2 * y - 1
    start   = np.zeros((2,))
    eps     = 10 ** -8
    f       = lambda w: ll(X, y, w)
    gradF   = lambda w: gradLL(X, y, w)
    w, _, _ = gradient_ascent.findMaximum(f, gradF, start, eps)
    return w

if __name__ == '__main__':
    w = logisticRegressionFile('exam.csv')
    print(f'model: P(pass|hours) = S({w[0]} + {w[1]} * hours)')
