

# Cancer Diagnosis Model



import pandas as pd
import matplotlib.pyplot as plt
import re
import warnings
import numpy as np
import nltk
from sklearn.calibration import CalibratedClassifierCV
from nltk.corpus import stopwords
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import CountVectorizer
import seaborn as sns
from sklearn.metrics import confusion_matrix
from sklearn.metrics.classification import accuracy_score, log_loss
from sklearn.linear_model import SGDClassifier
from scipy.sparse import hstack
from sklearn.model_selection import train_test_split
import math
from sklearn.linear_model import LogisticRegression

"""Mount the drive"""

from google.colab import drive
drive.mount('/content/drive')



""" Examine data"""

data = pd.read_csv('/content/training_variants')
data

data_text = pd.read_csv("/content/training_text", sep = "\|\|", engine = "python", names = ["ID","TEXT"], skiprows = 1)
data_text.head()

data_text['TEXT'][1]

lu = data_text['TEXT'][1].split()
print(lu)

gene_vectorize = CountVectorizer()
train_gene_feature_onehotCodin = gene_vectorize.fit_transform(lu)
lop=gene_vectorize.vocabulary_
print(lop)

result = pd.merge(data, data_text, on ='ID', how = 'left')

lst = []
for k in lop.keys():  
  if(k=="cbl" or k=="w802*" or k=="q249e" or k=="n454d"):
       lst.append(k)
print(lst)




"""# Pre-processing text"""

import string
regex1 = re.compile('[%s]' % re.escape(string.digits))
regex2 = re.compile('[%s]' % re.escape(string.punctuation))
def remove(sentence):
  reg = regex1.sub('',sentence)
  reg = regex2.sub('',reg)
  return reg

data_text['TEXT'] = data_text['TEXT'].apply(lambda x: remove(str(x)))

#replacing every null value  with gene value and variations.

result.loc[result['TEXT'].isnull(),'TEXT'] = result['Gene'] +' '+result['Variation']

y_true = result['Class'].values 
X_train, X_test, Y_train, Y_test = train_test_split(result, 
                                                    y_true, 
                                                    stratify = y_true, 
                                                    test_size = 0.2)
X_train_cv, X_test_cv, Y_train_cv, Y_test_cv = train_test_split(X_train, Y_train, 
                       stratify = Y_train, test_size = 0.2)



"""#Plotting confusion matrix."""

def plot_confusion_matrix(test_y, predict_y):
    C = confusion_matrix(test_y, predict_y)
    
    labels = [1,2,3,4,5,6,7,8,9]
    # representing A in heatmap format
    print("-"*20, "Confusion matrix", "-"*20)
    plt.figure(figsize = (20,7))
    sns.heatmap(C, annot = True, cmap = "YlGnBu", fmt = ".3f", 
                xticklabels = labels, yticklabels = labels)
    plt.xlabel('Predicted Class')
    plt.ylabel('Original Class')
    plt.show()

"""# Creating random model for benchmarking"""

# Test dataset
test_data_len = X_test.shape[0]
# Number of rows equals number of test datapoints
test_predicted_y = np.zeros((test_data_len,9))
for i in range(test_data_len):
    # generate 9 random  numbers for our random classes.
    rand_probs = np.random.rand(1,9)
    # divide each with the sum of all
    test_predicted_y[i] = ((rand_probs/sum(sum(rand_probs)))[0])
print("Log loss on Test Data using Random Model",
      log_loss(Y_test, test_predicted_y, eps=1e-15))

# get the max probability
predicted_y = np.argmax(test_predicted_y, axis = 1) 
plot_confusion_matrix(Y_test, predicted_y+1)

cv_data_len = X_test_cv.shape[0]

# Cross validation dataset
cv_predicted_y = np.zeros((cv_data_len,9)) 
for i in range(cv_data_len):
    rand_probs = np.random.rand(1,9) 
    cv_predicted_y[i] = ((rand_probs/sum(sum(rand_probs)))[0]) 

print("Log loss on Cross Validation Data using Random Model",
      log_loss(Y_test_cv, cv_predicted_y, eps = 1e-15))

# one-hot encoding of gene feature.
gene_vectorizer = CountVectorizer()
train_gene_feature_onehotCoding = gene_vectorizer.fit_transform(X_train['Gene'])
test_gene_feature_onehotCoding = gene_vectorizer.transform(X_test['Gene'])
cv_gene_feature_onehotCoding = gene_vectorizer.transform(X_train_cv['Gene'])

# one-hot encoding of variation feature.
variation_vectorizer = CountVectorizer()
train_variation_feature_onehotCoding = variation_vectorizer.fit_transform(X_train['Variation'])
test_variation_feature_onehotCoding = variation_vectorizer.transform(X_test['Variation'])
cv_variation_feature_onehotCoding = variation_vectorizer.transform(X_train_cv['Variation'])

# one-hot encoding of text feature.
# Minimum frequency for words = 3 and remove all stop words
text_vectorizer = CountVectorizer(min_df = 3, stop_words = 'english')
train_text_feature_onehotCoding = text_vectorizer.fit_transform(X_train['TEXT'])
train_text_feature_onehotCoding = normalize(train_text_feature_onehotCoding, axis = 0)
test_text_feature_onehotCoding = text_vectorizer.transform(X_test['TEXT'])
test_text_feature_onehotCoding = normalize(test_text_feature_onehotCoding, axis = 0)
cv_text_feature_onehotCoding = text_vectorizer.transform(X_train_cv['TEXT'])
cv_text_feature_onehotCoding = normalize(cv_text_feature_onehotCoding, axis = 0)

