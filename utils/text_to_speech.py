import streamlit.components.v1 as components
import json

VOICE_MAP = {
    "en-US-GuyNeural": {"lang": "en-US", "gender": "male"},
    "en-US-AriaNeural": {"lang": "en-US", "gender": "female"},
    "en-GB-SoniaNeural": {"lang": "en-GB", "gender": "female"},
    "en-AU-NatashaNeural": {"lang": "en-AU", "gender": "female"},
}


def speak_text(text, voice="en-US-GuyNeural", rate="+0%", pitch="+0Hz"):
    """Use browser's built-in SpeechSynthesis API to speak text."""
    voice_config = VOICE_MAP.get(voice, VOICE_MAP["en-US-GuyNeural"])
    safe_text = json.dumps(text)

    components.html(
        f"""
        <script>
        (function() {{
            const text = {safe_text};
            const synth = window.speechSynthesis;
            synth.cancel();

            function speak() {{
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = "{voice_config['lang']}";
                utterance.rate = 1.0;
                utterance.pitch = 1.0;
                utterance.volume = 1.0;

                const voices = synth.getVoices();
                const preferredGender = "{voice_config['gender']}";
                const langVoices = voices.filter(v => v.lang.startsWith("{voice_config['lang'].split('-')[0]}"));

                let selectedVoice = langVoices.find(v => {{
                    const name = v.name.toLowerCase();
                    if (preferredGender === "male") {{
                        return name.includes("male") || name.includes("guy") || name.includes("david") || name.includes("mark");
                    }} else {{
                        return name.includes("female") || name.includes("aria") || name.includes("zira") || name.includes("sonia") || name.includes("natasha");
                    }}
                }});

                if (!selectedVoice && langVoices.length > 0) {{
                    selectedVoice = langVoices[0];
                }}
                if (selectedVoice) {{
                    utterance.voice = selectedVoice;
                }}
                synth.speak(utterance);
            }}

            if (synth.getVoices().length === 0) {{
                synth.addEventListener("voiceschanged", speak, {{ once: true }});
            }} else {{
                speak();
            }}
        }})();
        </script>
        """,
        height=0,
    )
