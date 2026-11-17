import streamlit as st
import streamlit.components.v1 as components
import asyncio
import json
import os
import time
from datetime import datetime
from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from utils.llm_call import LLM_MODEL
from utils import (
    transcribe_with_speechmatics,
    extract_resume_info_using_llm,
    get_ai_greeting_message,
    get_final_thanks_message,
    analyze_candidate_response_and_generate_new_question,
    get_feedback_of_candidate_response,
    get_overall_evaluation_score,
    save_interview_data,
    load_content_streamlit,
)

MAX_QUESTIONS = 5


def missing_llm_api_key():
    """Return the required API key name for a supported provider if it is unset."""
    provider = LLM_MODEL.split("/", 1)[0].lower()
    key_name = {
        "gemini": "GEMINI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }.get(provider)
    return key_name if key_name and not os.getenv(key_name) else None


def valid_candidate_name(name):
    """Reject empty names and placeholders returned by the resume parser."""
    return bool(
        name
        and name.strip().casefold() not in {"", "not provided", "unknown", "n/a", "none"}
    )


# Configuration and Styling
def setup_page_config():
    """Setup page configuration and custom CSS"""
    st.set_page_config(page_title="AI Interview App", layout="wide")

    st.markdown(
        """
    <style>
    .audio-section {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
        text-align: center;
        border: 2px solid #e9ecef;
    }
    .interview-progress {
        background-color: #e8f5e8;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        text-align: center;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        "interview_started": False,
        "name": "",
        "resume_highlights": "",
        "job_description": "",
        "qa_index": 1,
        "conversations": [],
        "current_question": "",
        "question_spoken": False,
        "awaiting_response": False,
        "processing_audio": False,
        "messages": [],
        "interview_completed": False,
        "max_questions": MAX_QUESTIONS,
        "ai_voice": "Alex (Male)",
        "thanks_message_prepared": False,
        "thanks_message_spoken": False,
        "thanks_message_auto_played": False,
        "show_final_results": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_ai_voice_details():
    """Get AI voice configuration"""
    return {
        "Alex (Male)": {"name": "Alex", "code": "en-US-GuyNeural"},
        "Aria (Female)": {"name": "Aria", "code": "en-US-AriaNeural"},
        "Natasha (Female)": {"name": "Natasha", "code": "en-IN-NeerjaNeural"},
        "Sonia (Female)": {"name": "Sonia", "code": "en-GB-SoniaNeural"},
    }

def get_instructions():
    """Get instructions for the user"""
    content = """
    #### Please follow these steps to use the AI Interview App:
    1. **Upload Resume**: Upload your resume in PDF format.
    2. **Job Description**: Paste the job description.
    3. **Start Interview**: Click the "Start Interview" button to begin the AI-driven interview.
    4. **Maximum Questions**: You can set the maximum number of questions for the interview. (default: 5)
    5. **Voice Selection**: Choose the AI voice for the interview.(default: Alex (Male))
    6. **Answer Questions**: Answer the questions posed by the AI interviewer.
    7. **Review Results**: After the interview, review your performance and feedback.

    **Note**: The AI interviewer will ask you questions based on your resume and the job description.

    I hope you find the experience helpful!
    """
    return st.markdown(content)

def render_sidebar():
    """Render sidebar with candidate information and settings"""
    st.sidebar.title("Candidate Information")

    # File upload
    uploaded_resume = st.sidebar.file_uploader("Upload your Resume (PDF)", type=["pdf"])
    candidate_name = st.sidebar.text_input(
        "Candidate name (optional)",
        help="Enter your name if the resume parser cannot identify it.",
    )

    # Job description
    job_description = st.sidebar.text_area("Paste the Job Description")

    # Settings
    max_questions = st.sidebar.number_input(
        "Maximum number of questions",
        min_value=1,
        max_value=10,
        value=MAX_QUESTIONS,
    )
    st.session_state["max_questions"] = max_questions

    ai_voice = st.sidebar.radio(
        "Select AI Interviewer Voice",
        ["Alex (Male)", "Aria (Female)", "Natasha (Female)", "Sonia (Female)"],
    )
    st.session_state["ai_voice"] = ai_voice

    submit = st.sidebar.button("Submit")

    return uploaded_resume, candidate_name, job_description, submit


def process_resume_submission(uploaded_resume, job_description, candidate_name=""):
    """Process resume and job description submission"""
    with st.spinner("Processing resume..."):
        resume_content = load_content_streamlit(uploaded_resume)
        if not resume_content or not resume_content.strip():
            st.error(
                "No readable text was found in this PDF. Upload a text-based resume "
                "or run OCR on a scanned PDF before submitting."
            )
            return
        extracted_name, resume_highlights = extract_resume_info_using_llm(resume_content)

    name = candidate_name.strip() or extracted_name
    if not valid_candidate_name(name):
        st.error(
            "Could not identify your name. Enter it in 'Candidate name (optional)' "
            "and submit again."
        )
        return

    # Store in session state
    st.session_state["name"] = name
    st.session_state["resume_highlights"] = resume_highlights
    st.session_state["job_description"] = job_description

    # Reset interview state
    reset_interview_state()

    st.success(f"Candidate Name: {name}")


def reset_interview_state():
    """Reset interview-related session state"""
    interview_keys = [
        "interview_started",
        "qa_index",
        "conversations",
        "current_question",
        "question_spoken",
        "awaiting_response",
        "processing_audio",
        "messages",
        "interview_completed",
        "thanks_message_prepared",
        "thanks_message_spoken",
        "thanks_message_auto_played",
        "show_final_results",
    ]

    for key in interview_keys:
        if key == "interview_started" or key == "interview_completed":
            st.session_state[key] = False
        elif key in ["qa_index"]:
            st.session_state[key] = 1
        elif key in ["conversations", "messages"]:
            st.session_state[key] = []
        elif key in ["current_question"]:
            st.session_state[key] = ""
        else:
            st.session_state[key] = False


def start_interview():
    """Initialize and start the interview"""
    st.session_state["interview_started"] = True
    reset_interview_state()
    st.session_state["interview_started"] = True  # Reset above sets this to False

    # Get greeting message
    ai_voice_details = get_ai_voice_details()
    interviewer_name = ai_voice_details[st.session_state["ai_voice"]]["name"]
    greeting_message = get_ai_greeting_message(
        st.session_state["name"], interviewer_name=interviewer_name
    )

    st.session_state["current_question"] = greeting_message
    st.session_state["messages"].append(
        {"role": "assistant", "content": greeting_message}
    )


def display_chat_messages():
    """Display all chat messages from history"""
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def browser_speech_html(text, voice_name, voice_code, auto_speak=False):
    """Build a browser speech control; escape LLM text before embedding in JS."""
    safe_text = json.dumps(text).replace("<", "\\u003c")
    safe_name = json.dumps(voice_name)
    language = "-".join(voice_code.split("-")[:2])
    safe_language = json.dumps(language)
    safe_auto_speak = json.dumps(auto_speak)
    return f"""
        <div style="font-family: sans-serif; display: flex; align-items: center; gap: 10px;">
            <button id="play" type="button">▶ Play interviewer voice</button>
            <button id="stop" type="button">■ Stop</button>
        </div>
        <div id="status" aria-live="polite" style="font: 12px sans-serif; margin-top: 8px;"></div>
        <script>
            const text = {safe_text};
            const preferredName = {safe_name};
            const language = {safe_language};
            const autoSpeak = {safe_auto_speak};
            const status = document.getElementById("status");
            // The Streamlit component runs in an iframe. Use the main page's
            // speech context when accessible so its Start Interview click
            // can unlock Chrome's user-activation requirement.
            let speechWindow = window;
            try {{
                if (window.parent !== window && window.parent.speechSynthesis) {{
                    speechWindow = window.parent;
                }}
            }} catch (error) {{
                // Cross-origin frames can still use their own speech context.
            }}
            const synthesis = speechWindow.speechSynthesis;
            const SpeechUtterance = speechWindow.SpeechSynthesisUtterance
                || window.SpeechSynthesisUtterance;
            const isFemale = preferredName !== "Alex";
            const femaleNames = /aria|natasha|sonia|jenny|zira|samantha|karen|catherine|hazel|libby|susan|victoria|neerja|heera|swara|priya|raveena|aditi|female/i;
            const maleNames = /\\b(alex|guy|david|daniel|george|mark|male)\\b/i;
            const preferences = {{
                Alex: ["alex", "guy", "david", "daniel"],
                Aria: ["aria", "jenny", "zira", "samantha"],
                Natasha: ["neerja", "heera", "swara", "priya", "natasha", "karen", "catherine"],
                Sonia: ["sonia", "libby", "hazel"]
            }};
            let voices = [];
            let selectedVoice = null;

            function rankVoices(profile, preferredLanguage) {{
                const hints = preferences[profile] || [];
                const female = profile !== "Alex";
                return voices.map((voice, index) => {{
                    const name = voice.name.toLowerCase();
                    const lang = voice.lang.toLowerCase();
                    const hint = hints.findIndex(value => name.includes(value));
                    let score = hint < 0 ? 0 : 100 - hint * 10;
                    score += lang === preferredLanguage.toLowerCase() ? 30 : lang.startsWith("en") ? 10 : 0;
                    score += female && femaleNames.test(name) ? 30 : 0;
                    score += !female && maleNames.test(name) ? 30 : 0;
                    score -= female && maleNames.test(name) ? 100 : 0;
                    return {{ index, score }};
                }}).sort((a, b) => b.score - a.score);
            }}

            function chooseVoiceFor(profile, preferredLanguage, excluded = []) {{
                const ranked = rankVoices(profile, preferredLanguage).filter(item =>
                    voices[item.index].lang.toLowerCase().startsWith("en")
                    && !excluded.includes(item.index));
                const female = ranked.filter(item => {{
                    const name = voices[item.index].name;
                    return femaleNames.test(name) && !maleNames.test(name);
                }});
                const hasFemaleVoice = voices.some(voice =>
                    voice.lang.toLowerCase().startsWith("en")
                    && femaleNames.test(voice.name) && !maleNames.test(voice.name));
                return (profile === "Alex" || !hasFemaleVoice ? ranked[0] : female[0])?.index;
            }}

            function chooseVoice() {{
                if (preferredName !== "Natasha") return chooseVoiceFor(preferredName, language);
                const aria = chooseVoiceFor("Aria", "en-US");
                const sonia = chooseVoiceFor("Sonia", "en-GB");
                return chooseVoiceFor("Natasha", "en-IN", [aria, sonia])
                    ?? chooseVoiceFor("Natasha", "en-IN", [aria])
                    ?? chooseVoiceFor("Natasha", "en-IN");
            }}

            function loadVoices() {{
                if (!synthesis) return;
                const available = synthesis.getVoices();
                if (!available.length) return;
                voices = available;
                selectedVoice = voices[chooseVoice()] || null;
                status.textContent = "";
            }}

            if (synthesis) {{
                synthesis.addEventListener("voiceschanged", loadVoices);
                loadVoices();
                if (!voices.length) status.textContent = "Loading browser voices…";
            }} else {{
                status.textContent = "Speech playback is not supported in this browser.";
            }}

            async function playSpeech(automatic = false) {{
                if (!synthesis) return;
                if (!voices.length) {{
                    await new Promise(resolve => {{
                        synthesis.addEventListener("voiceschanged", resolve, {{ once: true }});
                        setTimeout(resolve, 1500);
                    }});
                    loadVoices();
                }}
                synthesis.cancel();
                const utterance = new SpeechUtterance(text);
                utterance.voice = selectedVoice;
                utterance.lang = utterance.voice?.lang || language;
                utterance.pitch = isFemale ? {{ Aria: 1.2, Natasha: 1.3, Sonia: 1.15 }}[preferredName] : 0.95;
                utterance.rate = preferredName === "Natasha" ? 0.95 : 1;
                let started = false;
                status.textContent = automatic ? "Starting interviewer voice…" : "Speaking…";
                utterance.onstart = () => {{
                    started = true;
                    status.textContent = "Speaking…";
                }};
                utterance.onend = () => status.textContent = "";
                utterance.onerror = () => status.textContent = "Speech playback failed. Press Play to retry.";
                synthesis.speak(utterance);
                if (automatic) setTimeout(() => {{
                    if (!started && !synthesis.speaking) status.textContent = "Autoplay blocked? Press Play.";
                }}, 4000);
            }}
            document.getElementById("play").addEventListener("click", () => playSpeech());
            document.getElementById("stop").addEventListener("click", () => {{
                synthesis?.cancel();
                status.textContent = "";
            }});
            if (autoSpeak) setTimeout(() => playSpeech(true), 0);
        </script>
    """


def render_interviewer_speech(text, auto_speak=False):
    voice = get_ai_voice_details()[st.session_state["ai_voice"]]
    components.html(
        browser_speech_html(text, voice["name"], voice["code"], auto_speak),
        height=55,
    )


def speak_current_question():
    """Try speaking each new question once; retain a manual Play control."""
    if st.session_state["current_question"]:
        render_interviewer_speech(
            st.session_state["current_question"],
            auto_speak=not st.session_state["question_spoken"],
        )
        st.session_state["question_spoken"] = True
        st.session_state["awaiting_response"] = True


def generate_next_question():
    """Generate and prepare the next question"""
    if st.session_state["conversations"]:
        last_conv = st.session_state["conversations"][-1]
        next_question, _ = asyncio.run(analyze_candidate_response_and_generate_new_question(
            last_conv["Question"],
            last_conv["Candidate Answer"],
            st.session_state["job_description"],
            st.session_state["resume_highlights"],
        ))
    else:
        next_question = "Tell me about yourself and your experience."

    st.session_state["current_question"] = next_question
    st.session_state["messages"].append({"role": "assistant", "content": next_question})
    st.session_state["question_spoken"] = False
    st.session_state["awaiting_response"] = False


def process_candidate_response(transcript):
    """Process candidate's response and move to next state"""
    # Add candidate's answer to chat
    st.session_state["messages"].append({"role": "user", "content": transcript})

    # Generate feedback for this response
    if st.session_state["qa_index"] < st.session_state["max_questions"] - 1:
        # Not the last question - generate next question and feedback
        next_question, feedback = asyncio.run(analyze_candidate_response_and_generate_new_question(
            st.session_state["current_question"],
            transcript,
            st.session_state["job_description"],
            st.session_state["resume_highlights"],
        ))
    else:
        # Last question - only generate feedback
        feedback = asyncio.run(get_feedback_of_candidate_response(
            st.session_state["current_question"],
            transcript,
            st.session_state["job_description"],
            st.session_state["resume_highlights"],
        ))

    # Store conversation
    st.session_state["conversations"].append(
        {
            "Question": st.session_state["current_question"],
            "Candidate Answer": transcript,
            "Evaluation": feedback["score"],
            "Feedback": feedback["feedback"],
        }
    )

    # Move to next question or complete interview
    st.session_state["qa_index"] += 1
    st.session_state["processing_audio"] = False
    st.session_state["awaiting_response"] = False

    if st.session_state["qa_index"] <= st.session_state["max_questions"]:
        # Prepare next question
        generate_next_question()
        st.success("✅ Answer recorded! Preparing next question...")
    else:
        # Interview completed - prepare thanks message
        st.session_state["interview_completed"] = True
        prepare_thanks_message()


def prepare_thanks_message():
    """Prepare and display thanks message"""
    if not st.session_state["thanks_message_prepared"]:
        final_note = get_final_thanks_message(st.session_state["name"])
        st.session_state["messages"].append(
            {"role": "assistant", "content": final_note}
        )
        st.session_state["thanks_message_prepared"] = True
        st.session_state["qa_index"] -= 1
        st.rerun()


def speak_thanks_message():
    """Speak the thanks message"""
    if (
        st.session_state["thanks_message_prepared"]
        and not st.session_state["thanks_message_spoken"]
    ):

        st.session_state["thanks_message_spoken"] = True
        st.success("🎉 Interview completed! Thank you for your time.")

        # Now show final results
        st.session_state["show_final_results"] = True
        st.rerun()


def handle_audio_recording():
    """Handle audio recording and processing"""
    if not (
        st.session_state["awaiting_response"]
        and not st.session_state["processing_audio"]
    ):
        return

    st.write("**🎙️ Please record your answer to the question above**")

    audio_key = f"audio_input_{st.session_state['qa_index']}_{len(st.session_state['messages'])}"
    audio_data = st.audio_input("Record your answer", key=audio_key)

    if audio_data is not None:
        st.session_state["processing_audio"] = True

        with st.spinner("Processing your answer..."):
            # Save audio file
            name = st.session_state["name"]
            safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
            filename = f"audio/{safe_name}/{safe_name}_{st.session_state['qa_index'] + 1}.wav"
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            with open(filename, "wb") as f:
                f.write(audio_data.read())

            # Transcribe audio
            transcript = transcribe_with_speechmatics(filename)

            if transcript and transcript.strip():
                process_candidate_response(transcript)
                st.rerun()
            else:
                st.error("No speech detected in audio. Please try recording again.")
                st.session_state["processing_audio"] = False


def display_final_results():
    """Display final interview results"""
    if (
        not st.session_state["show_final_results"]
        or not st.session_state["conversations"]
    ):
        return

    render_interviewer_speech(
        st.session_state["messages"][-1]["content"],
        auto_speak=not st.session_state["thanks_message_auto_played"],
    )
    st.session_state["thanks_message_auto_played"] = True

    with st.spinner("Calculating final score..."):
        final_score = get_overall_evaluation_score(st.session_state["conversations"])

        # Save interview data
        now = datetime.now().isoformat() + "Z"
        interview_data = {
            "name": st.session_state["name"],
            "createdAt": now,
            "updatedAt": now,
            "id": 1,
            "job_description": st.session_state["job_description"],
            "resume_highlights": st.session_state["resume_highlights"],
            "conversations": st.session_state["conversations"],
            "overall_score": round(final_score, 2),
        }
        save_interview_data(interview_data, candidate_name=st.session_state["name"])

    # Display results
    st.subheader("🎉 Interview Results")
    st.markdown(f"**Candidate:** {st.session_state['name']}")
    st.markdown(f"**Overall Score:** {final_score:.2f}/10")

    # Show detailed summary
    st.subheader("Detailed Interview Summary")
    for i, conv in enumerate(st.session_state["conversations"], 1):
        with st.expander(f"Question {i} (Score: {conv['Evaluation']}/10)"):
            st.write(f"**Q:** {conv['Question']}")
            st.write(f"**A:** {conv['Candidate Answer']}")
            st.write(f"**Feedback:** {conv['Feedback']}")

    # New interview option
    if st.button("Start New Interview"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def render_interview_progress():
    """Render interview progress indicator"""
    if st.session_state.get("interview_started", False):
        progress_text = f"Question {st.session_state['qa_index']} of {st.session_state['max_questions']}"
        st.markdown(
            f'<div class="interview-progress"><strong>{progress_text}</strong></div>',
            unsafe_allow_html=True,
        )


def main():
    """Main application function"""
    # Setup
    setup_page_config()
    initialize_session_state()

    # Header
    st.title("🤖 AI Interview System")
    insturctions = st.empty()
    if not  st.session_state["interview_started"]:
        insturctions = get_instructions()

    # Sidebar
    uploaded_resume, candidate_name, job_description, submit = render_sidebar()

    # Process submission
    if submit and uploaded_resume and job_description:
        insturctions.empty()
        missing_key = missing_llm_api_key()
        if missing_key:
            st.error(
                f"Missing {missing_key}. Add it to a .env file in the project root "
                "(see .env.example), then restart the app and submit again."
            )
        else:
            try:
                process_resume_submission(uploaded_resume, job_description, candidate_name)
            except AuthenticationError:
                st.error(
                    f"The AI provider rejected your API key for {LLM_MODEL}. "
                    "Check the key in .env, restart the app, and try again."
                )
            except ServiceUnavailableError:
                st.error(
                    "The configured Gemini models are temporarily overloaded (503). "
                    "Please wait a moment and submit again."
                )
            except RateLimitError:
                st.error(
                    "Gemini's rate limit was reached. Wait for your quota to reset "
                    "and submit again."
                )
            except (APIConnectionError, Timeout):
                st.error("Could not reach the AI provider. Check your connection and submit again.")
        

    # Start interview button
    if valid_candidate_name(st.session_state["name"]) and not st.session_state["interview_started"]:
        if st.button("Start Interview"):
            start_interview()
            st.rerun()

    # Interview section
    if st.session_state.get("interview_started", False):
        render_interview_progress()

        # Show chat history
        st.subheader("Interview Chat")
        display_chat_messages()

        # Handle different interview states
        if not st.session_state["interview_completed"]:
            # Active interview
            speak_current_question()
            handle_audio_recording()
        elif not st.session_state["thanks_message_prepared"]:
            # Interview just completed - prepare thanks
            prepare_thanks_message()
        elif not st.session_state["thanks_message_spoken"]:
            # Thanks message prepared but not spoken
            speak_thanks_message()
        else:
            # Everything done - show results
            display_final_results()


if __name__ == "__main__":
    main()
