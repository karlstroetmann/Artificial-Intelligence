def read_names(file_name):
    Result = []
    with open(file_name, 'r') as file:
        for name in file:
            Result.append(name[:-1]) # discard newline
    return Result

FemaleNames = read_names('names-female.txt')
MaleNames   = read_names('names-male.txt'  )

pFemale = len(FemaleNames) / (len(FemaleNames) + len(MaleNames))
pMale   = len(MaleNames)   / (len(FemaleNames) + len(MaleNames))

def conditional_prop(c, g):
    """
    Given a character c that is the last character of a name and a gender g,
    compute the conditional probability that the name has this last character. 
    """
    if g == 'f':
        return len([n for n in FemaleNames if n[-1] == c]) / len(FemaleNames)
    else:
        return len([n for n in MaleNames   if n[-1] == c]) / len(MaleNames)

Conditional_Probability = {}
for c in 'abcdefghijklmnopqrstuvwxyz':
    Conditional_Probability[(c, 'f')] = conditional_prop(c, 'f')
    Conditional_Probability[(c, 'm')] = conditional_prop(c, 'm')

def classify(name):
    last   = name[-1]
    female = Conditional_Probability[(last, 'f')] * pFemale
    male   = Conditional_Probability[(last, 'm')] * pMale
    if female >= male:
        return 'f'
    else:
        return 'm'

total   = 0
correct = 0
for n in FemaleNames:
    if classify(n) == 'f':
        correct += 1
    total += 1
for n in MaleNames:
    if classify(n) == 'm':
        correct += 1
    total += 1
accuracy = correct / total
print(f'The accuracy of our estimator is {accuracy}.')
