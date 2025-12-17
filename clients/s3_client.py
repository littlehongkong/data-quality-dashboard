import boto3
import streamlit as st
from config.settings import AWS_REGION

@st.cache_resource
def get_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)
