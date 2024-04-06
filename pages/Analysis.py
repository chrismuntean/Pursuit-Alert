import os
import json
import streamlit as st

# Check if a variable was passed in the URL query string
plate = st.query_params.get("plate")

if plate != None:
    st.header(plate, divider = 'gray')

    # Get the list of times the plate was detected from /logs/perm/all_plates.json
    
    # check if the all_plates.json file exists
    if os.path.exists("logs/perm/all_plates.json"):

        # get the all_plates.json file
        with open("logs/perm/all_plates.json", "r") as file:
            all_plates = json.load(file)

        # check if the plate is in the all_plates.json file
        if plate in all_plates:

            # reverse the list so that the latest detection is shown first
            all_plates[plate].reverse()

            for plate in all_plates[plate]:
                
                # for each time the plate was detected create an expander with the date and time
                with st.expander(plate["date"] + " at " + plate["time"]):
                    
                    # create 2 columns for the video and images
                    vid_col, image_col = st.columns([3, 1])

                    # load video bytes
                    vid_file = open('logs' + plate["video_path"], 'rb')
                    vid_bytes = vid_file.read()

                    # display the video
                    vid_col.video(vid_bytes)

                    # display the images vertically
                    image_col.image('logs' + plate["veh_crop_path"], use_column_width=True)
                    image_col.image('logs' + plate["plate_crop_path"], use_column_width=True)

        else:
            st.error("Plate number not found in logs.")


else:
    st.write("No plate specified, displaying default dataframe.")
    # Display the default dataframe or any other default information