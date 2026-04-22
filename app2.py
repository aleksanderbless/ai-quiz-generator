import json
import os

import pypdf
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Gets api keys from .env file
openai_key = os.getenv("OPENAI_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

st.title("📄 PDF to Multiple-Choice Quiz Generator")
st.markdown(
    "Upload an old exam PDF and generate MCQs using either OpenAI or Google Gemini."
)

# Select model/provider
provider = st.radio(
    "Choose AI Provider", options=["OpenAI (GPT)", "Google Gemini"], horizontal=True
)

# Key in env?
if provider == "OpenAI (GPT)" and not openai_key:
    st.error("⚠️ OPENAI_API_KEY not found in .env file.")
    st.stop()
elif provider == "Google Gemini" and not gemini_key:
    st.error("⚠️ GEMINI_API_KEY not found in .env file.")
    st.stop()

uploaded_file = st.file_uploader("Upload Exam PDF", type="pdf")
num_questions = st.slider("Number of questions", min_value=1, max_value=50, value=10)
difficulty = st.select_slider(
    "Difficulty level", options=["Easy", "Medium", "Hard"], value="Medium"
)

if uploaded_file and st.button("Generate Quiz"):
    with st.spinner("Extracting text from PDF..."):
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        if not text.strip():
            st.error(
                "No text could be extracted. Try a searchable PDF or add OCR later."
            )
            st.stop()

        st.success(
            f"Extracted {len(text):,} characters from {len(reader.pages)} pages."
        )

    with st.spinner(f"Generating {num_questions} questions using {provider}..."):
        prompt = f"""
        You are an expert exam question creator. Generate exactly {num_questions} high-quality multiple-choice questions
        from the following text at {difficulty.lower()} difficulty level.

        Each question must have:
        - A clear question
        - Exactly 4 options labeled A, B, C, D
        - One correct answer
        - A brief explanation

        Output ONLY valid JSON in this format (no extra text):
        [
          {{
            "question": "Question text here",
            "options": ["A: Option one", "B: Option two", "C: Option three", "D: Option four"],
            "correct": "B",
            "explanation": "Brief explanation here"
          }}
        ]

        Text:
        {text[:15000]}  # Truncated to avoid token limits
        """
        try:
            if provider == "OpenAI (GPT)":
                client = OpenAI(api_key=openai_key)

                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # Fast & cheap; change to "gpt-4o" for better quality
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a precise quiz generator. Output only valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    max_tokens=4000,
                )
                raw_output = response.choices[0].message.content.strip()

            else:  # Google Gemini
                client = OpenAI(
                    api_key=gemini_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                )

                response = client.chat.completions.create(
                    model="gemini-2.5-flash",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a precise quiz generator. Output only valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    # Set max tokens to limit usage, too low limit can lead to json
                    # parsing error.
                    # max_tokens=4000,
                )
                raw_output = response.choices[0].message.content.strip()

                # Gemini sometimes wraps in ```json ... ``` — clean it
                if raw_output.startswith("```json"):
                    raw_output = raw_output[7:]
                if raw_output.endswith("```"):
                    raw_output = raw_output[:-3]
                raw_output = raw_output.strip()

            # Parse JSON
            quiz = json.loads(raw_output)

            st.success(f"Quiz generated with {provider}! 🎉")

            for i, q in enumerate(quiz, 1):
                st.subheader(f"Question {i}: {q.get('question', 'N/A')}")

                # Display options with radio for fun (optional)
                for opt in q.get("options", []):
                    st.write(opt)

                with st.expander("Show answer & explanation"):
                    correct = q.get("correct", "?")
                    explanation = q.get("explanation", "No explanation provided.")
                    st.markdown(f"**Correct Answer: {correct}**")
                    st.write(explanation)

        except json.JSONDecodeError:
            st.error("Failed to parse quiz (invalid JSON). Raw output:")
            st.code(raw_output)
        except Exception as e:
            st.error(f"Error: {str(e)}")
            if "raw_output" in locals():
                st.code(raw_output)
