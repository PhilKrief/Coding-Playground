import streamlit as st
import requests
import pandas as pd
from pandas.tseries.offsets import DateOffset


pd.set_option('display.max_columns', 15)
# Set your Financial Modelling Prep API key here
API_KEY = 'd8eabf9ca1dec61aceefd4b4a9b93992'

def fetch_financial_data(ticker, limit=100):  # Fetch more than four quarters, e.g., 12
    # Define the URLs for the Income Statement and Cash Flow Statement
    income_statement_url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?period=quarter&limit={limit}&apikey={API_KEY}"
    cash_flow_statement_url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?period=quarter&limit={limit}&apikey={API_KEY}"
    balance_sheet_url =  f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?period=quarter&limit={limit}&apikey={API_KEY}"
    # Fetch the data from Financial Modelling Prep
    income_response = requests.get(income_statement_url)
    cash_flow_response = requests.get(cash_flow_statement_url)
    balance_sheet_response = requests.get(balance_sheet_url)

    # Check if the responses are successful
    if income_response.status_code != 200 or cash_flow_response.status_code != 200:
        st.error('Failed to fetch data from Financial Modelling Prep. Please check the ticker and your API key.')
        return None

    # Convert the response data to JSON and reverse the order to get chronological order
    income_data = income_response.json()[::-1]
    cash_flow_data = cash_flow_response.json()[::-1]
    balance_sheet_data = balance_sheet_response.json()[::-1]

    # Create DataFrames from the responses
    income_df = pd.DataFrame(income_data)
    cash_flow_df = pd.DataFrame(cash_flow_data)
    balance_sheet_df = pd.DataFrame(balance_sheet_data)

    # Select non-overlapping columns from cash_flow_df to avoid duplicate 'netIncome' column
    cash_flow_columns = [col for col in cash_flow_df.columns if col not in income_df.columns] + ['date']
    cash_flow_df = cash_flow_df[cash_flow_columns]

    # Merge the DataFrames on the 'date' column
    financial_data = pd.merge(income_df, cash_flow_df, on='date')
    financial_data = pd.merge(financial_data, balance_sheet_df, on='date')
    financial_data.to_excel("reitdata.xlsx")

    return financial_data

def calculate_ttm_ffo(financial_data, selected_date):
    # Find the index of the selected date
    
    selected_index = financial_data[financial_data['date'] == selected_date].index.item()

    # Calculate the FFO for each quarter
    financial_data['FFO'] = financial_data['netIncome'] + \
                            financial_data['depreciationAndAmortization'] + \
                            financial_data['netCashUsedForInvestingActivites']
    
    # Calculate the TTM FFO by summing the FFO of the four quarters trailing the selected date
    ttm_ffo = financial_data['FFO'].iloc[selected_index-3:selected_index+1].sum()

    return ttm_ffo

def calculate_forward_looking_estimate(financial_data, metric, ttm="Yes"):
    if ttm == "Yes":
        ttm_metrics = financial_data[['netIncome', 'depreciationAndAmortization', 'netCashUsedForInvestingActivites']].rolling(window=4).sum()
        ttm_metrics[['revenue', 'totalAssets']] = financial_data[['revenue', 'totalAssets']]
        # Calculate the TTM metric as a percentage of the chosen metric
        ttm_metrics_percentage = ttm_metrics.div(ttm_metrics[metric], axis=0) * 100
        # Calculate the average percentage
        average_percentage = ttm_metrics_percentage.rolling(window=4).mean()
        print("test")
    else:
        ttm_metrics = financial_data[['netIncome', 'depreciationAndAmortization', 'netCashUsedForInvestingActivites']]
        ttm_metrics[['revenue', 'totalAssets']] = financial_data[['revenue', 'totalAssets']]
        # Calculate the TTM metric as a percentage of the chosen metric
        ttm_metrics_percentage = ttm_metrics.div(ttm_metrics[metric], axis=0) * 100
        # Calculate the average percentage
        average_percentage = ttm_metrics_percentage
        print("test")

    #print(ttm_metrics)
    #print(ttm_metrics_percentage)
    #print(average_percentage)

    return average_percentage

def estimate_next_quarter_ffo(average_percentage_df,financial_data, ttm="Yes"):
    if ttm == "Yes":
        # Calculate quarter-over-quarter percentage change
        qoq_change = average_percentage_df.pct_change()
        #print(qoq_change)

        # Calculate the average percentage change for each component
        avg_qoq_change = qoq_change.rolling(window=4).mean()

        # Get the most recent quarter's data (assuming the last row is the most recent quarter)
        last_quarter_data = average_percentage_df.iloc[-1]

        # Calculate the estimated values for the next quarter by applying the average percentage change
        
        estimated_next_quarter = (1 + avg_qoq_change.iloc[-1]) * last_quarter_data
        print(estimated_next_quarter)
        estimated_values_scaled =estimated_next_quarter*financial_data.loc[len(financial_data)-1, "totalAssets"] / 100
    else:
        # Calculate quarter-over-quarter percentage change
        qoq_change = average_percentage_df.pct_change(4)
        #print(qoq_change)

        # Calculate the average percentage change for each component
        avg_qoq_change = qoq_change

        # Get the most recent quarter's data (assuming the last row is the most recent quarter)
        last_quarter_data = average_percentage_df.iloc[-1]

        # Calculate the estimated values for the next quarter by applying the average percentage change
        
        estimated_next_quarter = (1 + avg_qoq_change.iloc[-1]) * last_quarter_data
        
        estimated_values_scaled =estimated_next_quarter*financial_data.loc[len(financial_data)-1, "totalAssets"] / 100

    # Create a new DataFrame with the estimated values for the next quarter
    new_row = pd.DataFrame([estimated_values_scaled], columns=average_percentage_df.columns)

    financial_data['date'] = pd.to_datetime(financial_data['date'])
    
    # Get the last date from the 'date' column
    last_date = financial_data['date'].iloc[-1]
    
    # Add 3 months to the last date
    new_date = last_date + DateOffset(months=3)

    # Assign the new date to the new_row 'date' column
    new_row['date'] = new_date


    # Append the new_row to the financial_data DataFrame
    updated_financial_data = financial_data.append(new_row, ignore_index=True)

    print(updated_financial_data[['date','netIncome','depreciationAndAmortization','netCashUsedForInvestingActivites']])
  
    return  updated_financial_data

