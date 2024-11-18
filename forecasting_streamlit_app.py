import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime as dt
import gspread

@st.cache_data
def supply_calculation(supply_df, demand_df):
     compare = demand_df.merge(supply_df, how='left', on='unique_id')
     compare['Quantity to Meet Demand'] = np.ceil(compare[forecast_column] - compare['On Hand'])
     compare['Quantity to Meet Demand'] = np.where(compare['Quantity to Meet Demand']<0,0,compare['Quantity to Meet Demand'])
     return compare

@st.cache_data
def read_from_gsheet_to_df(filename):
     #st.toast(f'Loading {filename} data...')
     creds = dict(st.secrets["gcp"]['read_gsheet_credentials'])
     gc = gspread.service_account_from_dict(creds)
     sh = gc.open(filename)
     df = pd.DataFrame(sh.sheet1.get_all_records())
     df.replace(r'^\s*$', np.nan, regex=True, inplace=True)
     if 'ds' in df.columns:
          df['ds']  = pd.to_datetime(df['ds']).dt.date
     else:
          pass
     
     #st.toast(f"{filename} data loaded!")
     return df 

def write_to_gsheet(filename, data):
     creds = dict(st.secrets["gcp"]['write_gsheet_credentials'])
     gc = gspread.service_account_from_dict(creds)
     sh = gc.open(filename)
     sh.sheet1.append_row(data, table_range="A1:D1")

st.title("Demand and Supply Planning App")
mkdwn = '''Welcome to the Demand and Supply Planning App, an educational project by Ben Wyndham.

The purpose of this app is to provide automatic, high-quality, hierarchical demand forecasting and supply planning via a simple interface. This app is purely educational, and assumptions or notes are listed throughout the app. 

The forecasts are driven by an ML and Statistical forecaster that selects the best model for each time series, based on crossvalidation performance across 10, 6 week folds. This forecaster uses a wide selection of models such as LightGBM, Croston, HoltWinters, and ETS. Code can be found on [github](https://github.com/bwyndham/demand_supply_planning_app/blob/main/ml-forecaster.ipynb).

This app uses the Nixtla, LightGBM, Streamlit, Pandas, Gspread and Plotly Python libraries.  

If you have any feedback or suggestions, please let me know via the feedback form or my [website](https://benjaminwyndham.com/).'''
st.markdown(mkdwn)
tab1, tab2, tab3 = st.tabs(['Demand Planning','Supply Planning','Feedback'])
# hardcoded, need to refactor to get user input and save in this format
categorial_columns = ["state_id","store_id","cat_id","dept_id"]
item_column = 'item_id'
cat_item_columns = ["state_id","store_id","cat_id","dept_id","item_id"]
forecast_column = 'forecast'
historic_column = 'y'
date_column = ['ds']

df = read_from_gsheet_to_df("forecasted_values")


ttl_df = read_from_gsheet_to_df("combined_sales_fcast")
#ttl_df['ds']  = pd.to_datetime(ttl_df['ds']).dt.date
ttl_df.sort_values(by=date_column, inplace=True)

# get historical data
hist_df = ttl_df[ttl_df['forecast'].isna()]

# get error metrics
error_df = read_from_gsheet_to_df("hierarchical_evaluations_summary")
best_models = read_from_gsheet_to_df("forecast_model_breakout")
     
with tab1:
     start_date = st.date_input("Start Date of Historical Data", dt.datetime(2015,10,1))
     groups = ttl_df[categorial_columns].columns.to_list()
     group_choices = []
     group_choice = st.selectbox('Select Group By',groups)
     group_choices.append(group_choice)
     
     choices = {}
     ncol = len(ttl_df[categorial_columns].columns)
     cols = st.columns(ncol)
     for i, x in enumerate(cols):
          key = str(ttl_df[categorial_columns].columns[i])
          choice = x.multiselect(f'Select {ttl_df[categorial_columns].columns[i]}', ttl_df[ttl_df[categorial_columns].columns[i]].drop_duplicates(),key=i)
          if key in choices:
               choices[key].append(choice)
          else:
               choices[key] = choice

     ind = [True] * len(ttl_df)
     choices_not_null = {k: v for k, v in choices.items() if v}
     for col, vals in choices_not_null.items():
          ind = ind & (ttl_df[col].isin(vals))
     
     time_groupby = group_choices + date_column
     
     col1, col2 = st.columns(2)
     with col1:
          ttl_fcast = ttl_df[ind][forecast_column].sum()
          st.metric(label="Forecasted Total Units", value="{:,.0f} units".format(ttl_fcast))
          
          try:
               # historical line chart
               fig = px.line(ttl_df[ind & (ttl_df['ds'] > start_date) & (~ttl_df[historic_column].isna())].groupby(by=time_groupby).agg({historic_column:'sum'}).reset_index(),
                         x=date_column, y=historic_column, color=group_choice, title='Historical Sales',range_y=[0,150000])
               st.plotly_chart(fig, key='historic_series')
          except Exception as e:
               st.exception(e)
               
     with col2:
          ttl_error = error_df[error_df['level'] == 'Overall']['forecast'].values[0]
          error_metric = error_df[error_df['level'] == 'Overall']['metric'].values[0]
          st.metric(label=f"Forecast Average Error ({error_metric})",value = "{:,.0f} units".format(ttl_error))
          
          try:
          # forecast line chart
               fig = px.line(ttl_df[ind & (~ttl_df[forecast_column].isna())].groupby(by=time_groupby).agg({forecast_column:'sum'}).reset_index(),
                        x=date_column, y=forecast_column, color=group_choice, title='Forecasted Demand',range_y=[0,150000])
               st.plotly_chart(fig, key='forecast_test')
          except Exception as e:
               st.exception(e)
          
     
     st.info("Filter to a department and select up to 10 Items Below to view their forecasts.")
     depts = ttl_df['dept_id'].drop_duplicates()
     dept_choice = st.selectbox('Select Dept_Id',depts)
          
     item_df = pd.pivot_table(ttl_df[~ttl_df[forecast_column].isna() & (ttl_df['dept_id'] == dept_choice)], values=forecast_column,
                              index=cat_item_columns, columns=date_column, aggfunc='sum', fill_value=0)
     
     item_df['series'] = item_df.iloc[:,-6:].values.tolist()
     column_configuration = {'series': st.column_config.LineChartColumn("Forecast")}
     event = st.dataframe(item_df,use_container_width=True,hide_index=False,on_select='rerun',selection_mode='multi-row',column_config=column_configuration)
     selections = event.selection.rows
     filtered_df = item_df.iloc[selections].reset_index().melt(id_vars=cat_item_columns)
     fig = px.line(filtered_df,x='ds', y='value', color='item_id')
     st.plotly_chart(fig, key='filtered_items_series')
     
     st.info("Breakout of Forecasts and Quantity by Forecasting Model")
     st.warning("There are clear opportunities within the forecaster to improve results. With the right data and parameters, many of these algorithms can and should beat benchmarks like Naive and Average models.")
     st.dataframe(best_models)
     
     forecasts_csv = df.to_csv()
     st.download_button(label="Download Forecasts to CSV",
                        data=forecasts_csv,
                        file_name="forecasts.csv",
                        mime="text/csv")

