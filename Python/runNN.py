import mnist_loader
import network

def run():
    training_data, validation_data, test_data = mnist_loader.load_data_wrapper()
    training_data = list(training_data)
    test_data     = list(test_data)
    net = network.Network(60)
    net.sgd(training_data, 30, 10, 2.0, test_data)

run()



