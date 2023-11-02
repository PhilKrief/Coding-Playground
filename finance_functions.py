import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
pd.set_option('display.max_columns', 500)

#Basic Calculations


def allocation_df_prep(allocation, df, returns):
    selected_row = df.loc[allocation]
    allocation_df = pd.DataFrame( columns= selected_row.index, index= returns.Période)
    allocation_df.loc[:,:] = selected_row.values
    return allocation_df

def performance_table_2(years,rendement_mandat, rendement_bench, rendements_indices, mandat):
    columns = ["Fonds", "Date de début", "Date de fin", "Rendement brut (période)", "Rendement indice (période)",
               "Rendement brut (annualisée)", "Rendement indice (annualisée)", "Valeur ajoutée (période)", "Valeur ajoutée annualisée",
               "Risque actif annualisé", "Ratio information", "Beta", "Alpha annualisé", "Ratio sharpe", "Coefficient de corrélation",
               "Volatilité annualisée du fonds", "Volatilité annualisée de l'indice"]

    perf_df = pd.DataFrame(columns).rename(columns={0:"Index"})

    time = 12 * years
    inputs = rendement_mandat.reset_index()
    try:
        inputs = inputs.rename(columns={"date":"Période"})
    except:
        inputs = inputs

    inputs["Période"] = pd.to_datetime(inputs["Période"])
    date_end = inputs.loc[len(inputs)-1, "Période"]
    
    date_start = inputs.loc[len(inputs)-time, "Période"]

    df_final = pd.DataFrame()

    rendement_mandat = rendement_mandat.add_suffix('_bruts')
    rendement_bench = rendement_bench.add_suffix('_indices')
 
    df_final["Période"] = inputs["Période"]
    rendements_indices = rendements_indices.reset_index()
    df_final["Marché monétaire"] = rendements_indices["Marché monétaire"]

    df_final.set_index('Période', inplace=True)

    df_final[rendement_mandat.columns] = rendement_mandat[rendement_mandat.columns]
    df_final[rendement_bench.columns] = rendement_bench[rendement_bench.columns]
    df_final.reset_index(inplace=True)

    df_filtered = df_final[(df_final["Période"] <= date_end) & (df_final["Période"] >= date_start)]
    print(df_filtered)
    df_filtered[mandat+"_bruts_retours"] = df_filtered[mandat+"_bruts"] +1

    df_filtered[mandat+"_indices_retours"] = df_filtered[mandat+"_indices"]+1
    df_filtered["va"] = df_filtered[mandat+"_bruts"] - df_filtered[mandat+"_indices"]

    rendements_indices_periode = df_filtered[mandat+"_indices_retours"].prod()-1
    rendements_bruts_periode = df_filtered[mandat+"_bruts_retours"].prod()-1
    valeur_ajoute = rendements_bruts_periode - rendements_indices_periode

    rendements_annualisé_brut = (1+rendements_bruts_periode)**(1/(len(df_filtered)/12))-1
    rendements_annualisé_indice = (1+rendements_indices_periode)**(1/(len(df_filtered)/12))-1
    valeur_ajoute_annual = rendements_annualisé_brut - rendements_annualisé_indice
    risque_actif_annual = df_filtered["va"].std()*(12**(1/2))
    information_ratio = valeur_ajoute_annual/risque_actif_annual
    beta = (df_filtered[mandat+"_bruts"].astype(float).cov(df_filtered[mandat+"_indices"].astype(float)))/df_filtered[mandat+"_indices"].astype(float).var()

    df_filtered["Marché monétaire_retours"] = df_filtered["Marché monétaire"]+1
    risk_free = (df_filtered["Marché monétaire_retours"].prod()-1)
    risk_free_annual = (1+risk_free)**(1/(len(df_filtered)/12))-1
    alpha = rendements_annualisé_brut - beta*(rendements_annualisé_indice-risk_free_annual)-risk_free_annual
    stand_dev_fund = df_filtered[mandat+"_bruts"].std()*(12**(.5))
    stand_dev_index = df_filtered[mandat+"_indices"].std()*(12**(.5))
    sharpe = (rendements_annualisé_brut-risk_free_annual)/stand_dev_fund
    coeff_corr = df_filtered[mandat+"_bruts"].astype(float).corr(df_filtered[mandat+"_indices"].astype(float))
    dict_dum = {"Fonds":mandat, "Date de début":date_start, "Date de fin": date_end, "Rendement brut (période)":rendements_bruts_periode,
                "Rendement indice (période)":rendements_indices_periode, "Valeur ajoutée (période)":valeur_ajoute, "Rendement brut ("
                                                                                                           "annualisée)":rendements_annualisé_brut,
                "Rendement indice (annualisée)":rendements_annualisé_indice, "Valeur ajoutée annualisée":valeur_ajoute_annual, "Risque actif "
                                                                                                                               "annualisé":
                    risque_actif_annual,"Ratio information":information_ratio, "Beta":beta, "Alpha annualisé":alpha, "Ratio sharpe":sharpe,
                "Coefficient de corrélation":coeff_corr, "Volatilité annualisée du fonds": stand_dev_fund, "Volatilité annualisée de l'indice":stand_dev_index}
    perf_df[mandat] = perf_df["Index"].map(dict_dum)
    return perf_df

