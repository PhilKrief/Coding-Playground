import streamlit as st
import requests
import pandas as pd

pd.set_option('display.max_columns', 15)
# Set your Financial Modelling Prep API key here
API_KEY = 'd8eabf9ca1dec61aceefd4b4a9b93992'

def fetch_financial_data(ticker, limit=12):  # Fetch more than four quarters, e.g., 12
    # Define the URLs for the Income Statement and Cash Flow Statement
    income_statement_url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?period=quarter&limit={limit}&apikey={API_KEY}"
    cash_flow_statement_url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?period=quarter&limit={limit}&apikey={API_KEY}"

    # Fetch the data from Financial Modelling Prep
    income_response = requests.get(income_statement_url)
    cash_flow_response = requests.get(cash_flow_statement_url)

    # Check if the responses are successful
    if income_response.status_code != 200 or cash_flow_response.status_code != 200:
        st.error('Failed to fetch data from Financial Modelling Prep. Please check the ticker and your API key.')
        return None

    # Convert the response data to JSON and reverse the order to get chronological order
    income_data = income_response.json()[::-1]
    cash_flow_data = cash_flow_response.json()[::-1]

    # Create DataFrames from the responses
    income_df = pd.DataFrame(income_data)
    cash_flow_df = pd.DataFrame(cash_flow_data)

    # Select non-overlapping columns from cash_flow_df to avoid duplicate 'netIncome' column
    cash_flow_columns = [col for col in cash_flow_df.columns if col not in income_df.columns] + ['date']
    cash_flow_df = cash_flow_df[cash_flow_columns]

    # Merge the DataFrames on the 'date' column
    financial_data = pd.merge(income_df, cash_flow_df, on='date')
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
    print(financial_data[['date', 'FFO', 'netIncome', 'depreciationAndAmortization', 'netCashUsedForInvestingActivites']])
    print(financial_data['FFO'].iloc[selected_index-3:selected_index+1])
    return ttm_ffo

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
        selected_date = st.selectbox('Select the date for TTM FFO calculation:', options=date_options)

        # Match the market cap to the selected date, or use the most recent if the selected date is the most recent
        if selected_date == date_options[len(date_options)-1]:  # Assuming the first option is the most recent
            selected_market_cap = market_cap_data['marketCap'].iloc[0]
        else:
            # Find the market cap closest to the selected date
            market_cap_data['date_diff'] = (pd.to_datetime(selected_date) - market_cap_data['date']).abs()
            selected_market_cap = market_cap_data.loc[market_cap_data['date_diff'].idxmin(), 'marketCap']
            print(selected_market_cap)

        if st.button('Calculate FFO and Price/FFO'):
            # Calculate the FFO
            ffo = calculate_ttm_ffo(financial_data, selected_date)

            # Calculate Price/FFO ratio
            price_ffo_ratio = selected_market_cap / ffo

            # Display the FFO and Price/FFO ratio
            st.write(f"The FFO for {ticker_symbol} on a TTM basis starting from {selected_date} is: ${ffo:,.2f}")
            st.write(f"The Price/FFO ratio for {ticker_symbol} as of {selected_date} is: {price_ffo_ratio:.2f}")
    else:
        st.error('No financial data found for the given ticker symbol.')
else:
    st.error('Please enter a ticker symbol.')