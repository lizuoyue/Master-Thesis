import os, time
import matplotlib.pyplot as plt
import numpy as np

def mov_avg(li, n):
	print(len(li), n)
	assert(len(li) >= n)
	s = sum(li[0: n])
	res = [s / float(n)]
	for i in range(n, len(li)):
		s += (li[i] - li[i - n])
		res.append(s / float(n))
	return res

def process(filename, n = 1000):
	with open(filename) as f:
		lines = [line.strip().split(', ') for line in f.readlines()]
		loss_cls = [float(line[1]) for line in lines]
		loss_dlt = [float(line[2]) for line in lines]
		loss_cnn = [float(line[3]) for line in lines]
		loss_rnn = [float(line[4]) for line in lines]
	return mov_avg(loss_cls, n), mov_avg(loss_dlt, n), mov_avg(loss_cnn, n), mov_avg(loss_rnn, n)

if __name__ == '__main__':
	server = 'dalab'
	net = 'vgg16'
	city = 'Chicago'
	# os.popen('scp %s:~/thesis/building/Loss_train_%s_%s.out ./LossTrain.out' % (server, net, city))
	# os.popen('scp %s:~/thesis/building/Loss_valid_%s_%s.out ./LossValid.out' % (server, net, city))
	# quit()

	n = 1000
	# loss_cls, loss_dlt, loss_cnn, loss_rnn = process('LossTrain.out', n)
	# l = len(loss_cnn)
	# plt.plot(range(l), loss_cls, label = 'CLS')
	# plt.plot(range(l), loss_dlt, label = 'DLT')
	# plt.plot(range(l), loss_cnn, label = 'CNN')
	# plt.plot(range(l), loss_rnn, label = 'RNN')
	# plt.title('Training Loss')
	# plt.ylim(ymin = 0, ymax = 5)
	# plt.xlim(xmin = 0)
	# plt.legend(loc = 'upper right')
	# plt.show()

	int_val = 100
	n_val = int(n / int_val)
	loss_cls_val, loss_dlt_val, loss_cnn_val, loss_rnn_val = process('LossValid.out', n_val)
	l_val = len(loss_cnn_val)
	plt.plot((np.array(range(l_val)) + n_val) * int_val, loss_cls_val, label = 'CLS Val')
	plt.plot((np.array(range(l_val)) + n_val) * int_val, loss_dlt_val, label = 'DLT Val')
	plt.plot((np.array(range(l_val)) + n_val) * int_val, loss_cnn_val, label = 'CNN Val')
	plt.plot((np.array(range(l_val)) + n_val) * int_val, loss_rnn_val, label = 'RNN Val')
	plt.title('Validation Loss')
	plt.ylim(ymin = 0, ymax = 5)
	plt.xlim(xmin = 0)
	plt.legend(loc = 'upper right')
	plt.show()
	




