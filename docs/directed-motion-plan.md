# Directed motion implementation

1. Route shot planning and motion code to an explicitly configured director. Validate source references, timing and narration before rendering.
2. Give the solar eclipse benchmark four connected shots covering the shadow, alignment, observer comparison and corona. Supply local procedural motion when external art is unavailable.
3. Render the benchmark using the production caption and audio mixer. Inspect the encoded frames and media streams. Run the backend regression suite.
4. Evaluate further releases on a product demo and a data explainer, with human review of the finished audio and picture.

## Running the implementation

Install the backend's `anthropic` extra. Set `STUDIO_DIRECTOR_MODEL=claude-opus-5-5` and `ANTHROPIC_API_KEY` in the backend environment, then restart the backend. Submit a brief through the existing composer. The director handles storyboard and motion authoring. Research, assets, voice and creative review use their existing provider settings.

From the backend directory, run `../.venv/bin/python scripts/render_eclipse.py` to regenerate the four-shot eclipse reel. With Gemini configured it requests Fenrir with a different delivery instruction for each shot. The provider can fall back to Edge neural speech or local Flite. The premiere shows which voice was used. The `eclipsevoice` project contains the narrated preview, final MP4 and a contact sheet sampled from the encoded video.

For the next comparison, use a product brief with actual screen captures and a data brief with cited values. Compare the same inputs at the same duration, measuring delivered visual actions, spoken pace, citation accuracy, caption readability and time to export.
