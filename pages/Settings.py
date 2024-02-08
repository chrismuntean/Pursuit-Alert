import re
import subprocess
import streamlit as st

def list_webcams():
    device_re = re.compile(b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
    df = subprocess.check_output("lsusb", shell=True)
    devices = []
    for i in df.split(b'\n'):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                if b'camera' in dinfo['tag'].lower() or b'webcam' in dinfo['tag'].lower():  # Check for common webcam identifiers
                    dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
                    devices.append(dinfo)
    return devices

def get_webcams():
    webcams = list_webcams()

    for i, webcam in enumerate(webcams):

        # restructrure the webcam list to include the index number as the key to a nested array with the webcam info as the value
        webcams[i] = {i: webcam}
    
    return webcams

# create a streamlit app
st.title('Settings')
st.write('### Select input source:')

# allow the user to select a webcam or video file
cam_or_vid = st.toggle('Upload video instead', value=False)

if cam_or_vid == False:
    webcams = get_webcams()

    # if no webcams are found, display an error message
    if not webcams:
        st.error("No webcams found.")

    else:
        # reorganize the webcam list to be a comma separated string of just the tags
        webcam_tags = [list(webcam.values())[0]['tag'] for webcam in webcams]

        webcam_option = st.selectbox(
            'Select camera stream:',
            webcam_tags
        )

        # get the index of the selected webcam based on the tag
        source = webcam_tags.index(webcam_option)
elif cam_or_vid == True:

    # allow the user to upload a video file
    source = st.file_uploader("Upload a video", type=["mp4", "mov", "avi", "mkv"])

st.write('### Source: ', source)