def financial_metric_table(years, rendement_mandat, rendement_bench, indices_df, mandat):
    data = pd.DataFrame()

    for time in years:
        financial_metrics = performance_table_2(time,rendement_mandat, rendement_bench, indices_df, mandat).add_suffix('_%d'%time)
        data["Index"] = financial_metrics["Index_%d"%time]
        data = pd.merge(data, financial_metrics,  left_on="Index", right_on="Index_%d"%time, how="left")


    spike_cols = ["Index"] + [col for col in data.columns if mandat in col]
    data = data[spike_cols]

    return data




def allocation_df(allocations, portfolio_returns):
    allocation_df = pd.DataFrame(columns=portfolio_returns.columns, index=portfolio_returns.index)
    allocations = allocations.set_index("Ticker")
    allocations = allocations.astype(float)/100
    for ticker in allocation_df.columns:
        allocation_df[ticker] = allocations.loc[ticker, "Allocation"]

    return allocation_df

def calculate_portfolio_returns(allocations, returns):
    mask = returns.isna()
    allocations[mask] = np.nan
    row_sum = allocations.apply(lambda row: row.sum(skipna=True), axis=1)
    norm_aloc = allocations.div(row_sum, axis=0)
    portfolio_returns = (returns * norm_aloc).sum(axis=1)

    return portfolio_returns

def get_daily_stock_portfolio_prices(portfolio, key):
    # Define the start and end dates (10 years ago from today)
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=3653)).strftime('%Y-%m-%d')

    dfs = []
    for stock in portfolio:
        dum = get_daily_stock_prices(stock, key)
        dum = dum[['date', 'close']]
        dum.columns = ['date', stock]
        dum.set_index('date', inplace=True)
        dfs.append(dum)

    merged_df = pd.concat(dfs, axis=1)
    return merged_df

def get_monthly_stock_portfolio_prices(portfolio, key):
    # Define the start and end dates (10 years ago from today)
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=3653)).strftime('%Y-%m-%d')

    dfs = []
    for stock in portfolio:
        dum = get_monthly_stock_prices(stock, key)
        dum = dum[['date', 'close']]
        dum.columns = ['date', stock]
        dum.set_index('date', inplace=True)
        dfs.append(dum)

    merged_df = pd.concat(dfs, axis=1)
    return merged_df



def calculate_returns(df):
    """
    Calculates the daily returns of each stock in a merged dataframe of historical prices.
    
    Args:
    df (pandas.DataFrame): A merged dataframe of historical prices for multiple stocks.
    
    Returns:
    pandas.DataFrame: A dataframe of daily returns for each stock in the input dataframe.
    """
    # Calculate the daily returns for each stock
    try:
        df = df.set_index("date")
    except:
        df = df

    returns_df = df.iloc[:, :].pct_change(-1)
    
    # Replace the first row of NaNs with 0s
    #returns_df.iloc[0, :] = 0

    returns_df.dropna(inplace=True)
    
    return returns_df

##### Financial Modelling Prep Functions
def get_monthly_stock_prices(stock, key):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=3653)).strftime('%Y-%m-%d')

    """
    gets stock prices on a monthly basis from FMP

    Args:
        stock (str): Ticker
        start_date (datetime): start date
        end_date (datetime): end date

    Returns:
        _type_: _description_
    """
    url = f'https://financialmodelingprep.com/api/v3/historical-price-full/{stock}?from={start_date}&to={end_date}&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data['historical'])
    df["date"] = pd.to_datetime(df["date"])
    # Group by year and month, then select the maximum date within each group
    # Resample the dataframe to get the last day of each month
    # Set the "date" column as the index
    df.set_index("date", inplace=True)
    df_last_day = df.resample("M").last()

    # Reset the index
    df_last_day = df_last_day.reset_index()
    df_last_day = df_last_day[::-1]
    return df_last_day


def get_daily_stock_prices(stock, key):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=3653)).strftime('%Y-%m-%d')

    """gets stock prices on a daily basis from FMP

    Args:
        stock (str): Ticker
        start_date (datetime): start date
        end_date (datetime): end date

    Returns:
        _type_: _description_
    """
    url = f'https://financialmodelingprep.com/api/v3/historical-price-full/{stock}?from={start_date}&to={end_date}&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data['historical'])
    return df

