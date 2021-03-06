'''
All the model tuning codes are here.
'''
import warnings
warnings.filterwarnings("ignore")
import numpy as np
from sklearn.model_selection import GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn.model_selection import cross_val_score
from xgboost import XGBClassifier
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
from hyperopt import SparkTrials

def svmTuning(xTr, yTr, xTe, yTe, clflsvm, clfrsvm, cvMethod, dep, sensor, runIdx, savePath = './'):
    '''
    Tuning the SVM classifiers with given train and test data. This is one run for the outer loop.
    Tr: train, Te: test
    clf- classifier
    cvMethod: The cv object defined previously.
    dep: Deployment name, e.g. aisle rug
    sensor: Sensor id and sensor node name, e.g: '1_3' staands for sensor 1 location 3
    runIdx: The index of outer loop
    savePath: The folder to save the .npz and .txt files

    Also, it will return the test accuracy.
    '''
    gp_svm = {'C': [0.01, 0.1, 1, 10], 'gamma': [0.01, 0.1, 1, 10, 'scale']}
    gd_sr_lsvm = GridSearchCV(estimator=clflsvm,
                        param_grid=gp_svm,
                        scoring='accuracy',
                        cv=cvMethod,
                        n_jobs=-1,
                        refit=True,
                        verbose=0)
    gd_sr_rsvm = GridSearchCV(estimator=clfrsvm,
                        param_grid=gp_svm,
                        scoring='accuracy',
                        cv=cvMethod,
                        n_jobs=-1,
                        refit=True,
                        verbose=0)
    gd_sr_lsvm.fit(xTr, yTr)
    gd_sr_rsvm.fit(xTr, yTr)

    best_lsvm = gd_sr_lsvm.best_estimator_
    best_rsvm = gd_sr_rsvm.best_estimator_

    pred_lsvm = best_lsvm.predict(xTe)
    pred_rsvm = best_rsvm.predict(xTe)
    cm_lsvm = confusion_matrix(yTe, pred_lsvm)
    cm_rsvm = confusion_matrix(yTe, pred_rsvm)

    saveName_lsvm = savePath + dep + '_' + sensor + '_' + runIdx + '_lsvm'
    saveName_rsvm = savePath + dep + '_' + sensor + '_' + runIdx + '_rsvm'

    np.save(saveName_lsvm + '.npy', cm_lsvm)
    np.save(saveName_rsvm + '.npy', cm_rsvm)

    with open(saveName_lsvm + '.txt', 'w') as f:
            f.write(np.array2string(cm_lsvm, separator=', '))
    with open(saveName_rsvm + '.txt', 'w') as f:
            f.write(np.array2string(cm_rsvm, separator=', '))

    return (best_lsvm.score(xTe,yTe), best_rsvm.score(xTe,yTe))


def rfTuning(xTr, yTr, xTe, yTe, clfrf, cvMethod, dep, sensor, runIdx, savePath):
    '''
    Tuning random forest with bayes optimization
    '''
    n_estimators = [int(x) for x in np.linspace(start = 200, stop = 2000, num = 10)]
    max_features = ['auto', 'sqrt', 'log2']
    max_depth = [int(x) for x in np.linspace(10, 110, num = 11)]
    max_depth.append(None)
    min_samples_split = [2, 5, 10]
    min_samples_leaf = [1, 2, 3, 4]
    bootstrap = [True, False]
    criterion = ["gini", "entropy"]

    param_space = {
    'max_depth': hp.choice('max_depth', max_depth),
    'max_features': hp.choice('max_features', max_features),
    'n_estimators': hp.choice('n_estimators', n_estimators),
    'criterion': hp.choice('criterion', criterion),
    'min_samples_split': hp.choice('min_samples_split', min_samples_split),
    'min_samples_leaf': hp.choice('min_samples_leaf', min_samples_leaf),
    'bootstrap': hp.choice('bootstrap', bootstrap)}

    def acc_model(params):
        acc_score = cross_val_score(clfrf, xTr, yTr, cv=cvMethod)
        return acc_score.mean()
    
    def f(params):
        acc = acc_model(params)
        return {'loss': -acc, 'status': STATUS_OK}

    
    trials = Trials()
    best = fmin(f, param_space, algo=tpe.suggest, max_evals=60, trials=trials) #Get the index from space
    # best = fmin(f, param_space, algo=tpe.suggest, max_evals=100, trials=SparkTrials) #Get the index from space

    # indexes
    bstp = int(best['bootstrap'])
    cri = int(best['criterion'])
    m_dep = int(best['max_depth'])
    m_fea = int(best['max_features'])
    m_lef = int(best['min_samples_leaf'])
    m_sp = int(best['min_samples_split'])
    n_est = int(best['n_estimators'])

    best_rf = RandomForestClassifier(n_estimators=n_estimators[n_est],bootstrap=bootstrap[bstp], criterion=criterion[cri],  
                                    max_depth=max_depth[m_dep], max_features=max_features[m_fea], min_samples_leaf=min_samples_leaf[m_lef], 
                                    min_samples_split=min_samples_split[m_sp])

    best_rf.fit(xTr, yTr)
    pred = best_rf.predict(xTe)
    cm = confusion_matrix(yTe, pred)

    saveName = savePath + dep + '_' + sensor + '_' + runIdx + '_rf'

    np.save(saveName + '.npy', cm)

    with open(saveName + '.txt', 'w') as f:
            f.write(np.array2string(cm, separator=', '))

    return best_rf.score(xTe,yTe)

