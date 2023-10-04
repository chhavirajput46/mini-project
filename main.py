import streamlit as st
import streamlit_authenticator as stauth
from dependancies import sign_up, fetch_users
import io
from pathlib import Path
import select
from shutil import rmtree
import subprocess as sp
import sys
from typing import Dict, Tuple, Optional,IO
import os

st.set_page_config(page_title='Streamlit', page_icon='🐍', initial_sidebar_state='collapsed')

model = "htdemucs"
extensions = ["mp3", "wav", "ogg", "flac"] 
two_stems = None 
mp3 = True
mp3_rate = 320
float32 = False 
int24 = False   
out_folder = 'output/htdemucs'
if not os.path.exists(out_folder):
    os.makedirs(out_folder)


def find_files(in_path):
    st.info(inp_path)
    out = []
    for file in Path(in_path).iterdir():
        if file.suffix.lower().lstrip(".") in extensions:
            out.append(file)
    return out



def copy_process_streams(process: sp.Popen):
    def raw(stream: Optional[IO[bytes]]) -> IO[bytes]:
        assert stream is not None
        if isinstance(stream, io.BufferedIOBase):
            stream = stream.raw
        return stream

    p_stdout, p_stderr = raw(process.stdout), raw(process.stderr)
    stream_by_fd: Dict[int, Tuple[IO[bytes], io.StringIO, IO[str]]] = {
        p_stdout.fileno(): (p_stdout, sys.stdout),
        p_stderr.fileno(): (p_stderr, sys.stderr),
    }
    fds = list(stream_by_fd.keys())

    while fds:
        ready, _, _ = select.select(fds, [], [])
        for fd in ready:
            p_stream, std = stream_by_fd[fd]
            raw_buf = p_stream.read(2 ** 16)
            if not raw_buf:
                fds.remove(fd)
                continue
            buf = raw_buf.decode()
            std.write(buf)
            std.flush()

def separate(inp=None, outp='output'):

    cmd = ["python", "-m", "demucs.separate", "-o", str(outp), "-n", model]
    if mp3:
        cmd += ["--mp3", f"--mp3-bitrate={mp3_rate}"]
    if float32:
        cmd += ["--float32"]
    if int24:
        cmd += ["--int24"]
    if two_stems is not None:
        cmd += [f"--two-stems={two_stems}"]
    files = [f'{f}' for f in find_files(inp)]
    if not files:
        st.info(f"No valid audio files in {inp}")
        return
    st.info("Going to separate the files")
    st.markdown(f'''
                #### executing command
                `{" ".join(cmd+files)}`
                ''')
    try:
        p = sp.Popen(cmd + files, stdout=sp.PIPE, stderr=sp.PIPE, shell=True, text=True)
        for line in p.stdout:
            # Display each line in the Streamlit app
            st.warning(line.strip())
        p.wait()
        # Optionally, display stderr as well
        for line in p.stderr:
            st.warning(line.strip())
        if p.returncode != 0:
            st.error("Command failed, something went wrong.")
        else:
            st.success("Command executed")
    except Exception as e:
        st.error(f"Error occured during working {e}")
def save(audio):
    folder = os.path.join('uploads', audio.name.split('.')[0].replace(' ','_').lower())
    if os.path.exists(folder):
        st.error(f"file already exists, taking '{folder}' as input ")
    else:    
        os.makedirs(folder)
        with open(os.path.join(folder, audio.name.replace(' ','').lower()), 'wb') as f:
            f.write(audio.getvalue())
        st.success("file uploaded")
    return folder

menu=["Login","Sign Up"]
choice=st.sidebar.selectbox("Menu",menu)
if choice=="Login":
    try:
        users = fetch_users()
        emails = []
        usernames = []
        passwords = []

        def forget_password():
            password1 = st.text_input(':blue[Password]', placeholder='Enter Your Password', type='password')
            password2 = st.text_input(':blue[Confirm Password]', placeholder='Confirm Your Password', type='password')


        for user in users:
            emails.append(user['key'])
            usernames.append(user['username'])
            passwords.append(user['password'])

        credentials = {'usernames': {}}
        for index in range(len(emails)):
            credentials['usernames'][usernames[index]] = {'name': emails[index], 'password': passwords[index]}

        Authenticator = stauth.Authenticate(credentials, cookie_name='Streamlit', key='abcdef', cookie_expiry_days=4)

        email, authentication_status, username = Authenticator.login(':green[Login]', 'main')

        info, info1 = st.columns(2)

        #if not authentication_status:
            #b=st.button("sign up")
            #sign()
            

        if username:
            if username in usernames:
                if authentication_status:
                    # let User see app
                    st.sidebar.subheader(f'Welcome {username}')
                    Authenticator.logout('Log Out', 'sidebar')
                    st.title('*Musically')
                    menu=["Home","About"]
                    choice=st.sidebar.selectbox("Menu",menu)
                    if choice=="Home":
                        st.subheader("Home")
                        audio=st.file_uploader("upload audio file",type=[])
                        st.audio(audio)
                        
                        if st.button("Seperate"):
                            with st.spinner("processing"):
                                inp_path = save(audio)
                                separate(inp_path)
                                st.balloons()
                                st.success("Task compeleted successfully")
                        st.header("Generated Files")
                        folders = os.listdir(out_folder)
                        selected = st.selectbox("select a music file", folders)
                        for file in os.listdir(os.path.join(out_folder, selected)):
                            st.subheader(file)
                            st.audio(f'{os.path.join(out_folder,selected,file)}')
                

                    elif choice=="About":
                        st.subheader("About")
                        st.write('''This free application will help you seaprate drums, bass, and vocals from the rest of the accompaniment.

                    Once you choose a song, it will separate the vocals from the instrumental ones. You will get four tracks - a karaoke version of your song (no vocals), acapella version (isolated vocals), drum and bass.
                    ''')
                    

                elif not authentication_status:
                    with info:
                        st.error('Incorrect Password or username')
                else:
                    with info:
                        st.warning('Please feed in your credentials')
            else:
                with info:
                    st.warning('Username does not exist, Please Sign up')
                    


    except:
        st.success('Refresh Page')
if choice=="Sign Up":
    sign_up()
