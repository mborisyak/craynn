import tensorflow as tf

from ..layers_meta import *
from .conv_common import *

from .. import init
from ..common_ops import get_nonlinearity

from ...meta import based_on, curry_incoming

__all__ = [
  'TransposedConv2DLayer',
]

from ..nonlinearities import leaky_relu
default_conv_nonlinearity = leaky_relu(0.05)


class TransposedConvLayer(FunctionalLayer):
  def __init__(
    self, incoming, ndim, conv_op,
    num_filters, filter_size, pad, stride,
    kernel=init.default_weight_init, biases=init.default_bias_init,
    nonlinearity=default_conv_nonlinearity,
    name=None
  ):
    super(TransposedConvLayer, self).__init__(incoming, name=name)
    self.ndim = ndim

    self.filter_size = get_kernel_size(filter_size, ndim)
    self.num_filters = num_filters

    self.input_shape = get_output_shape(incoming)
    self.num_input_channels = self.input_shape[-1]

    self.pad = get_pad(pad)
    self.stride = get_stride(stride, ndim=self.ndim)

    self.nonlinearity = get_nonlinearity(nonlinearity)

    kernel_shape = self.filter_size + (num_filters, self.num_input_channels)
    self.kernel = tf.Variable(
      initial_value=kernel(kernel_shape),
      dtype='float32',
      expected_shape=kernel_shape
    )

    self.biases = tf.Variable(
      initial_value=biases((1, ) * ndim + (1, num_filters)),
      dtype='float32',
      expected_shape=((1, ) * ndim + (1, num_filters))
    )

    self.params['kernel'] = (self.kernel, ['weights', 'trainable', 'free', 'conv_kernel'])
    self.params['biases'] = (self.biases, ['biases', 'trainable', 'free'])

    self.conv_op = conv_op

  def get_output_for(self, X):
    ow, oh = get_transposed_kernel_output_shape(
      self.input_shape[1:-1],
      spatial_kernel_size=self.filter_size,
      pad=self.pad,
      stride=self.stride[1:-1]
    )

    output_shape = tf.concat([
      tf.gather(tf.shape(X), [0]),
      [ow, oh, self.num_filters]
    ], axis=0)

    conved = self.conv_op(
      X,
      output_shape=output_shape,
      filter=self.kernel,
      strides=self.stride,
      padding=self.pad,
      data_format=strange_data_format(self.ndim),
    )

    return self.nonlinearity(conved + self.biases)

  def get_output_shape_for(self, input_shape):
    return (input_shape[0], ) + get_transposed_kernel_output_shape(
      input_shape[1:-1],
      spatial_kernel_size=self.filter_size,
      pad=self.pad,
      stride=self.stride[1:-1]
    ) + (self.num_filters, )


TransposedConv2DLayer = based_on(TransposedConvLayer).derive('TransposedConv2DLayer').let(
  ndim=2,
  conv_op=tf.nn.conv2d_transpose,
).with_defaults(
  filter_size=(3, 3),
  pad='same',
  stride=(1, 1),
)