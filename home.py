from pathlib import Path
import streamlit as st
from ui import style

@st.cache_data
def home_html(source):
    # Embed local font faces. Animation never receives user input or credentials.
    # Only font declarations are shared; the poster scene owns its colors/layout.
    css=style().split('    html,body,')[0]
    return source.replace('</head>',css+'</style></head>')



def neuron_home():
    st.iframe(home_html((Path(__file__).parent/'assets'/'neuron.html').read_text()),height=580,alt='세로로 분절된 기억 조각이 뉴런 신호와 함께 연결되는 메멘토 홈')
