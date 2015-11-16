
'''
Byron C. Wallace 

LSTM model for picking out groups (tokens) from abstracts. 
Annotated data is courtesy of Rodney Sumerscales. 

Sample use: 

    > import LSTM_extraction
    > LSTM_extraction.LSTM_exp() # assumes *-w2v.bin file exists!!!

Requires keras, sklearn and associated dependencies. 

notes to self:

    * run in python 2.x 
    * this is only groups at the moment (using LSTM)
'''


from __future__ import absolute_import
from __future__ import print_function

import sys
import pdb 

import numpy as np
np.random.seed(1337)  # for reproducibility
import scipy as sp

import pandas as pd  

import gensim 
from gensim.models import Word2Vec

from keras.preprocessing import sequence
from keras.optimizers import RMSprop
from keras.models import Sequential
from keras.layers.recurrent import LSTM
from keras.layers.core import Dense, Dropout, Activation, Flatten
from keras.layers.embeddings import Embedding
from keras.layers.convolutional import Convolution1D, MaxPooling1D
from keras.datasets import imdb

import nltk 

import matplotlib.pyplot as plt 
import seaborn as sns 

import sklearn
from sklearn.metrics import roc_curve, auc

import parse_summerscales 

#"PubMed-w2v.bin"
def load_trained_w2v_model(path="PubMed-w2v.bin"):
    m = Word2Vec.load_word2vec_format(path, binary=True)
    return m 



'''
note: this is for groups right now. the ranking performance is reasonable,
        if not great (~.7 AUC). 
'''
def LSTM_exp(wv=None, wv_dim=200, p_test=.25, n_epochs=10, use_w2v=True):
    if wv is None and use_w2v:
        print("loading embeddings...")
        wv = load_trained_w2v_model() 
        print("ok!")

    X_embedded, X_tokens, y, vectorizer, unknown_words_to_vecs, pmids = get_X_y(
            wv=wv, wv_dim=wv_dim)

    v_size = len(vectorizer.vocabulary_)

    init_vectors = []
    if use_w2v:
        #pdb.set_trace()
        #for t in vectorizer.vocabulary_:
        for token_idx, t in enumerate(vectorizer.vocabulary):
            try:
                init_vectors.append(wv[t])
            except:
                init_vectors.append(unknown_words_to_vecs[t])
        init_vectors = np.vstack(init_vectors)

    #pdb.set_trace()
    ''' build model; this should probably be factored out! '''
    print("constructing model...")
    model = Sequential()
    # embedding layer; map token indices to vector representations

    if use_w2v:
        embedding_layer = Embedding(v_size, wv_dim, weights=[init_vectors])
    else:
        print ("no initial embeddings!!")
        embedding_layer = Embedding(v_size, wv_dim)

    model.add(embedding_layer)

    model.add(LSTM(output_dim=128, 
        activation='sigmoid', inner_activation='hard_sigmoid'))
    
    # @TODO! tune
    #model.add(Dropout(0.25))
    model.add(Dense(1))
    model.add(Activation('sigmoid')) 

    model.compile(loss='binary_crossentropy',
              optimizer='adam',
              class_mode="binary")
    print("model compiled.")
  

    ''' train / test '''
    # @TODO! be sure to split at start of a pmid 
    #   (i.e., do not split midway through and abstract!)
    N = X_tokens.shape[0]
    test_n = int(p_test*N)

    X_tokens_train = X_tokens[:-test_n]
    X_tokens_test  = X_tokens[-test_n:]
    y_train  = y[:-test_n]
    y_test   = y[-test_n:]
    pmids_train = pmids[:-test_n]
    pmids_test  = pmids[-test_n:]

    print("training!")
    model.fit(X_tokens_train, y_train, nb_epoch=n_epochs)

    ''' evaluation '''
    print("ok. predicting...")
    preds = model.predict(X_tokens_test)

    fpr, tpr, thresholds = roc_curve(y_test, preds)
    cur_auc = auc(fpr, tpr)
    print("auc: %s" % cur_auc)

    ### note to self: to inspect features you can do something like:
    ### words = [vectorizer.vocabulary[j] for j in X_tokens_test[180:200]]
    return model, preds, y_test




def get_X_y(wv, wv_dim):

    pmids, sentences, lbls, vectorizer = parse_summerscales.get_tokens_and_lbls()


    # see: https://github.com/fchollet/keras/issues/233
    # num_sentences x 1 x max_token_len x wv_dim
    # number of sequences x 1 x max number of tokens (padded to max len) x word vector size
    num_sentences = len(sentences)
    #max_token_len = max([len(s) for s in sentences])

    #X_embedded = np.zeros((num_sentences, wv_dim))
    X_embedded, X_tokens = [], [] # here a sequence associated with each doc/abstract
    y = []
    

    #X_tokens = []
    cur_pmid = pmids[0]
   
    cur_x_embedded, cur_x_tokens, cur_y, token_pmid_list = [], [], [], []
 
    unknown_words_to_vecs = {}

    for idx, s in enumerate(sentences):
        if cur_pmid != pmids[idx]:
            X_embedded.append(np.vstack(cur_x_embedded))
            X_tokens.append(np.vstack(cur_x_tokens))
            y.append(np.array(cur_y))
            cur_x_embedded, cur_x_tokens, cur_y = [], [], []
            cur_pmid = pmids[idx]
        
        for j, t in enumerate(s): 
            try:
                v = wv[t]
            except:
                print("%s not known!" % t)

                # or maybe use 0s???
                if not t in unknown_words_to_vecs:
                    v = np.random.uniform(-1,1,wv_dim)
                    unknown_words_to_vecs[t] = v 
                
                v = unknown_words_to_vecs[t]

            cur_x_embedded.append(v)
            cur_x_tokens.append(vectorizer.vocabulary_[t])
            token_pmid_list.append(cur_pmid)

        cur_y.extend(lbls[idx])


    X_embedded.append(np.vstack(cur_x_embedded))
    X_tokens.append(np.vstack(cur_x_tokens))
    y.append(np.array(cur_y))

    X_embedded = np.vstack(X_embedded)
    X_tokens   = np.vstack(X_tokens)
    y          = np.hstack(y)
    return X_embedded, X_tokens, y, vectorizer, unknown_words_to_vecs, token_pmid_list



def preprocess_texts(texts, m, dim=200):

    for text in texts: 
        tokenized_text = nltk.word_tokenize(text)
        for t in tokenized_text: 
            try:
                v = m[t]
            except:
                # or maybe use 0s???
                v = np.random.uniform(-1,1,dim)


def setup_model(vocab, X):

    model = Sequential()



### ignore this for now.
def load_trained_d2v_model(path="Doc2Vec/400_pvdbow_doc2vec.d2v"):
    ''' @TODO swap in MEDLINE trained variant '''
    m = Doc2Vec.load(path)
    return m


### @TODO revisit this for loading up PMC + MEDLINE model!
def load_bin_vec(fname, vocab):
    """
    Loads 300x1 word vecs from Google (Mikolov) word2vec
    """
    word_vecs = {}
    with open(fname, "rb") as f:
        header = f.readline()
        vocab_size, layer1_size = map(int, header.split())
        binary_len = np.dtype('float32').itemsize * layer1_size
        for line in xrange(vocab_size):
            word = []
            while True:
                ch = f.read(1)
                if ch == ' ':
                    word = ''.join(word)
                    break
                if ch != '\n':
                    word.append(ch)
            if word in vocab:
               word_vecs[word] = np.fromstring(f.read(binary_len), dtype='float32')
            else:
                f.read(binary_len)
    return word_vecs