def lrTuning(xTr, yTr, xTe, yTe, clflr, cvMethod, dep, sensor, runIdx, savePath = './'):
    '''
    This is for multi-class logistic regression.
    '''
    gp_lr={"C":[0.001,0.01,0.1,1,10,100], "multi_class":["auto", "ovr", "multinomial"], "max_iter":[100, 200, 300, 400, 500]}
    gd_sr_lr = GridSearchCV(estimator=clflr,
	                    param_grid=gp_lr,
	                    scoring='accuracy',
	                    cv=cvMethod,
	                    n_jobs=-1,
	                    refit=True,
	                    verbose=0)
    gd_sr_lr.fit(xTr, yTr)
    best_lr = gd_sr_lr.best_estimator_
    pred = best_lr.predict(xTe)
    cm = confusion_matrix(yTe, pred)

    saveName = savePath + dep + '_' + sensor + '_' + runIdx + '_lr'

    np.save(saveName + '.npy', cm)

    with open(saveName + '.txt', 'w') as f:
            f.write(np.array2string(cm, separator=', '))

    return best_lr.score(xTe,yTe)

def adbTuning(xTr, yTr, xTe, yTe, clfadb, cvMethod, dep, sensor, runIdx, savePath = './'):
    '''
    Multi-class adaBoost Tuning with Bayesian Optimizatrion
    '''
    n_estimators = [int(x) for x in np.linspace(start = 50, stop = 1000, num = 80)]
    learning_rate = [.001, 0.01, 0.05, 0.1]

    param_space = {'n_estimators': hp.choice('n_estimators', n_estimators), 'learning_rate': hp.choice('learning_rate', learning_rate)}

    def acc_model(params):
        acc_score = cross_val_score(clfadb, xTr, yTr, cv=cvMethod)
        return acc_score.mean()

    def f(params):
        acc = acc_model(params)
        return {'loss': -acc, 'status': STATUS_OK}

    trials = Trials()
    best = fmin(f, param_space, algo=tpe.suggest, max_evals=60, trials=trials) #Get the index from space

    n_est = int(best['n_estimators'])
    lr = int(best['learning_rate'])

    best_adb = AdaBoostClassifier(n_estimators=n_estimators[n_est], learning_rate = learning_rate[lr])
    best_adb.fit(xTr, yTr)	
    pred = best_adb.predict(xTe)
    cm = confusion_matrix(yTe, pred)

    saveName = savePath + dep + '_' + sensor + '_' + runIdx + '_adb'

    np.save(saveName + '.npy', cm)

    with open(saveName + '.txt', 'w') as f:
            f.write(np.array2string(cm, separator=', '))

    return best_adb.score(xTe,yTe)

def nbEval(xTr, yTr, xTe, yTe, clfnb, cvMethod, dep, sensor, runIdx, savePath = './'):
    '''
    Since Gaussian Naive Beyesian has nothing to be tuned, it is Eval instead of Tuning
    ''' 
    clfnb.fit(xTr, yTr)
    pred = clfnb.predict(xTe)
    cm = confusion_matrix(yTe, pred)
    saveName = savePath + dep + '_' + sensor + '_' + runIdx + '_nb'
    np.save(saveName + '.npy', cm)
    with open(saveName + '.txt', 'w') as f:
            f.write(np.array2string(cm, separator=', '))

    return clfnb.score(xTe,yTe)