with tab2:
     oh_df= read_from_gsheet_to_df("on_hand_supply_planning")
     demand_df = df.groupby(by='unique_id').sum(forecast_column).reset_index()
     compare = supply_calculation(oh_df, demand_df)
     hist_start = hist_df['ds'].max() - dt.timedelta(weeks=4)
     st.warning("For simplicity, 0 week lead time is assumed. In practice that is rarely, if ever, the case.")
     
     groups = ttl_df[categorial_columns].columns.to_list()
     group_choices = []
     group_choice = st.selectbox('Select Group By',groups, key="groups_supply")
     group_choices.append(group_choice)
     
     choices = {}
     ncol = len(ttl_df[categorial_columns].columns)
     cols = st.columns(ncol)
     for i, x in enumerate(cols):
          key = str(ttl_df[categorial_columns].columns[i])
          choice = x.multiselect(f'Select {ttl_df[categorial_columns].columns[i]}', ttl_df[ttl_df[categorial_columns].columns[i]].drop_duplicates(),key=f"{i}_supply")
          if key in choices:
               choices[key].append(choice)
          else:
               choices[key] = choice


     hist_ind = [True] * len(hist_df)
     choices_not_null = {k: v for k, v in choices.items() if v}
     for col, vals in choices_not_null.items():
          hist_ind = hist_ind & (hist_df[col].isin(vals))
          
     compare_ind = [True] * len(compare)
     choices_not_null = {k: v for k, v in choices.items() if v}
     for col, vals in choices_not_null.items():
          compare_ind = compare_ind & (compare[col].isin(vals))
     
     avg_sales_4wk = (hist_df[hist_ind & (hist_df['ds'] >= hist_start)]['y'].sum())/4
     curr_oh = compare[compare_ind]['On Hand'].sum()
     woc = curr_oh / avg_sales_4wk
     fcast_sales_4wk = (compare[compare_ind][forecast_column].sum()/4)
     fwos = curr_oh / fcast_sales_4wk
     ttl_buy = compare[compare_ind]['Quantity to Meet Demand'].sum()
     col1, col2, col3 = st.columns(3)
     with col1:
          st.metric(label="Quantity to Meet Forecasted Demand", value="{:,.0f} qty".format(ttl_buy))
     with col2:
          st.metric(label="Weeks of Cover (L4W)", value="{:,.0f} weeks".format(woc))
     with col3:
          st.metric(label="Weeks of Supply (Forecasted Next 4)", value="{:,.0f} weeks".format(fwos))
     
     fig = px.bar(compare[compare_ind].groupby(by=group_choice).agg({'Quantity to Meet Demand':'sum'}).reset_index(),x=group_choice,y='Quantity to Meet Demand')
     st.plotly_chart(fig, key='agg_buys')
     
     st.dataframe(compare[compare_ind])
     supply_df = compare.to_csv()
     st.download_button(label="Download Supply Recommendations to CSV",
                        data=supply_df,
                        file_name="supply_recommendations.csv",
                        mime="text/csv")

with tab3:
     with st.form("feedback_form"):
          st.write("What do you think about this app?")
          star_rating = st.feedback("stars")
          interest = st.radio("Are you interested in learning more?",["Yes","No"])
          email = st.text_input("Email")
          feedback = st.text_area("Any specific feedback?")
          submitted = st.form_submit_button("Submit Feedback")
     if submitted:
          form_list = [star_rating, interest, email, feedback]
          write_to_gsheet("forecasting_app_feedback", form_list)
     