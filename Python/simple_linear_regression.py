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

def test(col):
    """
    Compute the coefficient of determination for the specified column
    of the csv file 'cars.csv'.
    """
    with open('cars.csv') as input_file:
        reader     = csv.reader(input_file, delimiter=',')
        line_count = 0
        mpg        = []
        cause      = []
        colNames   = {}
        for row in reader:
            if line_count == 0:  
                colNames = { col:row[col] for col in range(len(row)) }
            else:
                mpg  .append(float(row[0]))  
                cause.append(float(row[col])) 
            line_count += 1
    m  = len(mpg)
    X  = np.array(cause)
    Y  = np.array([1 / mpg[i] for i in range(m)])
    R2 = simple_linear_regression(X, Y)
    return colNames[col], R2
     
if __name__ == '__main__':
    for col in range(1, 6+1):
        name, R2 = test(col)
        print(f'The explained variance of {name} is {R2}%')
