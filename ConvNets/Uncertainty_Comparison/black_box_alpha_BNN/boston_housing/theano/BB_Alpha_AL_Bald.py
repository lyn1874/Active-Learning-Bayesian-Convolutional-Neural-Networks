
import theano
import theano.tensor as T
from black_box_alpha import BB_alpha

import os

import sys

import numpy as np

import gzip

import cPickle

import random

import network

import network_layer

# We download the data

def load_data():
    # We load the data
    data = np.loadtxt('../data/data.txt')

    # We load the indexes for the features and for the target

    index_features = np.loadtxt('../data/index_features.txt')
    index_target = np.loadtxt('../data/index_target.txt')

    X = data[ : , index_features.tolist() ]
    y = data[ : , index_target.tolist() ]

    i = np.int(np.loadtxt('simulation_index.txt'))

    # We load the indexes of the training set

    index_train = np.loadtxt("../data/index_train_{}.txt".format(i))
    index_test = np.loadtxt("../data/index_test_{}.txt".format(i))

    X_train = X[ index_train.tolist(), ]
    y_train = y[ index_train.tolist() ][ : , None ]
    X_test = X[ index_test.tolist(), ]
    y_test = y[ index_test.tolist() ][ : , None ]

    # We normalize the features

    std_X_train = np.std(X_train, 0)
    std_X_train[ std_X_train == 0 ] = 1
    mean_X_train = np.mean(X_train, 0)
    X_train = (X_train - mean_X_train) / std_X_train
    X_test = (X_test - mean_X_train) / std_X_train
    mean_y_train = np.mean(y_train, 0)
    std_y_train = np.std(y_train, 0)

    y_train = (y_train - mean_y_train) / std_y_train

    X_train_All = X_train
    y_train_All = y_train

    X_train = X_train_All[0:100, :]
    y_train = y_train_All[0:100, :]

    X_pool = X_train_All[100:, :]
    y_pool = y_train_All[100:, :]


    return X_train, y_train, X_test, y_test, X_pool, y_pool, mean_y_train, std_y_train


def shared_dataset(data_xy, borrow=True):

    data_x, data_y = data_xy
    shared_x = theano.shared(np.asarray(data_x, dtype=theano.config.floatX), borrow=borrow)
    shared_y = theano.shared(np.asarray(data_y, dtype=theano.config.floatX), borrow=borrow)

    return shared_x, T.cast(shared_y, 'float32')


# function to compute the predictive distributon
#predict_probabilistic = theano.function( [x], network.output_probabilistic(x))



# # # creat a network
# network = network_layer.Network_layer(layer_sizes, n_samples, v_prior, N)




# def predictive_mean_and_variance(X_test, mean_y_train, std_y_train ):
#     mean = np.zeros(X_test.shape[0])
#     variance = np.zeros(X_test.shape[0])
#     for i in range(X_test.shape[0]):
#         Xi = X_test[i, :]

#         m, v = theano.function( [Xi], network.output_probabilistic(mean_y_train, std_y_train ))
#         # m, v = predict_probabilistic(Xi)
#         m = m * std_y_train + mean_y_train
#         v *= std_y_train**2
#         mean[i] = m
#         variance[i] = v

#     return mean, variance



import os
acquisition_iterations = 1
Queries = 1
adam_epochs = 20         # original = 500
all_rmse = 0



# We load the random seed
np.random.seed(1)

# We load the data
X_train, y_train, X_test, y_test, X_pool, y_pool, mean_y_train, std_y_train = load_data()

n = X_train.shape[0]
d = X_train.shape[1]

train_set = X_train, y_train
test_set = X_test, y_test

train_set_x, train_set_y = shared_dataset(train_set)
test_set_x, test_set_y = shared_dataset(test_set)


datasets = [(train_set_x, train_set_y), (test_set_x, test_set_y)]

train_set_x, train_set_y = datasets[ 0 ]
test_set_x, test_set_y = datasets[ 1 ]


N_train = train_set_x.get_value(borrow = True).shape[ 0 ]
N_test = test_set_x.get_value(borrow = True).shape[ 0 ]
layer_sizes = [ d, 100, len(mean_y_train) ]
n_samples = 50
alpha = 0.5
learning_rate = 0.001
v_prior = 1.0




# NEED TO REDUCE BATCH SIZE IF AL EXPERIMENT IS STARTING WITH 20 DATA POINTS
batch_size = 32

print '... building model'
sys.stdout.flush()

bb_alpha = BB_alpha(layer_sizes, n_samples, alpha, learning_rate, v_prior, batch_size, train_set_x, train_set_y, N_train, test_set_x, test_set_y, N_test, mean_y_train, std_y_train)

print '... training'
sys.stdout.flush()

#test_error, test_ll = bb_alpha.train_ADAM(adam_epochs)
test_error, test_ll = bb_alpha.train_ADAM(adam_epochs)

print('Test Error', test_error)
print('Test Log Likelihood', test_ll)


all_rmse = test_error


for i in range(acquisition_iterations):

    print('Acquisition Iteration: ', i)


    mean, variance = bb_alpha.predictive_mean_and_variance(X_pool)


    #select next x with highest predictive variance
    v_sort = v_pool.flatten()
    x_pool_index = v_sort.argsort()[-Queries:][::-1]

    Pooled_X = X_pool[x_pool_index, :]
    Pooled_Y = y_pool[x_pool_index, :]

    X_pool = np.delete(X_pool, (x_pool_index), axis=0)
    y_pool = np.delete(y_pool, (x_pool_index), axis=0)

    X_train = np.concatenate((X_train, Pooled_X), axis=0)
    y_train = np.concatenate((y_train, Pooled_Y), axis=0)

    mean_y_train = np.mean(y_train, 0)
    std_y_train = np.std(y_train, 0)

    n = X_train.shape[0]
    d = X_train.shape[1]

    train_set = X_train, y_train
    test_set = X_test, y_test

    train_set_x, train_set_y = shared_dataset(train_set)
    test_set_x, test_set_y = shared_dataset(test_set)


    datasets = [(train_set_x, train_set_y), (test_set_x, test_set_y)]

    train_set_x, train_set_y = datasets[ 0 ]
    test_set_x, test_set_y = datasets[ 1 ]


    N_train = train_set_x.get_value(borrow = True).shape[ 0 ]
    N_test = test_set_x.get_value(borrow = True).shape[ 0 ]
    layer_sizes = [ d, 100, len(mean_y_train) ]
    n_samples = 50
    alpha = 0.5
    learning_rate = 0.001
    v_prior = 1.0

    # NEED TO REDUCE BATCH SIZE IF AL EXPERIMENT IS STARTING WITH 20 DATA POINTS
    batch_size = 32

    print '... building model'
    sys.stdout.flush()

    bb_alpha = BB_alpha(layer_sizes, n_samples, alpha, learning_rate, v_prior, batch_size, train_set_x, train_set_y, N_train, test_set_x, test_set_y, N_test, mean_y_train, std_y_train)

    print '... training'
    sys.stdout.flush()

    #test_error, test_ll = bb_alpha.train_ADAM(adam_epochs)
    test_error, test_ll = bb_alpha.train_ADAM(adam_epochs)

    print('Test Error', test_error)
    print('Test Log Likelihood', test_ll)
    

    all_rmse = np.append(all_rmse, test_error)


print('All RMSE:', all_rmse)









