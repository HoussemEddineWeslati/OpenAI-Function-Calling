import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from college_qa.assistant import answer
from college_qa.db import HANDLERS

load_dotenv()
client = OpenAI()

st.title("AtliQ College: Q&A")
question = st.text_input("Ask about a student's marks or fees, or any general question")

if question:
    with st.spinner("Thinking..."):
        st.write(answer(question, client=client, handlers=HANDLERS))
