import streamlit as st
import requests
import pandas as pd
from pandas.tseries.offsets import DateOffset
from io import BytesIO


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

def calculate_estimated_ttm_ffo(financial_data, selected_date):
    # Find the index of the selected date
    
    selected_index = financial_data[financial_data['date'] == selected_date].index.item()

    # Calculate the FFO for each quarter
    financial_data['FFO'] = financial_data['netIncome'] + \
                            financial_data['depreciationAndAmortization'] + \
                            financial_data['netCashUsedForInvestingActivites']
    
    # Calculate the TTM FFO by summing the FFO of the four quarters trailing the selected date
    ttm_ffo = financial_data['FFO'].iloc[selected_index].sum()

    return ttm_ffo


def calculate_average_percentage_change(financial_data, metric):

    ttm_metrics = financial_data[['netIncome', 'depreciationAndAmortization', 'netCashUsedForInvestingActivites']].rolling(window=4).sum()
    ttm_metrics[['revenue', 'totalAssets']] = financial_data[['revenue', 'totalAssets']]
    # Calculate the TTM metric as a percentage of the chosen metric
    ttm_metrics_percentage = ttm_metrics.div(ttm_metrics[metric], axis=0) * 100
    # Calculate the average percentage
    average_percentage = ttm_metrics_percentage.rolling(window=4).mean()
    return average_percentage

def estimate_next_year_growth(average_percentage_df):

        # Calculate quarter-over-quarter percentage change
    qoq_change = average_percentage_df.pct_change()
    # Calculate the average percentage change for each component
    avg_yoy_change = qoq_change.rolling(window=4).mean()
    return avg_yoy_change

def estimate_next_year_metrics(average_percentage_df,financial_data, avg_yoy_change, allow_input = False):
    # Divide the annual growth rate by 4 to get the estimated quarterly growth rate
    # Check if user input is allowed
    if allow_input:
        quarterly_growth_rate =  avg_yoy_change.iloc[-1] * 100

        # Initialize an empty dictionary to store user inputs
        growth_inputs = {}
        
        # Use Streamlit's number_input to get user input for each metric's growth rate
        for metric in ['netIncome', 'depreciationAndAmortization', 'netCashUsedForInvestingActivites', 'revenue', 'totalAssets']:
           # Set the default value as the last YoY growth rate for the metric
            default_growth_rate = quarterly_growth_rate.get(metric, 0.0)
            
            # Collect user input with the default value set
            user_input = st.sidebar.number_input(
                f'Enter the estimated annual growth rate for {metric} (%)',
                min_value=-100.0,
                value=default_growth_rate,
                step=0.1,
                format='%.2f'
            )
            growth_inputs[metric] = user_input / 100 
        quarterly_growth_rate = pd.Series(growth_inputs) /4 +1
    
    else:
        quarterly_growth_rate = (1 + avg_yoy_change / 4).iloc[-1]


    # Initialize the DataFrame to store the new rows
    new_rows = []
    
    # Get the most recent quarter's data (assuming the last row is the most recent quarter)
    ttm_metrics = financial_data[['netIncome', 'depreciationAndAmortization', 'netCashUsedForInvestingActivites']].rolling(window=4).sum()
    ttm_metrics[['revenue', 'totalAssets']] = financial_data[['revenue', 'totalAssets']]
    # Calculate the TTM metric as a percentage of the chosen metric
    ttm_metrics_percentage = ttm_metrics.div(ttm_metrics[metric], axis=0) * 100
    # Calculate the average percentage
    last_quarter_data = ttm_metrics_percentage

    for i in range(1, 5):

        # Calculate the estimated values for the next quarter
        estimated_values = (quarterly_growth_rate ** i) * last_quarter_data

        # Scale the estimated values
        estimated_values_scaled = estimated_values.iloc[-1] * financial_data.loc[len(financial_data) - 1, "totalAssets"] / 100

        # Create a new DataFrame row with the estimated values
        new_row = estimated_values_scaled.to_frame().transpose()
        # Calculate the new date, adding 3 months for each future quarter
        # Ensure 'date' in financial_data is a datetime object
        financial_data['date'] = pd.to_datetime(financial_data['date'])

        # Now you can add the DateOffset
        new_date = financial_data['date'].iloc[-1] + DateOffset(months=3 * i)



        # Assign the new date to the new_row 'date' column
        new_row['date'] = new_date

        # Append the new row to the list of new_rows
        new_rows.append(new_row)

    # Concatenate the new rows with the original financial_data DataFrame

    updated_financial_data = pd.concat([financial_data] + new_rows, ignore_index=True)
   
    return updated_financial_data


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



# Function to convert the DataFrame to an Excel byte stream
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.save()
    processed_data = output.getvalue()
    return processed_data

# Create a button to download the data




# Initialize the Streamlit app
st.title('REIT Valuation Model')

# User input for the ticker symbol
ticker_symbol = st.text_input('Enter the ticker symbol of the REIT:', '')
allow_input = st.sidebar.checkbox('Allow user input for growth rates', value=False)


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
       

        averages = calculate_average_percentage_change(financial_data, "totalAssets")
        yearly_growth = estimate_next_year_growth(averages)
        updated_financial_data = estimate_next_year_metrics(averages,financial_data, yearly_growth, allow_input)
        
        if st.button('Calculate FFO and Price/FFO'):
            # Calculate the FFO
            ffo = calculate_ttm_ffo(financial_data, selected_date)

            # Calculate Price/FFO ratio
            price_ffo_ratio = selected_market_cap / ffo

            # Display the FFO and Price/FFO ratio
            st.write(f"The FFO for {ticker_symbol} on a TTM basis starting from {selected_date} is: ${ffo:,.2f}")
            st.write(f"The Price/FFO ratio for {ticker_symbol} as of {selected_date} is: {price_ffo_ratio:.2f}")
            
            estimated_ffo = calculate_estimated_ttm_ffo(updated_financial_data, updated_financial_data['date'].iloc[-1])
            st.write(f"The FFO for {ticker_symbol} on a 1 year forward looking basis, using the estimates in the sidebar, starting from {selected_date} is: ${estimated_ffo:,.2f}")
        if st.button('Download Data as Excel'):
            tmp_download_link = to_excel(financial_data)
            st.download_button(label='📥 Download Current Result',
                            data=tmp_download_link,
                            file_name='financial_data.xlsx',
                            mime='application/vnd.ms-excel')
    else:
        st.error('No financial data found for the given ticker symbol.')
else:
    st.error('Please enter a ticker symbol.')

