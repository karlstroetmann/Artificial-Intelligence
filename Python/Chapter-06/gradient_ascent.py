def findMaximum(f, gradF, start, eps, verbose=False):
    """
    The function findMaximum computes the maximum of the function f using the
    method of gradient ascent.  It is assumed that the function is convex and
    therefore there is only one global maximum.
    f:     The function to minimize.  This function is expected to take one
           argument as its input.  This input is assumed to be a vector and 
           f returns a floating point number.
    fGrad: The gradient of f.  This function takes one input that is is assumed
           to be a vector.
    start: The value used to start the iteration.
    eps:   Precisison.  If the change of f is less than eps, then the iteration
           stops.
    The function returns both the position x_max of the maximum as well as the
    value that the function f has at this position.
    """
    x     = start
    fx    = f(x)
    alpha = 0.1
    cnt   = 1  # number of iterations
    while True:
        xOld, fOld = x, fx
        x  += alpha * gradF(x)
        fx  = f(x)
        if verbose:
            print(f'cnt = {cnt}, f({x}) = {fx}')
            print(f'gradient = {gradF(x)}')
        if abs(fx - fOld) <= abs(fx) * eps and cnt > 1:
            return x, fx, cnt
        if fx <= fOld:   
            alpha *= 0.5
            if verbose:
                print(f'decrementing: alpha = {alpha}')
            x, fx = xOld, fOld
            continue
        else:
            alpha *= 1.2
            if verbose:
                print(f'incrementing: alpha = {alpha}')
        cnt += 1

if __name__ == '__main__':
    import math
    import numpy as np
    # one dimensional example
    f  = lambda x: math.sin(x) - x**2 / 2
    fs = lambda x: math.cos(x) - x
    start = 0
    x, fx, cnt = findMaximum(f, fs, start, 10**-15, True)
    print(f'maximum at {x}, value {fx}, {cnt} iterations')
    # two dimensional example
    f  = lambda x: 3 - (x[0] - 1.5) ** 2 - (x[1] + 2.0) ** 4
    fs = lambda x: - np.array([2 * (x[0] - 1.5), 4 * (x[1] + 2.0) ** 3])
    start = np.array([0.0, 0.0])
    x, fx, cnt = findMaximum(f, fs, start, 10**-11, True)
    print(f'maximum at {x}, value {fx}, {cnt} iterations')