def key_metrics(stock, key):
    """gets stock key metrics like PE and roe

    Args:
        stock (str): Ticker
    Returns:
        _type_: _description_
    """
    url = f'https://financialmodelingprep.com/api/v3/key-metrics/{stock}?period=annual&limit=130&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)
    df = df[['date', 'period', 'revenuePerShare', 'netIncomePerShare',
       'operatingCashFlowPerShare', 'freeCashFlowPerShare', 'cashPerShare',
       'bookValuePerShare', 'peRatio', 'priceToSalesRatio', 
       'pfcfRatio', 'freeCashFlowYield', 'debtToEquity', 'debtToAssets']]
    
    df[['revenuePerShare', 'netIncomePerShare',
       'operatingCashFlowPerShare', 'freeCashFlowPerShare', 'cashPerShare',
       'bookValuePerShare', 'peRatio', 'priceToSalesRatio', 
       'pfcfRatio', 'freeCashFlowYield', 'debtToEquity', 'debtToAssets']] = df[['revenuePerShare', 'netIncomePerShare',
       'operatingCashFlowPerShare', 'freeCashFlowPerShare', 'cashPerShare',
       'bookValuePerShare', 'peRatio', 'priceToSalesRatio', 
       'pfcfRatio', 'freeCashFlowYield', 'debtToEquity', 'debtToAssets']].round(2)
    
    df.rename(columns={'date':'Date', 'period':'Period', 'revenuePerShare':"Revenue Per Share", 'netIncomePerShare':"Net Income Per Share",
       'operatingCashFlowPerShare':"Operating Cash Flow Per Share", 'freeCashFlowPerShare': "FCF Per Share", 'cashPerShare':"Cash Per Share",
       'bookValuePerShare': "Book Value Per Share", 'peRatio': "P/E Ratio", 'priceToSalesRatio': "P/S Ratio", 
       'pfcfRatio': "P/FCF Ratio", 'freeCashFlowYield': "FCF Yield", 'debtToEquity': "Debt-to-Equity", 'debtToAssets': "Debt-to-Assets"}, inplace=True)
    df = df.loc[0,]
    df.T
    return df

def key_metrics_ttm(stock, key):
    """gets stock key metrics like PE and roe

    Args:
        stock (str): Ticker
    Returns:
        _type_: _description_
    """
    url = f'https://financialmodelingprep.com/api/v3/key-metrics-ttm/{stock}?period=annual&limit=130&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)
    df = df[['revenuePerShareTTM', 'netIncomePerShareTTM',
       'operatingCashFlowPerShareTTM', 'freeCashFlowPerShareTTM', 'cashPerShareTTM',
       'bookValuePerShareTTM', 'peRatioTTM', 'priceToSalesRatioTTM', 
       'pfcfRatioTTM', 'freeCashFlowYieldTTM', 'debtToEquityTTM', 'debtToAssetsTTM']]
    
    df[['revenuePerShareTTM', 'netIncomePerShareTTM',
       'operatingCashFlowPerShareTTM', 'freeCashFlowPerShareTTM', 'cashPerShareTTM',
       'bookValuePerShareTTM', 'peRatioTTM', 'priceToSalesRatioTTM', 
       'pfcfRatioTTM', 'freeCashFlowYieldTTM', 'debtToEquityTTM', 'debtToAssetsTTM']] = df[['revenuePerShareTTM', 'netIncomePerShareTTM',
       'operatingCashFlowPerShareTTM', 'freeCashFlowPerShareTTM', 'cashPerShareTTM',
       'bookValuePerShareTTM', 'peRatioTTM', 'priceToSalesRatioTTM', 
       'pfcfRatioTTM', 'freeCashFlowYieldTTM', 'debtToEquityTTM', 'debtToAssetsTTM']].round(2)
    
    df.rename(columns={'revenuePerShareTTM':"Revenue Per Share", 'netIncomePerShareTTM':"Net Income Per Share",
       'operatingCashFlowPerShareTTM':"Operating Cash Flow Per Share", 'freeCashFlowPerShareTTM': "FCF Per Share", 'cashPerShareTTM':"Cash Per Share",
       'bookValuePerShareTTM': "Book Value Per Share", 'peRatioTTM': "P/E Ratio", 'priceToSalesRatioTTM': "P/S Ratio", 
       'pfcfRatioTTM': "P/FCF Ratio", 'freeCashFlowYieldTTM': "FCF Yield", 'debtToEquityTTM': "Debt-to-Equity", 'debtToAssetsTTM': "Debt-to-Assets"}, inplace=True)
    df = df.loc[0,]
    df.T
    return df


