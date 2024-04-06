import streamlit as st

# check if a variable was passed in the URL query string

# Extract query parameters
# query_params = st.experimental_get_query_params()
plate = st.query_params.get("plate")  # Default to None if not specified

if plate != None:
    st.header(plate)

    # Get the list of times the plate was detected from /logs/perm/all_plates.json
    


else:
    st.write("No plate specified, displaying default dataframe.")
    # Display the default dataframe or any other default information