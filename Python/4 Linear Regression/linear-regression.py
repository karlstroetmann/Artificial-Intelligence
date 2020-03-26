import csv
import numpy as np

def linear_regression(fileName, target, explaining, f):
    """
    * fileName:   name of a csv file
    * target:     column of the dependent variable
    * explaining: list of columns containing the explaining variables
    * f:          function to process the target
    returns the coefficient of determination R2
    """
    with open(fileName) as input_file:
        reader     = csv.reader(input_file, delimiter=',')
        line_count = 0
        goal       = []
        Causes     = []
        for row in reader:
            if line_count != 0:  
                goal  .append(f(float(row[target])))  
                Causes.append([float(row[i]) for i in explaining] + [1.0]) 
            line_count += 1
    m = len(goal)
    X = np.array(Causes)
    y = np.array(goal)
    w = np.linalg.solve(X.T @ X, X.T @ y)
    RSS   = np.sum((X @ w - y) ** 2)
    yMean = np.sum(y) / m
    TSS   = sum((y - yMean) ** 2)
    R2    = 1 - RSS / TSS
    return R2

def main():
    explaining = [1, 2, 3, 4, 5, 6]
    R2 = linear_regression("cars.csv", 0, explaining, lambda x: 1/x)
    print(f'portion of explained variance : {R2}')

main()