def company_profile(stock, key):
    """gets company profile

    Args:
        stock (str): Ticker

    Returns:
        _type_: _description_
    """
    url = f'https://financialmodelingprep.com/api/v3/profile/{stock}?apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)
    df = df[['companyName', 'symbol', 'price', 'mktCap', 'exchangeShortName', 'sector', 'industry', 'ceo']]
    df.rename(columns={'companyName': 'Company Name', 'symbol':'Symbol', 'price':'Price', 'mktCap':"Market Cap", 'exchangeShortName':"Exchange Name", 'sector':'Sector', 'industry':'Industry', 'ceo':'CEO'}, inplace=True)
    df = df.T
    return df

def key_executives(stock, key):
    """gets key executives

    Args:
        stock (str): Ticker

    Returns:
        _type_: _description_
    """
    url = f'https://financialmodelingprep.com/api/v3/key-executives/{stock}?apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)
    return df

def format_percentage(numb):
    percentage = numb * 100
    formatted_percentage = "{:.2f}%".format(percentage)
    return formatted_percentage

##### Financial Modelling Prep Functions
def get_list_of_stocks(key):    
    """gets list of stocks from FMP

    Args:
        stock (str): Ticker

    Returns:
        _type_: _description_
    """
    url = f'https://financialmodelingprep.com/api/v3/stock/list?apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)
    return df   

def get_news_general(key):
    """gets stock news on a daily basis from FMP

    Args:
        stock (str): Ticker
        start_date (datetime): start date
        end_date (datetime): end date

    Returns:
        _type_: _description_
    """
    url = f'https://financialmodelingprep.com/api/v4/general_news?page=0&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)
    return df

def get_news_stocks(key):
    """gets stock news on a daily basis from FMP

    Args:
        stock (str): Ticker
        start_date (datetime): start date
        end_date (datetime): end date

    Returns:
        _type_: _description_
    """
    
    url = f'https://financialmodelingprep.com/api/v3/stock_news?limit=100&&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)
    return df

def get_news_stocks_specific(ticker, key):
    """gets stock news on a daily basis from FMP

    Args:
        stock (str): Ticker
        start_date (datetime): start date
        end_date (datetime): end date

    Returns:
        _type_: _description_
    """
    ""
    url = f'https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}&limit=50&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)
    return df

#earnings calls
def get_earnings_calls(ticker,quarter,year ,key):

    url = f'https://financialmodelingprep.com/api/v3/earning_call_transcript/{ticker}?quarter={quarter}&year={year}&apikey={key}'
    response = requests.get(url)
    data = response.json()[0]
    df = pd.DataFrame(data)
    return df

#financial
def get_quarterly_income_statement(ticker, key):
    "https://financialmodelingprep.com/api/v3/income-statement/AAPL?period=quarter&limit=400&apikey=d8eabf9ca1dec61aceefd4b4a9b93992"
    url = f'https://financialmodelingprep.com/api/v3/income-statement/{ticker}?period=quarter&limit=8&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)
 
    # Identify integer columns
    integer_columns = df.select_dtypes(include='integer').columns
    # Convert integer columns to floats
    df[integer_columns] = df[integer_columns].astype(float)
 
    #df = df.T
    #df.columns = df.loc['date']
    return df

def get_annual_income_statement(ticker, key):
    url = f'https://financialmodelingprep.com/api/v3/income-statement/{ticker}?limit=10&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data).T
    df.columns = df.loc['date']
    return df

def get_quarterly_balance_statement(ticker, key):
    "https://financialmodelingprep.com/api/v3/balance-sheet-statement/AAPL?period=quarter&limit=400&apikey=d8eabf9ca1dec61aceefd4b4a9b93992"
    url = f'https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?period=quarter&limit=8&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data).T
    df.columns = df.loc['date']
    return df

def get_annual_balance_statement(ticker, key):
    "https://financialmodelingprep.com/api/v3/income-statement/AAPL?period=quarter&limit=400&apikey=d8eabf9ca1dec61aceefd4b4a9b93992"
    url = f'https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?limit=8&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data).T
    df.columns = df.loc['date']
    return df

def get_quarterly_cashflow_statement(ticker, key):
    "https://financialmodelingprep.com/api/v3/income-statement/AAPL?period=quarter&limit=400&apikey=d8eabf9ca1dec61aceefd4b4a9b93992"
    url = f'https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?period=quarter&limit=8&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data).T
    df.columns = df.loc['date']
    return df

def get_annual_cashflow_statement(ticker, key):
    "https://financialmodelingprep.com/api/v3/income-statement/AAPL?period=quarter&limit=400&apikey=d8eabf9ca1dec61aceefd4b4a9b93992"
    url = f'https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?limit=8&apikey={key}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data).T
    df.columns = df.loc['date']
    return df


key = "d8eabf9ca1dec61aceefd4b4a9b93992"

