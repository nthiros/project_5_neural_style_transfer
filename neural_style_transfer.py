#!/usr/bin/env python
# coding: utf-8
import keras.preprocessing as kp
import matplotlib.pyplot as plt
import numpy as np

content_path = './main_hall.jpg'
style_path = './starry_night.jpg'

# Load image to get geometry
temp_img = kp.image.load_img(content_path)
width,height = temp_img.size

# fix the number of rows, while adapting the aspect ratio
img_rows = 400
img_cols = int(width * img_rows / height)

# Load content image
content_img = kp.image.load_img(content_path, target_size=(img_rows, img_cols))
content_img = kp.image.img_to_array(content_img)
# plt.figure()
# plt.imshow(content_img.astype(int))

# Load style image
style_img = kp.image.load_img(style_path, target_size=(img_rows, img_cols))
style_img = kp.image.img_to_array(style_img)
# plt.figure()
# plt.imshow(style_img.astype(int))
# 
# plt.show()

content_img[:, :, 0] -= 103.939
content_img[:, :, 1] -= 116.779
content_img[:, :, 2] -= 123.68
content_img = np.expand_dims(content_img, axis=0)

style_img[:, :, 0] -= 103.939
style_img[:, :, 1] -= 116.779
style_img[:, :, 2] -= 123.68
style_img = np.expand_dims(style_img, axis=0)


# Next, let's instantiate a VGG19 model for the content image:

import vgg
import keras.backend as K
import keras.layers as kl
import keras.models as km

# Note that we'll be working quite a bit with the TensorFlow objects that underlie Keras
content_model_input = kl.Input(tensor=K.tf.Variable(content_img))

content_base_model = vgg.VGG19(input_tensor=content_model_input)
evaluator = K.function([content_base_model.input],[content_base_model.output])
feature_maps = evaluator([content_img])
# plt.imshow(feature_maps[0][0,:,:,500])
# plt.show()





# Define the layer outputs that we are interested in
content_layers = ['block4_conv2']

# Get the tensor outputs of those layers
content_outputs = [content_base_model.get_layer(n).output for n in content_layers]

# Instantiate a new model with those outputs as outputs
content_model = km.Model(inputs=content_base_model.inputs,outputs=[content_base_model.get_layer(n).output for n in content_layers])


# In[5]:


# This is not used any further, it's just for visualizing the features
evaluator = K.function([content_model.input],[content_model.output])
feature_maps = evaluator([content_img])
# plt.imshow(feature_maps[0][0,:,:,125])
# plt.show()


#! Change me
style_layers = ['block1_relu1', 'block2_relu1', 'block3_relu1', 'block4_relu1', 'block5_relu1']

style_base_model = vgg.VGG19(input_tensor=kl.Input(tensor=K.tf.Variable(style_img)))
style_outputs = [style_base_model.get_layer(n).output for n in style_layers]

#! Change me
style_model = km.Model(inputs=style_base_model.inputs, outputs=[style_base_model.get_layer(n).output for n in style_layers])
style_outputs = style_model.outputs


# What are we saying about the size of the input image here?
blended_model_input = kl.Input(shape=content_img.shape[1:])
blend_base_model = vgg.VGG19(input_tensor=blended_model_input)
blend_outputs = content_layers + style_layers
#! Change me
blend_model = km.Model(inputs=blend_base_model.inputs, outputs=[blend_base_model.get_layer(n).output for n in blend_outputs])
# Separate the model outputs into those intended for comparison with the content layer and the style layer
blend_content_outputs = [blend_model.outputs[0]]
blend_style_outputs = blend_model.outputs[1:]
# print(blend_style_outputs)
# print(style_outputs)

from keras import backend as K

def content_layer_loss(Fp, Fx):
    #! Change me
    _,h,w,d = Fp.get_shape().as_list() #batch h w d
    tmp = (Fx - Fp)**2
    tmp = K.sum(tmp)
    denom = 2*(h*w)**(1./2.)*d**(1./2.)
    loss = tmp/denom
    return loss

content_loss = content_layer_loss(content_model.output, blend_content_outputs[0])

# The correct output of this function is 195710720.0
np.random.seed(0)
input_img = np.random.randn(1,img_rows,img_cols,3)
content_loss_evaluator = K.function([blend_model.input],[content_loss])
print("Correct: 195710720", content_loss_evaluator([input_img]))

def gram_matrix(f, M, N):
    # Accepts a (height,width,depth)-sized feature map,
    # reshapes to (M,N), then computes the inner product
    # !Change me
    reshaped = K.reshape(f, (M, N))
    G = K.dot(K.transpose(reshaped), reshaped)
    return G
    
# For a correctly implemented gram_matrix, the following code will produce 113934860.0
fmap = content_model.output
_,h,w,d = fmap.get_shape()
M = h*w
N = d
gram_matrix_evaluator = K.function([content_model.input],[gram_matrix(fmap,M,N)])
print("Correct: 113934860", gram_matrix_evaluator([content_img])[0].mean())

