# -*- coding: utf-8 -*-
"""FinalBERT.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Vm799psRtN4tCEkEmq_r07aCVqY_x6u3

# Sentiment analysis using BERT
"""

!pip install tqdm

!pip install tensorflow-gpu

!pip install --upgrade grpcio

!pip install bert-for-tf2

!pip install sentencepiece

"""# Essential modules to be imported"""

import os 
import math
import datetime
from tqdm import tqdm
import numpy as np
import pandas as pd
import tensorflow as tf 
from tensorflow import keras 
import seaborn as sns
from sklearn.model_selection import train_test_split
import re 
from sklearn.metrics import classification_report
import keras.backend as K

"""## BERT modules"""

import bert 
from bert import BertModelLayer
from bert.loader import StockBertConfig, map_stock_config_to_params, load_stock_weights
from bert.tokenization.bert_tokenization import FullTokenizer

"""# Read data from my drive"""

train = pd.read_csv('/content/drive/My Drive/parto tech/sentiment_analysis/twitter/train.csv')
test = pd.read_csv('/content/drive/My Drive/parto tech/sentiment_analysis/twitter/test.csv')
train.drop('id',axis=1,inplace=True)
test.drop('id',axis=1,inplace=True)

"""# Defining preprocessing functions to remove user metions, tags, single characters and multiple spaces"""

def remove_at_and_hashtag (tweet) :
  tweet = tweet.replace('@user',' ')
  return tweet.replace('#',' ')

def data_processing(tweet): 
  # remove user mentions and tags
  sentence = remove_at_and_hashtag(tweet)
  
  # Single character removal
  sentence = re.sub(r"\s+[a-zA-Z]\s+", ' ', sentence)

  # Removing multiple spaces
  sentence = re.sub(r'\s+', ' ', sentence)

  return sentence

train['tweet'] = train['tweet'].apply(data_processing)

"""# Plotting data to distinguish data balance.

## Due to figure below this is unbalanced dataFrame.
"""

sns.countplot(train.label)

"""# In the four cells below I have downloaded uncased_L-12_H-768_A-12 version of BERT word embedding, unzip and moving it to "model" folder ."""

!wget https://storage.googleapis.com/bert_models/2018_10_18/uncased_L-12_H-768_A-12.zip

!unzip uncased_L-12_H-768_A-12.zip.1

os.makedirs('model',exist_ok=True)

!mv uncased_L-12_H-768_A-12/ model

"""# Keep track of essential bert files in order to be used in my final model"""

bert_model_name = 'uncased_L-12_H-768_A-12'
bert_ckpt_dir = os.path.join('model/',bert_model_name)
bert_ckpt_file = os.path.join(bert_ckpt_dir,'bert_model.ckpt')
bert_config_file = os.path.join(bert_ckpt_dir,'bert_config.json')

"""# Split train dataset to train and test . 
- train_data is 0.8 of whole data . train_data's shape is (25569,2)
- test_data is 0.2 of whole data . test_data's shape is (6394,2)
"""

