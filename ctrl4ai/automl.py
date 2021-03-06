# -*- coding: utf-8 -*-
"""
Created on Tue May 19 19:00:36 2020

@author: Shaji,Charu,Selva
"""

from . import preprocessing
from . import helper
from . import exceptions


import sklearn
import pandas as pd
pd.set_option('mode.chained_assignment', None)

def preprocess(dataset,
               learning_type,
               target_variable=None,
               target_type=None,
               impute_null_method='central_tendency',
               tranform_categorical='label_encoding',
               categorical_threshold=0.3,
               remove_outliers=False,
               log_transform=None,
               drop_null_dominated=True,
               dropna_threshold=0.7,
               derive_from_datetime=True,
               ohe_ignore_cols=[],
               feature_selection=True,
               define_continuous_cols=[],
               define_categorical_cols=[]
               ):
    """
    dataset=pandas DataFrame (required)
    learning_type='supervised'/'unsupervised' (required)
    target_variable=Target/Dependent variable (required for supervised learning type)
    target_type='continuous'/'categorical' (required for supervised learning type)
    impute_null_method='central_tendency' (optional) [Choose between 'central_tendency' and 'KNN']
    tranform_categorical='label_encoding' (optional) [Choose between 'label_encoding' and 'one_hot_encoding']
    categorical_threshold=0.3 (optional) [Threshold for determining categorical column based on the percentage of unique values]
    remove_outliers=False (optional) [Choose between True and False]
    log_transform=None (optional) [Choose between 'yeojohnson'/'added_constant']
    drop_null_dominated=True (optional) [Choose between True and False - Optionally change threshold in dropna_threshold if True]
    dropna_threshold=0.7 (optional) [Proportion check for dropping dull dominated column]
    derive_from_datetime=True (optional) [derive hour, year, month, weekday etc from datetime column - make sure that the dtype is datetime for the column]
    ohe_ignore_cols=[] (optional) [List - if tranform_categorical=one_hot_encoding, ignore columns not to be one hot encoded]
    feature_selection=True (optional) [Choose between True and False - Uses Pearson correlation between two continuous variables, CramersV correlation between two categorical variables, Kendalls Tau correlation between a categorical and a continuos variable]
    define_continuous_cols=[] (optional) [List - Predefine continuous variables]
    define_categorical_cols=[] (optional) [List - Predefine categorical variables]
    |
    |
    returns [Dict - Label Encoded Columns and Values], [DataFrame - Processed Dataset]
    """
    
    col_labels=dict()
    if str.lower(learning_type) not in ['supervised','unsupervised']:
        print('learning_type should be supervised/unsupervised')
        raise exceptions.ParameterError
    if str.lower(tranform_categorical) not in ['label_encoding','one_hot_encoding']:
        print('learning_type should be label_encoding/one_hot_encoding')
        raise exceptions.ParameterError
    if str.lower(learning_type)=='supervised' and target_variable==None:
        print('target_variable is a required parameter for supervised learning')
        raise exceptions.ParameterError
    if str.lower(learning_type)=='supervised' and target_type==None:
        print('target_type (continuous/categorical) is a required parameter for supervised learning')
        raise exceptions.ParameterError
        
    #resetting the index of the dataset
    dataset=dataset.reset_index(drop=True)
    if derive_from_datetime:
        dataset=preprocessing.derive_from_datetime(dataset)
    
    #remove null dominated fields based on threshold if the flag is true
    if drop_null_dominated:
        dataset=preprocessing.drop_null_fields(dataset,dropna_threshold=dropna_threshold)
        
    #drop all single valued columns
    dataset=preprocessing.drop_single_valued_cols(dataset)
    
    #split categorical and continuous variables
    categorical_cols=[]
    continuous_cols=[]
    if str.lower(learning_type)=='supervised':
        for col in dataset:
            if col!=target_variable:
                if helper.check_categorical_col(dataset[col],categorical_threshold=categorical_threshold) and col not in define_continuous_cols:
                    categorical_cols.append(col)
                elif helper.check_numeric_col(dataset[col]) and col not in define_categorical_cols:
                    continuous_cols.append(col)
    else:
        for col in dataset:
            if helper.check_categorical_col(dataset[col],categorical_threshold=categorical_threshold) and col not in define_continuous_cols:
                categorical_cols.append(col)
            elif helper.check_numeric_col(dataset[col]) and col not in define_categorical_cols:
                continuous_cols.append(col)
    for col in define_categorical_cols:
        if col not in categorical_cols:
            categorical_cols.append(col)
    for col in define_continuous_cols:
        if col not in continuous_cols:
            continuous_cols.append(col)
    print('Columns identified as continuous are '+','.join(continuous_cols))        
    print('Columns identified as categorical are '+','.join(categorical_cols))   
    categorical_dataset=dataset[categorical_cols]
    continuous_dataset=dataset[continuous_cols]
    
    # encoding categorical features
    categorical_dataset=preprocessing.impute_nulls(categorical_dataset)
    if str.lower(tranform_categorical)=='label_encoding':
        col_labels,categorical_dataset=preprocessing.get_label_encoded_df(categorical_dataset,categorical_threshold=categorical_threshold)
    elif str.lower(tranform_categorical)=='one_hot_encoding':
        categorical_dataset=preprocessing.get_ohe_df(categorical_dataset,ignore_cols=ohe_ignore_cols,categorical_threshold=categorical_threshold)
        for col in ohe_ignore_cols:
            if helper.check_numeric_col(categorical_dataset[col]):
                pass
            else:
                label_dict,categorical_dataset=preprocessing.label_encode(categorical_dataset,col)
                col_labels[col]=label_dict
    
    # impute nulls in continuous features using choosen method
    continuous_dataset=preprocessing.impute_nulls(continuous_dataset,method=impute_null_method)
    
    # does log transform based on the choosen method if opted
    if log_transform is not None:
        continuous_dataset=preprocessing.log_transform(method=log_transform,categorical_threshold=categorical_threshold)
        
    #merge datasets
    cleansed_dataset=pd.concat([categorical_dataset,continuous_dataset],axis=1)
    if str.lower(learning_type)=='supervised':
        target_df=pd.DataFrame(dataset[target_variable])
        if str.lower(target_type)=='categorical':
            # label encode if target variable is categorical
            label_dict,target_df=preprocessing.label_encode(target_df,target_variable)
            col_labels[target_variable]=label_dict
        mapped_dataset=pd.concat([cleansed_dataset,target_df],axis=1)
        
        #remove outliers if opted
        if remove_outliers:
            mapped_dataset=preprocessing.auto_remove_outliers(mapped_dataset,ignore_cols=[target_variable],categorical_threshold=categorical_threshold)
        
        # does feature selection for supervised learning if opted
        if feature_selection:
            col_corr,correlated_features=preprocessing.get_correlated_features(mapped_dataset,target_variable,target_type)
            final_dataset=mapped_dataset[correlated_features+[target_variable]]
    elif str.lower(learning_type)=='unsupervised':
        
        #remove outliers if opted
        if remove_outliers:
            cleansed_dataset=preprocessing.auto_remove_outliers(cleansed_dataset,categorical_threshold=categorical_threshold)
        final_dataset=cleansed_dataset
    return col_labels,final_dataset