# merging gene, variation and text features
train_gene_var_onehotCoding = hstack((train_gene_feature_onehotCoding,
                                      train_variation_feature_onehotCoding))
test_gene_var_onehotCoding = hstack((test_gene_feature_onehotCoding,
                                     test_variation_feature_onehotCoding))
cv_gene_var_onehotCoding = hstack((cv_gene_feature_onehotCoding,
                                   cv_variation_feature_onehotCoding))

train_x_onehotCoding = hstack((train_gene_var_onehotCoding, 
                               train_text_feature_onehotCoding)).tocsr()
train_y = np.array(list(X_train['Class']))

test_x_onehotCoding = hstack((test_gene_var_onehotCoding, 
                              test_text_feature_onehotCoding)).tocsr()
test_y = np.array(list(X_test['Class']))

cv_x_onehotCoding = hstack((cv_gene_var_onehotCoding, 
                            cv_text_feature_onehotCoding)).tocsr()
cv_y = np.array(list(X_train_cv['Class']))


"""# Logistic Regression with class balancing.

### Selecting best alpha value
"""

alpha = [10 ** x for x in range(-6, 3)]
cv_log_error_array = []
for i in alpha:
    print("for alpha =", i)
    clf = SGDClassifier(class_weight='balanced', 
                        alpha = i, penalty = 'l2', 
                        loss = 'log', random_state = 42)
    clf.fit(train_x_onehotCoding, train_y)
    sig_clf = CalibratedClassifierCV(clf, method = "sigmoid")
    sig_clf.fit(train_x_onehotCoding, train_y)
    sig_clf_probs = sig_clf.predict_proba(cv_x_onehotCoding)
    cv_log_error_array.append(log_loss(cv_y, sig_clf_probs, 
                                       labels = clf.classes_, eps = 1e-15))
    print("Log Loss :",log_loss(cv_y, sig_clf_probs))
    

"""### Train with the best alpha"""

best_alpha = np.argmin(cv_log_error_array)
clf = SGDClassifier(class_weight = 'balanced', 
                    alpha = alpha[best_alpha], penalty = 'l2', 
                    loss='log', random_state = 42)
clf.fit(train_x_onehotCoding, train_y)
sig_clf = CalibratedClassifierCV(clf, method = "sigmoid")
sig_clf.fit(train_x_onehotCoding, train_y)

predict_y = sig_clf.predict_proba(train_x_onehotCoding)
print("The train log loss is:",
      log_loss(Y_train, predict_y, labels = clf.classes_, eps = 1e-15))
predict_y = sig_clf.predict_proba(cv_x_onehotCoding)
print("The cross validation log loss is:",
      log_loss(Y_train_cv, predict_y, labels = clf.classes_, eps = 1e-15))
predict_y = sig_clf.predict_proba(test_x_onehotCoding)
print("The test log loss is:",
      log_loss(Y_test, predict_y, labels = clf.classes_, eps = 1e-15))



"""# Model evaluation"""

def predict_and_plot_confusion_matrix(train_x, train_y,
                                      test_x, test_y, clf):
    clf.fit(train_x, train_y)
    sig_clf = CalibratedClassifierCV(clf, method = "sigmoid")
    sig_clf.fit(train_x, train_y)
    pred_y = sig_clf.predict(test_x)

    # Display number of data points that are misclassified
    print("Number of mis-classified points :", 
          np.count_nonzero((pred_y- test_y))/test_y.shape[0])
    plot_confusion_matrix(test_y, pred_y)

clf = SGDClassifier(class_weight = 'balanced', 
                    alpha = alpha[best_alpha], penalty = 'l2', 
                    loss = 'log', random_state = 42)
predict_and_plot_confusion_matrix(train_x_onehotCoding, 
                                  train_y, cv_x_onehotCoding, 
                                  cv_y, clf)



"""# Feature importance for interpretability of our model."""


def getImportantFeatures(indices, gene, variation, text, noOfFeatures):
 
    gene_features = gene_vectorizer.get_feature_names()
    variation_features = variation_vectorizer.get_feature_names()
    text_features = text_vectorizer.get_feature_names()
    
    gene_feat_len = len(gene_features)
    var_feat_len = len(variation_features)
    text_features_len =len(text_features)
    
    word_present = 0
    for i, v in enumerate(indices):
        if v < gene_feat_len:
            word = gene_features[v]
            if word == gene:
                word_present += 1
                print("{}st Gene feature [{}] is present in query point [{}]".format(i+1, word,bool_var))
                    
        elif (v < gene_feat_len + var_feat_len):
            word = variation_features[v - gene_feat_len]           
            if word == variation:
                word_present += 1
                print("{}th Variation feature [{}] is present in query point".format(i+1, word))
        else:
            word = text_features[v - (gene_feat_len + var_feat_len)]

            if word in text.split():              
                word_present += 1
                print("{}th Text feature [{}] is present in query point".format(i+1, word))
                    
    print("-"*63)                
    print("Out of the top "+str(noOfFeatures)+" features "+
          str(word_present)+" are present in query point")
    print("-"*63)

testDataPoint = 500
top_features = 1000
predicted_cls = sig_clf.predict(test_x_onehotCoding[testDataPoint])
print("Predicted Class :", predicted_cls[0])
print("Predicted Class Probabilities:", np.round(sig_clf.predict_proba(test_x_onehotCoding[testDataPoint]),4))
print("Actual Class :", test_y[testDataPoint])
indices = np.argsort(-1*abs(clf.coef_))[predicted_cls-1][:,:top_features]
getImportantFeatures(indices[0], X_test.iloc[testDataPoint]["Gene"], 
                     X_test.iloc[testDataPoint]["Variation"], 
                     X_test.iloc[testDataPoint]["TEXT"], top_features)