train_len = (len(train) // 10) * 8
train_data , test_data = train.loc[:train_len] , train.loc[train_len:]

"""# Create a class for tokenizing and padding the tweets"""

class TweetSentimentAnalysisData :
  DATA_COLUMN = 'tweet'
  LABEL_COLUMN = 'label'


  def __init__(self,train,test,tokenizer:FullTokenizer,max_seq_len=150) :
    self.train = train 
    self.test = test 
    self.tokenizer = tokenizer 
    self.max_seq_len = 0 

    ((self.x_train,self.y_train),(self.x_test,self.y_test)) = map(self._prepare,[train,test])
    self.max_seq_len = min(self.max_seq_len,max_seq_len)
    self.x_train,self.x_test = map(self._padding,[self.x_train,self.x_test ])


  def _prepare(self,df) :
    x,y = [],[] 

    for _ , row in tqdm(df.iterrows()) :
      tweet , label = row[TweetSentimentAnalysisData.DATA_COLUMN] , row[TweetSentimentAnalysisData.LABEL_COLUMN] 

      tokens = self.tokenizer.tokenize(tweet)
      tokens = ["[CLS]"] + tokens + ["[SEP]"]

      token_ids = self.tokenizer.convert_tokens_to_ids(tokens)

      self.max_seq_len = max(self.max_seq_len,len(token_ids)) 

      x.append(token_ids) 
      y.append(label)

    return np.array(x) , np.array(y)
  

  def _padding(self,ids) :
    x = [] 
    
    for input_ids in ids :
      cut_point = min(len(input_ids),self.max_seq_len-2)
      input_ids = input_ids[:cut_point]
      input_ids = input_ids + [0]* (self.max_seq_len-len(input_ids))
      x.append(np.array(input_ids))


    return np.array(x)

"""# Create a tokenizer using BERT"""

tokenizer = FullTokenizer(vocab_file=os.path.join(bert_ckpt_dir,'vocab.txt'))

"""# Apply TweetSentimentAnalysis class to train_data and test_data"""

data = TweetSentimentAnalysisData(train_data,test_data,tokenizer,max_seq_len=150)

"""# Designing and building the architecture of neural net and take a look at net's summary"""

def create_model (max_seq_len,bert_config_file,bert_ckpt_file) :
  with tf.io.gfile.GFile(bert_config_file,'r') as reader :
    bert_config = StockBertConfig.from_json_string(reader.read())
    bert_params = map_stock_config_to_params(bert_config)
    bert_params.adapter_size = None 
    bert = BertModelLayer.from_params(bert_params,name='bert')


  input_ids = keras.layers.Input(shape=(max_seq_len,),dtype='int32',name ='input_ids') 
  bert_output = bert(input_ids)
  print(bert_output.shape)
  cls_out = keras.layers.Lambda(lambda seq : seq[:,0,:])(bert_output)
  cls_out = keras.layers.Dropout(0.5)(cls_out)
  logits = keras.layers.Dense(768,activation='tanh')(cls_out)
  logits = keras.layers.Dropout(0.5)(logits)
  logits = keras.layers.Dense(1,activation='sigmoid')(logits)


  model = keras.Model(inputs=input_ids,outputs=logits)
  model.build(input_shape=(None,max_seq_len))

  load_stock_weights(bert,bert_ckpt_file)

  return model

model = create_model(data.max_seq_len,bert_config_file,bert_ckpt_file)

model.summary()

"""# I want to use f1-score as my NN metric param, so i copied this block of code from previous versions of keras"""

import keras.backend as K

def get_f1(y_true, y_pred): 
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    recall = true_positives / (possible_positives + K.epsilon())
    f1_val = 2*(precision*recall)/(precision+recall+K.epsilon())
    return f1_val

"""# Compiling model with Adam optimizer . using of Adam optimizer is suggested !"""

model.compile(
    optimizer = keras.optimizers.Adam(1e-5),
    loss = keras.losses.BinaryCrossentropy() ,
    metrics = [get_f1] ,
)

"""# As we see in previous cells this dataset is unbalanced thus I will pass weight of each class to my model. Below I've calculate the weights using sklearn"""

from sklearn.utils import class_weight
class_weights = class_weight.compute_class_weight('balanced',classes=[0,1],y=train.label)
class_weights = dict(enumerate(class_weights))

class_weights

"""# Fitting the model for 5 epochs"""

model.fit(
    x=data.x_train ,
    y=data.y_train ,
    validation_split=0.1 ,
    batch_size = 16 ,
    shuffle = True ,
    epochs = 5 ,
    class_weight = class_weights
)

y_pred = model.predict(data.x_test)

"""# Let's take a look at classification_report of our model !"""

print(classification_report(data.y_test,K.round(y_pred)))

"""# Compared with word2vec using NN approach, f1-score of positive class (contains sexism or racism content) has been improved by 23% !!
# F1-score of negative class is still 98%

# Conclusion 
### By using BERT word embedding accuracy has imporved so much but it takes about one hour to learn because NN has more than 109 million trainable parameters
"""