def fetch_daily_market_cap_dataframe(api_key, symbol):
    url = f"https://financialmodelingprep.com/api/v3/historical-market-capitalization/{symbol}?limit=6000&apikey={api_key}"
    response = requests.get(url)
    
    if response.status_code != 200:
        st.error(f"Error fetching market cap data for {symbol}: {response.status_code}")
        return None

    data = response.json()
    market_cap_df = pd.DataFrame(data)
    market_cap_df = market_cap_df[['date', 'marketCap']]
    market_cap_df['date'] = pd.to_datetime(market_cap_df['date'])
    return market_cap_df
# Initialize the Streamlit app
st.title('REIT Valuation Model')

# User input for the ticker symbol
ticker_symbol = st.text_input('Enter the ticker symbol of the REIT:', '')

if ticker_symbol:
    # Fetch the financial data for the given ticker symbol
    financial_data = fetch_financial_data(ticker_symbol)
    market_cap_data = fetch_daily_market_cap_dataframe(API_KEY, ticker_symbol)


    if financial_data is not None and market_cap_data is not None:
        # Let the user select a date
        date_options = financial_data['date'].unique()
        #flip the order of the dates
        date_options = date_options[::-1]
        selected_date = st.selectbox('Select the date for TTM FFO calculation:', options=date_options[:(len(date_options)-50)])

        # Match the market cap to the selected date, or use the most recent if the selected date is the most recent
        if selected_date == date_options[0]:  # Assuming the first option is the most recent
            selected_market_cap = market_cap_data['marketCap'].iloc[0]
        else:
            # Find the market cap closest to the selected date
            market_cap_data['date_diff'] = (pd.to_datetime(selected_date) - market_cap_data['date']).abs()
            selected_market_cap = market_cap_data.loc[market_cap_data['date_diff'].idxmin(), 'marketCap']
       

        if st.button('Calculate FFO and Price/FFO'):
            # Calculate the FFO
            ffo = calculate_ttm_ffo(financial_data, selected_date)

            # Calculate Price/FFO ratio
            price_ffo_ratio = selected_market_cap / ffo

            # Display the FFO and Price/FFO ratio
            st.write(f"The FFO for {ticker_symbol} on a TTM basis starting from {selected_date} is: ${ffo:,.2f}")
            st.write(f"The Price/FFO ratio for {ticker_symbol} as of {selected_date} is: {price_ffo_ratio:.2f}")
            averages = calculate_forward_looking_estimate(financial_data, "totalAssets")
            updated_financial_data = estimate_next_quarter_ffo(averages,financial_data)
            
            
            estimated_ffo = calculate_ttm_ffo(updated_financial_data, updated_financial_data['date'].iloc[-1])
            st.write(estimated_ffo)
    else:
        st.error('No financial data found for the given ticker symbol.')
else:
    st.error('Please enter a ticker symbol.')




def estimate_next_year_metrics(average_percentage_df,financial_data, avg_yoy_change):
    # Divide the annual growth rate by 4 to get the estimated quarterly growth rate
    quarterly_growth_rate = (1 + avg_yoy_change / 4)

    # Initialize the DataFrame to store the new rows
    new_rows = []
    
    # Get the most recent quarter's data (assuming the last row is the most recent quarter)
    last_quarter_data = average_percentage_df.iloc[-1]

    # Calculate the estimated values for the next quarter by applying the average percentage change
    
    estimated_next_quarter = (1 + avg_yoy_change.iloc[-1]) * last_quarter_data
 
    estimated_values_scaled =estimated_next_quarter*financial_data.loc[len(financial_data)-1, "totalAssets"] / 100
    
    # Create a new DataFrame with the estimated values for the next quarter
    new_row = pd.DataFrame([estimated_values_scaled], columns=average_percentage_df.columns)

    financial_data['date'] = pd.to_datetime(financial_data['date'])
    
    # Get the last date from the 'date' column
    last_date = financial_data['date'].iloc[-1]
    
    # Add 3 months to the last date
    new_date = last_date + DateOffset(months=3)

    # Assign the new date to the new_row 'date' column
    new_row['date'] = new_date


    # Append the new_row to the financial_data DataFrame
    updated_financial_data = financial_data.append(new_row, ignore_index=True)


    return  updated_financial_data