def style_layer_loss(Fa, Fx):
    #! Change me
    _, h, w, d = Fa.get_shape().as_list()
    Ga = gram_matrix(Fa, h*w, d) 
    Gx = gram_matrix(Fx, h*w, d) 
    L = K.sum((Ga - Gx)**2)
    return L/(4*h*w*h*w*d*d)

style_loss_0 = style_layer_loss(style_model.output[0], blend_style_outputs[0])

# The correct output of this function is 220990.31
np.random.seed(0)
input_img = np.random.randn(1,img_rows,img_cols,3)
style_loss_evaluator = K.function([blend_model.input],[style_loss_0])
print("Correct: 220990.31", style_loss_evaluator([input_img])[0])


style_loss = 0
for i in range(5):
    style_loss += 0.2*style_layer_loss(style_model.output[i], blend_style_outputs[i])
    
# The correct output of this function is 177059700.0
np.random.seed(0)
input_img = np.random.randn(1,img_rows,img_cols,3)
style_loss_evaluator = K.function([blend_model.input],[style_loss])
print("Correct: 177059700.0", style_loss_evaluator([input_img]))


# ## Prior loss (regularization)
# While this doesn't have much to do with neural networks, it's part of the problem specification.  In particular, we want to make sure that our blended image isn't too noisy.  To do this, we'll simply add a penalty on [total variation](https://en.wikipedia.org/wiki/Total_variation), which is simply the summed up absolute values of the derivatives.

# In[ ]:


tv_loss = K.tf.image.total_variation(blend_model.input)


# ## Total loss
# Finally, we can add these three losses up, scaled by some arbitrary weighting factors, to get a total loss:

# In[ ]:


alpha = 5.0
beta = 2e3
gamma = 1e-3

total_loss = alpha*content_loss + beta*style_loss + gamma*tv_loss
    
# The correct output of this function is 1.7715756e+12
np.random.seed(0)
input_img = np.random.randn(1,img_rows,img_cols,3)
total_loss_evaluator = K.function([blend_model.input],[total_loss])
print("Correct: 1.7715756e12", total_loss_evaluator([input_img]))

grads = K.gradients(total_loss,blend_model.input)[0]


# This produces a tensor, but what we need is a function that takes our input image as an input, and outputs the loss and the gradient of the loss.  We can use the tensorflow 'function' to do this

# In[ ]:


loss_and_grad_evaluator = K.function([blend_model.input],[total_loss,grads])

np.random.seed(0)
input_img = np.random.randn(1, img_rows, img_cols, 3)
l0, g0 = loss_and_grad_evaluator([input_img])
# Correct value of l0 is 3.5509e11
# Correct value of first element in g0 is -7.28989e2
print("Correct: 3.5509e11", l0)
print("Correct: -7.28989e2", g0[0][0][0][0])


class LossWrapper:
    
    def __init__(self, x):
        self.l0, self.g0 = loss_and_grad_evaluator([x])

    def loss(self, x):
        x = x.reshape((1, img_rows, img_cols, 3))
        self.l0, self.g0 = loss_and_grad_evaluator([x])
        return self.l0[0].astype(np.float64)

    def grad(self, x):
        return np.asarray(self.g0.ravel().astype(np.float64))

# Slow gradient descent.
# lr = 0.0001
# import time
# start = int(time.time())
# for i in range(100000):
#     l0, g0 = loss_and_grad_evaluator([input_img])
#     if(np.isnan(l0[0])):
#         break
#     input_img -= lr*g0
#     if (i+1) % 10 == 0:
#         print("Loss: {}. Step: {}. tps: {}".format(l0[0], i, (int(time.time()) - start)/i))
#     if (i+1) % 1000 == 0:
#         plt.figure()
#         plt.imshow(input_img[0])
#         plt.savefig('{}_{}.png'.format(l0[0], i))
#         plt.close()

# We can now evaluate the loss and gradient for an arbitrary image input.  All that's left is to solve the minimization problem.  The authors of the original neural style transfer paper use l_bfgs.  There is a convenient implementation of this algorithm in scipy
# NOTE: I can't get lbfgs to work.
import scipy.optimize as sio

grad_evaluator = K.function([blend_model.input], [grads])
lw = LossWrapper(input_img)
x, f, d = sio.fmin_l_bfgs_b(func=lw.loss, x0=input_img.ravel(), fprime=lw.grad, maxiter=500)
x = x.reshape((img_rows, img_cols, 3))
x[:, :, 0] += 103.939
x[:, :, 1] += 116.779
x[:, :, 2] += 123.68
plt.imshow(x.astype(np.int32))
plt.savefig("lfbgs_mean_added.png")
plt.show()
