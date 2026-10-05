# Text to Video (Streamlit)

Story paste karein, video khud ban jati hai.

## Script likhne ke 2 tareeqe
1. Simple: sirf apni story ya narration paste karein. App khud scenes aur images bana leti hai.
2. Advanced: har line = `visual prompt (English) | narration`
   (# se shuru hone wali lines ignore hoti hain)

Misal: `story_12min.txt` (72 scenes, 12 minute). App kholte hi ye story box mein aa jati hai.

## Local chalane ke liye
python -m venv venv
venv\Scripts\activate          (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py

Browser mein http://localhost:8501 khulega. Video output/final.mp4 mein banti hai.

## Streamlit Cloud par deploy
1. Poore folder ki files GitHub repo mein upload karein (app.py repo ke root mein ho).
2. share.streamlit.io par GitHub se login karein -> Create app -> repo chunein.
3. Main file path: app.py. Advanced settings mein Python 3.11 chunein.
4. Deploy dabayein.

## Folder
app.py, requirements.txt, packages.txt, story_12min.txt, README.md, .gitignore,
.streamlit/config.toml, fonts/NotoNaskhArabic-Bold.ttf

## Dhyan rakhein
- Images free Pollinations se aati hain, awaz edge-tts se. Dono ke liye internet chahiye.
- Streamlit Cloud par 72 scenes (12 minute) mein bahut waqt lag sakta hai. Pehle chhoti script se test karein.