def scale_transform(dataset,
                    method='standard'):
    """
    Usage: [arg1]:[dataframe], [method (default=standard)]:[Choose between standard, mimmax, robust, maxabs]
    Returns: numpy array [to be passed directly to ML model]
    |
    standard: Transorms data by removing mean
    mimmax: Fits values to a range around 0 to 1
    robust: Scaling data with outliers
    maxabs: Handling sparse data
    
    """
    if str.lower(method)=='mimmax':
        scaler=sklearn.preprocessing.MinMaxScaler()
    elif str.lower(method)=='standard':
        scaler=sklearn.preprocessing.StandardScaler()
    elif str.lower(method)=='robust':
        scaler=sklearn.preprocessing.RobustScaler()
    elif str.lower(method)=='maxabs':
        scaler=sklearn.preprocessing.MaxAbsScaler()
    arr_data=scaler.fit_transform(dataset)
    return arr_data


def master_correlation(dataset,
                       categorical_threshold=0.3,
                       define_continuous_cols=[],
                       define_categorical_cols=[]):
    """
    Usage:
    dataset=pandas DataFrame (required)
    categorical_threshold=0.3 (optional) [Threshold for determining categorical column based on the percentage of unique values]
    define_continuous_cols=[] (optional) [List - Predefine continuous variables]
    define_categorical_cols=[] (optional) [List - Predefine categorical variables]
    |
    Description: Auto-detects the type of data. Uses Pearson correlation between two continuous variables, CramersV correlation between two categorical variables, Kendalls Tau correlation between a categorical and a continuos variable
    |
    returns Correlation DataFrame
    
    """
    categorical_cols=[]
    continuous_cols=[]
    for col in dataset:
        if helper.check_categorical_col(dataset[col],categorical_threshold=categorical_threshold):
            categorical_cols.append(col)
        elif helper.check_numeric_col(dataset[col]):
            continuous_cols.append(col)
    
    categorical_dataset=dataset[categorical_cols]
    continuous_dataset=dataset[continuous_cols]
    
    _,categorical_dataset=preprocessing.get_label_encoded_df(dataset[categorical_cols])
    
    data=pd.concat([categorical_dataset,continuous_dataset],axis=1)
    data=preprocessing.drop_single_valued_cols(data)
    data=preprocessing.impute_nulls(data,method='central_tendency')
    
    column_list=data.columns
    
    from itertools import combinations
    
    column_combination=list(combinations(column_list,2))
    
    corr_df=pd.DataFrame(columns=column_list,index=column_list)
    
    for col in column_list:
        corr_df.loc[col,col]=1
    
    for comb in column_combination:
        col1=comb[0]
        col2=comb[1]
        if col1 in continuous_cols and col2 in continuous_cols:
            corr_value=preprocessing.pearson_corr(data[col1],data[col2])
        elif col1 in categorical_cols and col2 in categorical_cols:
            corr_value=preprocessing.cramersv_corr(data[col1],data[col2])
        elif col1 in continuous_cols and col2 in categorical_cols:
            corr_value=preprocessing.kendalltau_corr(data[col1],data[col2])
        elif col1 in categorical_cols and col2 in continuous_cols:
            corr_value=preprocessing.kendalltau_corr(data[col1],data[col2])
        corr_df.loc[col1,col2]=corr_value
        corr_df.loc[col2,col1]=corr_value
    return corr_df