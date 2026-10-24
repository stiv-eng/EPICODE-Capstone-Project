"""Shared safe choices when source or selected-frame availability changes."""
import streamlit as st


def valid_selectbox(label, options, key, **kwargs):
    options=list(options)
    if not options:
        st.session_state.pop(key,None)
        return None
    if key in st.session_state and st.session_state[key] not in options:
        st.session_state.pop(key,None)
    return st.selectbox(label,options,key=key,**kwargs)


def valid_multiselect(label, options, key, default=None, **kwargs):
    options=list(options)
    if not options:
        st.session_state.pop(key,None)
        return []
    if key in st.session_state:
        st.session_state[key]=[c for c in st.session_state[key] if c in options]
    return st.multiselect(label,options,default=default,key=key,**kwargs)
