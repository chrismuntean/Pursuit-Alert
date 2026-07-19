import re
import subprocess
import streamlit as st
import tempfile
import cv2

# Initialize session state variables if not already set
if 'source_type' not in st.session_state:
    st.session_state['source_type'] = "USB Camera"

if 'cam_index' not in st.session_state:
    st.session_state['cam_index'] = 0

if 'file_path' not in st.session_state:
    st.session_state['file_path'] = None

if 'rtsp_url' not in st.session_state:
    st.session_state['rtsp_url'] = ""

if 'frame_skip' not in st.session_state:
    st.session_state['frame_skip'] = 10


def list_webcams():
    """Return a list of USB cameras visible inside the Linux container."""
    device_re = re.compile(
        rb"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$",
        re.I,
    )

    try:
        result = subprocess.run(
            ["lsusb"],
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    devices = []

    for line in result.stdout.splitlines():
        info = device_re.match(line)
        if not info:
            continue

        dinfo = info.groupdict()
        tag = dinfo["tag"].lower()

        if b"camera" in tag or b"webcam" in tag:
            dinfo["device"] = b"/dev/bus/usb/%s/%s" % (
                dinfo.pop("bus"),
                dinfo.pop("device"),
            )
            devices.append(dinfo)

    devices.reverse()
    return devices


def classify_resolution(width, height):
    if height >= 2160 or width >= 3840:
        return "4K"
    if height >= 1080 or width >= 1920:
        return "1080p"
    if height >= 720 or width >= 1280:
        return "720p"
    if height >= 480 or width >= 640:
        return "480p"
    return "Low Resolution"


def inspect_stream(stream_path):
    """Open a stream briefly and return whether it works plus basic properties."""
    cap = cv2.VideoCapture(stream_path)

    if not cap.isOpened():
        cap.release()
        return False, 0, 0, 0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_rate = int(cap.get(cv2.CAP_PROP_FPS))

    # Some RTSP streams report 0 FPS even though they work.
    if frame_rate <= 0:
        frame_rate = 25

    cap.release()
    return True, width, height, frame_rate


st.header("General Settings", divider="gray")
st.write("### Select input source:")

source_type = st.radio(
    "Source type",
    options=["USB Camera", "Video File", "RTSP Camera"],
    index=["USB Camera", "Video File", "RTSP Camera"].index(
        st.session_state["source_type"]
    ),
    horizontal=True,
)

st.session_state["source_type"] = source_type
st.divider()

stream_ready = False
stream_fps = 0
stream_width = 0
stream_height = 0

if source_type == "USB Camera":
    st.session_state["file_path"] = None
    st.session_state["rtsp_url"] = ""

    webcams = list_webcams()
    st.write("##### Connected webcams:")

    if not webcams:
        st.warning(
            "No USB webcams were detected inside the container. "
            "This is expected on macOS unless camera passthrough is configured."
        )
    else:
        for webcam in webcams:
            st.code(webcam["tag"].decode(errors="replace"))

    webcam_option = st.selectbox(
        "Select stream index",
        options=list(range(10)),
        index=int(st.session_state["cam_index"]),
    )
    st.session_state["cam_index"] = webcam_option

    if st.button("Test USB camera"):
        stream_ready, stream_width, stream_height, stream_fps = inspect_stream(
            webcam_option
        )
        if stream_ready:
            st.success("USB camera connected successfully")
        else:
            st.error("That webcam index is not available.")

elif source_type == "Video File":
    st.session_state["cam_index"] = None
    st.session_state["rtsp_url"] = ""

    uploaded_file = st.file_uploader(
        "Upload a video",
        type=["mp4", "mov", "avi", "mkv"],
        accept_multiple_files=False,
    )

    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(uploaded_file.read())
            st.session_state["file_path"] = tmp_file.name

    if st.session_state["file_path"]:
        stream_ready, stream_width, stream_height, stream_fps = inspect_stream(
            st.session_state["file_path"]
        )
        if stream_ready:
            st.success("Video file connected successfully")
        else:
            st.error("That video file could not be opened.")
    else:
        st.info("Upload a video file to continue.")

elif source_type == "RTSP Camera":
    st.session_state["cam_index"] = None
    st.session_state["file_path"] = None

    st.write("##### RTSP stream address")
    rtsp_url = st.text_input(
        "RTSP URL",
        value=st.session_state["rtsp_url"],
        placeholder=(
            "rtsp://username:password@camera-ip:554/"
            "h264Preview_01_main"
        ),
        type="password",
        help=(
            "For a Reolink main stream, use "
            "rtsp://username:password@CAMERA_IP:554/h264Preview_01_main"
        ),
    )
    st.session_state["rtsp_url"] = rtsp_url.strip()

    show_url = st.checkbox("Show RTSP address")
    if show_url and st.session_state["rtsp_url"]:
        st.code(st.session_state["rtsp_url"])

    if st.button("Test RTSP connection", type="primary"):
        if not st.session_state["rtsp_url"]:
            st.error("Enter an RTSP address first.")
        else:
            with st.spinner("Connecting to RTSP stream..."):
                (
                    stream_ready,
                    stream_width,
                    stream_height,
                    stream_fps,
                ) = inspect_stream(st.session_state["rtsp_url"])

            if stream_ready:
                st.session_state["rtsp_test_ok"] = True
                st.session_state["rtsp_fps"] = stream_fps
                st.session_state["rtsp_width"] = stream_width
                st.session_state["rtsp_height"] = stream_height
                st.success("RTSP camera connected successfully")
            else:
                st.session_state["rtsp_test_ok"] = False
                st.error(
                    "Could not open the RTSP stream. Check the address, "
                    "credentials, RTSP setting, and camera network access."
                )

    if st.session_state.get("rtsp_test_ok"):
        stream_ready = True
        stream_fps = int(st.session_state.get("rtsp_fps", 25))
        stream_width = int(st.session_state.get("rtsp_width", 0))
        stream_height = int(st.session_state.get("rtsp_height", 0))


st.divider()
st.write("### Set the frame skip:")

if stream_ready:
    resolution = classify_resolution(stream_width, stream_height)
    st.code(f"Input FPS: {stream_fps}")
    st.code(
        f"Input resolution: {resolution} "
        f"({stream_width}x{stream_height})"
    )

    max_skip = max(1, stream_fps - 1)
    default_skip = min(
        max(0, int(st.session_state.get("frame_skip", 10))),
        max_skip,
    )

    frame_skip = st.slider(
        "Select frame skip",
        min_value=0,
        max_value=max_skip,
        value=default_skip,
    )
    st.session_state["frame_skip"] = frame_skip
else:
    st.info(
        "Connect or test an input source before setting the frame skip."
    )

st.sidebar.write("### Session state variables")
st.sidebar.write(st.session_state)
