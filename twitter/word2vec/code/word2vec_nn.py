# -*- coding: utf-8 -*-
"""word2vec_nn.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1RIVOJN_zUsFTAMHjakXDO5UgdNb6XbbF

### I used [this dataset](https://www.kaggle.com/arkhoshghalb/twitter-sentiment-analysis-hatred-speech) for sentiment analysis .
### My task is recognizing speech with sexist and racist sentiment .
"""

from gensim.models import KeyedVectors
import pandas as pd 
import numpy as np 
import nltk 
import re
import math
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

nltk.download('wordnet')
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

from nltk.stem import WordNetLemmatizer 
from nltk.corpus import wordnet 
from nltk import word_tokenize, pos_tag
from collections import defaultdict

import tensorflow as tf
from tensorflow.keras import layers
import keras.backend as K

"""### I useed pre-trained [google news vectors](https://code.google.com/archive/p/word2vec/) as word2vec model ."""

model = KeyedVectors.load_word2vec_format(open('/content/drive/My Drive/parto tech/sentiment_analysis/twitter/word2vec/word2vec.bin','rb'), binary=True)

train = pd.read_csv('/content/drive/My Drive/parto tech/sentiment_analysis/twitter/train.csv')

def remove_at_and_hashtag (text) :
  text = text.replace('@user',' ')
  text = re.sub('[^a-zA-Z]', ' ', text)

    # Single character removal
  text = re.sub(r"\s+[a-zA-Z]\s+", ' ', text)

    # Removing multiple spaces
  text = re.sub(r'\s+', ' ', text)
  return text.replace('#',' ')
  #TODO : use hashtags

"""### At cell below I developed functions to lemmatize tokens based on their POS tag using nltk library."""

# lemmatizing with NLTK lemmatize


def get_wordnet_pos(pos):
    """Map POS tag to first character lemmatize() accepts"""
    tag = pos.upper()
    tag_dict = {"J": wordnet.ADJ,
                "N": wordnet.NOUN,
                "V": wordnet.VERB,
                "R": wordnet.ADV}

    return tag_dict.get(tag, wordnet.NOUN)


lem = WordNetLemmatizer()

def my_lemmatizer (text) :
  tokens = word_tokenize(text)
  lemmatized=[]
  poses = [get_wordnet_pos(tag[0]) for tag in pos_tag(tokens)]
  for i in range (len(tokens)):
    lemma = lem.lemmatize(tokens[i],poses[i])
    lemmatized.append(lemma)
  return ' '.join(lemmatized)

train['tweet'] = train['tweet'].apply(remove_at_and_hashtag)
train['tweet'] = train['tweet'].apply(my_lemmatizer)

"""### sentence2vec function creates a vector for each sentence based on the mean of it's words vector. If there was a word which it was not present in the pre-trained word2vec model, I've considered zero vector for that ."""

def sentence2vec(row,w2v) :
  vector = np.zeros((1,300)) 
  words = row.split()
  count = 0 
  for word in words :
    try :
      vector += w2v[word].reshape((1,300))
      count +=1 
    except KeyError :
      continue 
  if count != 0 :
    return vector/count
  return vector

"""### At four cells below, I've defined x and y ,then splited them to testing and training set"""

tweets = train.tweet.to_list()
embedded_tweets = [sentence2vec(tweet,model) for tweet in tweets]

y = np.array(train.label)

x_train,x_test , y_train,y_test = train_test_split(embedded_tweets,y,test_size=0.3,random_state=101)

np.shape(x_train)

"""### Because I used NN method for sentiment analysis using BERT word embedding, I prefered to train another model using neural net for word2vec word embedding for better comparison.




### at cell below i've defined NN model params.
"""

CNN1_FILTERS = 16
CNN2_FILTERS = 32
CNN3_FILTERS = 64
DNN_UNITS = 512
OUTPUT_CLASSES = 2

DROPOUT_RATE = 0.2

NB_EPOCHS = 10

"""### Here I designed the architecture of NN"""

text_model = tf.keras.Sequential([
              layers.Conv1D(filters=CNN1_FILTERS,kernel_size=3,input_shape=(300,1),activation="relu"),
              layers.MaxPool1D(),
              layers.Conv1D(filters=CNN2_FILTERS,kernel_size=4,activation="relu"),
              layers.MaxPool1D(),
              layers.Conv1D(filters=CNN3_FILTERS,kernel_size=6,activation="relu"),
              layers.MaxPool1D(),
              layers.Flatten(),
              layers.Dense(units=DNN_UNITS, activation=tf.nn.leaky_relu),
              layers.Dropout(DROPOUT_RATE),
              layers.Dense(units=DNN_UNITS, activation=tf.nn.leaky_relu),
              layers.Dropout(DROPOUT_RATE),
              layers.Dense(1,activation="sigmoid")

])

text_model.summary()

"""### Because I did not find f1-score as metrics in tensorflow.keras, I copied the code from previous versions of keras and pass function as a metric param while compiling the NN"""

def get_f1(y_true, y_pred): 
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    recall = true_positives / (possible_positives + K.epsilon())
    f1_val = 2*(precision*recall)/(precision+recall+K.epsilon())
    return f1_val

text_model.compile(loss="binary_crossentropy",
                  optimizer="adam",
                  metrics=[get_f1])

"""### reshaping data for fitting into NN"""

x_train = np.reshape(x_train,(22373,300,1))
x_test = np.reshape(x_test,(9589,300,1))
y_train = np.reshape(y_train,(22373,1))
y_test = np.reshape(y_test,(9589,1))

print(np.shape(x_train)) 
print(np.shape(y_train))

print(np.shape(x_test))
print(np.shape(y_test))

text_model.fit(
    x_train,
    y_train ,
    epochs=NB_EPOCHS,
)

np.shape(y_test)

from sklearn.metrics import f1_score , classification_report

y_pred = text_model.predict_classes(x_test)
print(f1_score(y_test,y_pred))
print(classification_report(y_test,y_pred))

"""### As we can see from output of above cell, performance has been **improved about 4%**"""