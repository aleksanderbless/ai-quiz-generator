import os

import openai
import pypdf
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")  # Put your key in a .env file

st.title("PDF to Multiple-Choice Quiz Generator")

uploaded_file = st.file_uploader("Upload an old exam PDF", type="pdf")
num_questions = st.number_input(
    "Number of questions", min_value=1, max_value=50, value=10
)

if uploaded_file and st.button("Generate Quiz"):
    # Extract text from PDF
    reader = pypdf.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    if not text.strip():
        st.error("No text extracted. Try a text-based PDF or add OCR.")
    else:
        st.info(f"Extracted {len(text)} characters. Generating quiz...")

        prompt = f"""
        From the following text, generate exactly {num_questions} multiple-choice questions.
        Each question should have:
        - The question
        - 4 options (A, B, C, D)
        - The correct answer (e.g., "B")
        - A brief explanation

        Text: {text[:10000]}  # Limit to avoid token overflow; chunk if needed

        Output as JSON: [{{"question": "...", "options": ["A: ...", "B: ...", ...], "correct": "B", "explanation": "..."}}, ...]
        """

        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Cheap and good; use gpt-4o for better quality
            messages=[
                {"role": "system", "content": "You are a quiz generator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        try:
            import json

            quiz = json.loads(response.choices[0].message.content)
            st.success("Quiz generated!")

            for i, q in enumerate(quiz, 1):
                st.subheader(f"Question {i}: {q['question']}")
                for opt in q["options"]:
                    st.write(opt)
                with st.expander("Show answer & explanation"):
                    st.write(f"Correct: {q['correct']}")
                    st.write(q["explanation"])
        except:
            st.error("Error parsing response. Raw output:")
            st.write(response.choices[0].message.content)
