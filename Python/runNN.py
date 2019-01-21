import mnist_loader
import network

def run():
    training_data, validation_data, test_data = mnist_loader.load_data()
    net = network.Network(60)
    net.sgd(training_data, 30, 20, 0.3, test_data)

run()



