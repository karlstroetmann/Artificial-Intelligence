def simple_linear_regression(X, Y):
    """
    This function implements linear regression.
    
    * X:     explaining variable, numpy array
    * Y:     dependant variable, numpy array   

    Output: The R2 value of the linear regression.
    """
    m     = len(X)
    xMean = sum(X) / m;
    yMean = sum(Y) / m;
    ϑ1    = sum( (X - xMean) * (Y - yMean) ) / sum((X - xMean) ** 2)
    ϑ0    = yMean - ϑ1 * xMean;
    TSS   = sum((Y - yMean) ** 2)
    RSS   = sum((ϑ1 * X + ϑ0 - Y) ** 2)
    R2    = 1 - RSS / TSS;
    return R2

import csv
import numpy as np



if __name__ == '__main__':
    with open('cars.csv') as input_file:
        reader       = csv.reader(input_file, delimiter=',')
        line_count   = 0
        kpl          = []
        displacement = []
        for row in reader:
            if line_count != 0:  # skip header of file
                kpl         .append(float(row[0]) * 0.00425144) # miles per gallon is in first column 
                displacement.append(float(row[2]) * 0.0163871)  # engine displacement is in third column
            line_count += 1
    m  = len(displacement)
    X  = np.array([displacement[i] for i in range(m)])
    Y  = np.array([1 / kpl[i] for i in range(m)])
    R2 = simple_linear_regression(X, Y)
    print(f'The explained variance is {R2}%')
        
