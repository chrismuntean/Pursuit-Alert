import re
import subprocess
import streamlit as st
import tempfile
import cv2

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
    df = subprocess.check_output("lsusb", shell = True)
    
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

def classify_resolution(width, height):
    if height >= 2160 or width >= 3840:
        return "4K"
    elif height >= 1080 or width >= 1920:
        return "1080p"
    elif height >= 720 or width >= 1280:
        return "720p"
    elif height >= 480 or width >= 640:
        return "480p"
    else:
        return "Low Resolution"

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
        st.error("No webcams found.Please connect a camera and refresh the page.")

    # if webcams are found, display the list of webcams in a dropdown
    else:
        # reorganize the webcam list to be a comma separated string of just the tags
        webcam_tags = [list(webcam.values())[0]['tag'] for webcam in webcams]

        # display the list of webcams as h3
        for tag in enumerate(webcam_tags):
            st.code(tag[1])

    st.write('#') # SPACER

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
    uploaded_file = st.file_uploader("#### Upload a video", type=["mp4", "mov", "avi", "mkv"], 
                                     accept_multiple_files = False)
    
    # set the session state
    if uploaded_file is not None:

        # Use tempfile.NamedTemporaryFile to create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:

            # Write the data from the uploaded file into the temporary file
            tmp_file.write(uploaded_file.read())
            
            # Store the path of the temporary file in session_state
            st.session_state['file_path'] = tmp_file.name

    st.divider()

st.write('### Set the frame skip:')

# if the user selected a webcam
if st.session_state['cam_or_vid'] == False:
    
    # check if the webcam index is set
    if st.session_state['cam_index'] is not None:

        #_# GET WEBCAM PROPERTIES #_#
        #############################

        # try opening the webcam
        cap = cv2.VideoCapture(st.session_state['cam_index'])

        # if the cap is not opened, display an error message
        if not cap.isOpened():
            st.error('That webcam index is not available. Please select another index.')

        elif cap.isOpened():
            st.success('Webcam connected successfully')

            # get the frame rate
            frame_rate = int(cap.get(cv2.CAP_PROP_FPS))

            # get the resolution from the width and height
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # classify the resolution
            resolution = classify_resolution(width, height)

            st.code(f'Input FPS: {frame_rate}')
            st.code(f'Input resolution: {resolution}')

            st.write('#') # SPACER

            # display the slider
            frame_skip = st.slider('#### Select frame skip:', min_value = 0, max_value = frame_rate, value = 10)

            # set the session state for the frame rate
            st.session_state['frame_skip'] = frame_skip

            # release the webcam
            cap.release()

    else:
        st.error('Please select an index')

# if the user selected a video file
elif st.session_state['cam_or_vid'] == True:

    # check if the file path is set
    if st.session_state['file_path'] is not None:

        #_# GET VIDEO PROPERTIES #_#

        # try opening the video file
        # if the video file is not found, display an error message
        cap = cv2.VideoCapture(st.session_state['file_path'])

        if not cap.isOpened():
            st.error('That video file is not available. Please select another file.')

        elif cap.isOpened():
            st.success('Video file connected successfully')

            # get the frame rate
            frame_rate = int(cap.get(cv2.CAP_PROP_FPS))

            # get the resolution from the width and height
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # classify the resolution
            resolution = classify_resolution(width, height)

            st.code(f'Input FPS: {frame_rate}')
            st.code(f'Input resolution: {resolution}')            

            st.write('#') # SPACER

            # display the slider
            frame_rate = st.slider('#### Select frame skip:', min_value = 0, max_value = frame_rate, value=10)

            # set the session state for the frame rate
            st.session_state['frame_skip'] = frame_rate

            # release the video file
            cap.release()

    else:
        st.error('Please upload a video file')


# write the session state variables to the sidebar (navbar) for development
st.sidebar.write('### Session state variables') # FOR DEVELOPMENT ONLY
st.sidebar.write(st.session_state) # FOR DEVELOPMENT ONLY