import re
import subprocess
import streamlit as st
import pandas as pd

# Initialize session state variables if not already set
if 'cam_or_vid' not in st.session_state:
    st.session_state['cam_or_vid'] = False # Default to Webcam (False)

if 'cam_index' not in st.session_state:
    st.session_state['cam_index'] = None

if 'file_path' not in st.session_state:
    st.session_state['file_path'] = None


def list_webcams():
    # use the lsusb command to list all usb devices
    device_re = re.compile(b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
    df = subprocess.check_output("lsusb", shell=True)

    # create an empty list to store the webcams
    devices = []

    # iterate through the list of usb devices and check for common webcam identifiers
    for i in df.split(b'\n'):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                if b'camera' in dinfo['tag'].lower() or b'webcam' in dinfo['tag'].lower():  # Check for common webcam identifiers
                    dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
                    devices.append(dinfo)

    # reverse the list of devices
    devices.reverse()

    # restructure the list to incude the index as the key
    for i, device in enumerate(devices):
        devices[i] = {i: device}

    return devices

# create a streamlit app
st.header('General Settings', divider = 'gray')
st.write('### Select input source:')

# allow the user to select a webcam or video file and update the session state
cam_or_vid = st.toggle('Upload video instead', value=st.session_state['cam_or_vid'])
st.session_state['cam_or_vid'] = cam_or_vid

st.divider()

# if the user selected webcam, display webcam selector and clear the file path
if cam_or_vid == False:
    st.session_state['file_path'] = None

    # get the list of webcams
    webcams = list_webcams()
    
    st.write('##### Connected webcams:')

    # if no webcams are found, display an error message
    if not webcams:
        st.error("No webcams found.\nPlease connect a camera and refresh the page.")

    # if webcams are found, display the list of webcams in a dropdown
    else:
        # reorganize the webcam list to be a comma separated string of just the tags
        webcam_tags = [list(webcam.values())[0]['tag'] for webcam in webcams]

        # display the list of webcams as h3
        for tag in enumerate(webcam_tags):
            st.text(tag[1])

    webcam_option = st.selectbox(
        '##### Select stream index:',
        options = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        index = st.session_state['cam_index']
    )

    # set the session states for the tag and index
    st.session_state['cam_index'] = webcam_option

    st.divider()

# if the user selected video, display the file uploader and clear the webcam index
elif cam_or_vid == True:
    st.session_state['cam_index'] = None

    st.session_state['cam_or_vid'] = True
    uploaded_file = st.file_uploader("Upload a video", type=["mp4", "mov", "avi", "mkv"], 
                                     accept_multiple_files=False)
    if uploaded_file is not None:
        st.session_state['file_path'] = uploaded_file

# write the session state variables to the sidebar (navbar) for development
st.sidebar.write('### Session state variables')
st.sidebar.write(st.session_state)