def xgTuning(xTr, yTr, xTe, yTe, clfxgb, cvMethod, dep, sensor, runIdx, savePath = './'):

    max_depth = [int(x) for x in range (2, 10, 1)]
    n_estimators = [int(x) for x in range(20, 200, 10)]
    learning_rate = [0.1, 0.01, 0.05]
    min_child_weight = [int(x) for x in range (1, 10, 1)]
    gamma = [0.5, 1, 1.5, 2, 5]
    colsample_bytree = [0.1, 0.5, 0.8, 1]

    gp_xg = { 'max_depth': hp.choice('max_depth', max_depth),
            'n_estimators': hp.choice('n_estimators', n_estimators),
            'learning_rate': hp.choice('learning_rate', learning_rate),
            'min_child_weight': hp.choice('min_child_weight', min_child_weight),
            'gamma': hp.choice('gamma', gamma),
            'colsample_bytree': hp.choice('colsample_bytree', colsample_bytree)}

    def acc_model(params):
        acc_score = cross_val_score(clfxgb, xTr, yTr, cv=cvMethod)
        return acc_score.mean()

    def f(params):
        acc = acc_model(params)
        return {'loss': -acc, 'status': STATUS_OK}

    trials = Trials()
    best = fmin(f, gp_xg, algo=tpe.suggest, max_evals=60, trials=trials) #Get the index from space

    # indexes
    n_est = int(best['n_estimators'])
    m_dep = int(best['max_depth'])
    lr = int(best['learning_rate'])
    mcw = int(best['min_child_weight'])
    gm = int(best['gamma'])
    cbt = int(best['colsample_bytree'])

    best_xg = XGBClassifier(n_estimators=n_estimators[n_est], max_depth=max_depth[m_dep], learning_rate=learning_rate[lr],  
                                    min_child_weight=min_child_weight[mcw], gamma=gamma[gm], colsample_bytree=colsample_bytree[cbt],
                                    objective='multi:softmax')
    best_xg.fit(xTr, yTr)
    pred = best_xg.predict(xTe)
    cm = confusion_matrix(yTe, pred)

    saveName = savePath + dep + '_' + sensor + '_' + runIdx + '_xg'

    np.save(saveName + '.npy', cm)

    with open(saveName + '.txt', 'w') as f:
            f.write(np.array2string(cm, separator=', '))

    return best_xg.score(xTe,yTe)

def knnTuning(xTr, yTr, xTe, yTe, clfknn, cvMethod, dep, sensor, runIdx, savePath = './'):
    gp_knn={'n_neighbors':[3, 4, 5, 6, 7, 8],
            'weights':['uniform', 'distance'],
            'algorithm':['auto', 'ball_tree','kd_tree']}

    gd_sr_knn = GridSearchCV(estimator=clfknn,
                        param_grid=gp_knn,
                        scoring='accuracy',
                        cv=cvMethod,
                        n_jobs=-1,
                        refit=True,
                        verbose=0)

    gd_sr_knn.fit(xTr, yTr)
    best_knn = gd_sr_knn.best_estimator_
    pred = best_knn.predict(xTe)
    cm = confusion_matrix(yTe, pred)

    saveName = savePath + dep + '_' + sensor + '_' + runIdx + '_knn'

    np.save(saveName + '.npy', cm)

    with open(saveName + '.txt', 'w') as f:
            f.write(np.array2string(cm, separator=', '))

    return best_knn.score(xTe,yTe)

def etTuning(xTr, yTr, xTe, yTe, clfet, cvMethod, dep, sensor, runIdx, savePath):
    '''
    Tuning extra trees with bayes optimization. The setup is almost the same with random forest.
    '''
    n_estimators = [int(x) for x in np.linspace(start = 200, stop = 2000, num = 10)]
    max_features = ['auto', 'sqrt', 'log2']
    max_depth = [int(x) for x in np.linspace(10, 110, num = 11)]
    max_depth.append(None)
    min_samples_split = [2, 5, 10]
    min_samples_leaf = [1, 2, 3, 4]
    bootstrap = [True, False]
    criterion = ["gini", "entropy"]

    param_space = {
    'max_depth': hp.choice('max_depth', max_depth),
    'max_features': hp.choice('max_features', max_features),
    'n_estimators': hp.choice('n_estimators', n_estimators),
    'criterion': hp.choice('criterion', criterion),
    'min_samples_split': hp.choice('min_samples_split', min_samples_split),
    'min_samples_leaf': hp.choice('min_samples_leaf', min_samples_leaf),
    'bootstrap': hp.choice('bootstrap', bootstrap)}

    def acc_model(params):
        acc_score = cross_val_score(clfet, xTr, yTr, cv=cvMethod)
        return acc_score.mean()
    
    def f(params):
        acc = acc_model(params)
        return {'loss': -acc, 'status': STATUS_OK}

    
    trials = Trials()
    best = fmin(f, param_space, algo=tpe.suggest, max_evals=60, trials=trials) #Get the index from space

    # indexes
    bstp = int(best['bootstrap'])
    cri = int(best['criterion'])
    m_dep = int(best['max_depth'])
    m_fea = int(best['max_features'])
    m_lef = int(best['min_samples_leaf'])
    m_sp = int(best['min_samples_split'])
    n_est = int(best['n_estimators'])

    best_et = RandomForestClassifier(n_estimators=n_estimators[n_est],bootstrap=bootstrap[bstp], criterion=criterion[cri],  
                                    max_depth=max_depth[m_dep], max_features=max_features[m_fea], min_samples_leaf=min_samples_leaf[m_lef], 
                                    min_samples_split=min_samples_split[m_sp])

    best_et.fit(xTr, yTr)
    pred = best_et.predict(xTe)
    cm = confusion_matrix(yTe, pred)

    saveName = savePath + dep + '_' + sensor + '_' + runIdx + '_et'

    np.save(saveName + '.npy', cm)

    with open(saveName + '.txt', 'w') as f:
            f.write(np.array2string(cm, separator=', '))

    return best_et.score(xTe,yTe)
