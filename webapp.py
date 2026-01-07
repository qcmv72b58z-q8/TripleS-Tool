import streamlit as st
import instaloader
from fpdf import FPDF
import matplotlib.pyplot as plt
import os
import requests
import yagmail
import time
import random
from collections import Counter
import arabic_reshaper
from bidi.algorithm import get_display

# --- CONFIGURATION ---
SENDER_EMAIL = "YOUR_EMAIL@gmail.com"
SENDER_PASSWORD = "YOUR_APP_PASSWORD"

# --- STEP 1: FONT LOADING ---
HEADERS = {'User-Agent': 'Mozilla/5.0'}
FONT_REG = "Cairo-Regular.ttf"
FONT_BOLD = "Cairo-Bold.ttf"

def setup_fonts():
    def clean_download(url, filename):
        if os.path.exists(filename) and os.path.getsize(filename) < 50000:
            try: os.remove(filename)
            except: pass
        if not os.path.exists(filename):
            try:
                r = requests.get(url, headers=HEADERS)
                if r.status_code == 200:
                    with open(filename, 'wb') as f: f.write(r.content)
            except: pass

    clean_download("https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Regular.ttf", FONT_REG)
    clean_download("https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Bold.ttf", FONT_BOLD)

setup_fonts()

# --- STEP 2: TEXT PROCESSOR ---
def safe_text(text, is_arabic=False):
    if not text: return ""
    text = str(text)
    if is_arabic:
        clean = "".join(c for c in text if c <= '\uFFFF')
        try:
            reshaped = arabic_reshaper.reshape(clean)
            return get_display(reshaped)
        except: return clean
    else:
        return text.encode('latin-1', 'ignore').decode('latin-1')

def clean_number(num):
    return "{:,}".format(num)

# --- STEP 3: DEEP SCAN ENGINE (HUMAN MODE) ---
def get_instagram_data(username, session_user, session_pass):
    L = instaloader.Instaloader()
    
    # LOGIN ATTEMPT (Silent)
    if session_user and session_pass:
        try:
            L.login(session_user, session_pass)
        except: pass 

    try:
        profile = instaloader.Profile.from_username(L.context, username)
        
        limit = 40  # Safer limit
        posts_data = []
        likes = []
        comments = []
        dates = []
        hashtags = []
        captions_len = []
        vid_c = 0
        img_c = 0
        count = 0
        
        for post in profile.get_posts():
            count += 1
            likes.append(post.likes)
            comments.append(post.comments)
            dates.append(post.date)
            hashtags.extend(post.caption_hashtags)
            if post.caption: captions_len.append(len(post.caption))
            if post.is_video: vid_c += 1
            else: img_c += 1
            
            if count >= limit: break
            
            # --- THE FIX: RANDOM HUMAN DELAY ---
            # Sleeps for 3 to 6 seconds to look exactly like a human on a phone
            time.sleep(random.uniform(3, 6))
            
        if count == 0: return None

        avg_likes = int(sum(likes) / count)
        avg_comments = int(sum(comments) / count)
        eng_rate = round(((avg_likes + avg_comments) / profile.followers) * 100, 2)
        price_high = int(avg_likes * 0.25)
        days = [d.strftime("%A") for d in dates]
        
        return {
            "username": username,
            "followers": profile.followers,
            "eng_rate": eng_rate,
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "likes_history": likes,
            "vid_count": vid_c,
            "img_count": img_c,
            "top_hashtags": Counter(hashtags).most_common(10),
            "days": Counter(days),
            "avg_len": int(sum(captions_len)/len(captions_len)) if captions_len else 0,
            "price_high": price_high,
            "count": count
        }
    except Exception as e:
        # DETECT 401 BLOCK
        err_msg = str(e)
        if "401" in err_msg or "wait" in err_msg.lower():
            st.error(f"🚨 Instagram Speed Limit Hit: Please wait 15 minutes before scanning @{username} again.")
        else:
            st.error(f"Error scanning @{username}: {e}")
        return None

# --- PROFESSIONAL CHARTS THEME ---
def generate_comparison_charts(data1, data2=None):
    plt.style.use('bmh')
    
    # 1. Growth Chart
    plt.figure(figsize=(10, 5))
    plt.plot(data1['likes_history'][::-1], color='#D4AF37', linewidth=3, label=f"@{data1['username']}")
    if data2:
        plt.plot(data2['likes_history'][::-1], color='#800000', linewidth=3, label=f"@{data2['username']}")
    
    plt.title("Engagement Velocity (Last 40 Posts)", fontsize=14, fontweight='bold', pad=20)
    plt.xlabel("Timeline", fontsize=10)
    plt.ylabel("Likes", fontsize=10)
    plt.legend(frameon=True, facecolor='white', framealpha=1)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("chart_growth_vs.png", dpi=300)
    plt.close()
    
    # 2. Mix Chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    
    ax1.pie([max(1, data1['img_count']), max(1, data1['vid_count'])], labels=['Images', 'Reels'], 
            colors=['#333333', '#D4AF37'], autopct='%1.1f%%', startangle=90)
    ax1.set_title(f"@{data1['username']}", fontweight='bold')
    
    if data2:
        ax2.pie([max(1, data2['img_count']), max(1, data2['vid_count'])], labels=['Images', 'Reels'], 
                colors=['#333333', '#800000'], autopct='%1.1f%%', startangle=90)
        ax2.set_title(f"@{data2['username']}", fontweight='bold')
    else:
        ax2.axis('off')
        
    plt.suptitle("Content Strategy Mix", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig("chart_pie_vs.png", dpi=300)
    plt.close()

# --- 8-PAGE PDF GENERATOR ---
TRANSLATIONS = {
    'English 🇺🇸': {'h1': "WAR ROOM REPORT", 'sub': "Competitive Intelligence", 'rec': "Strategic Recommendations"},
    'Arabic 🇸🇦': {'h1': "تقرير غرفة العمليات", 'sub': "تحليل المنافسين", 'rec': "التوصيات الاستراتيجية"},
    'Spanish 🇪🇸': {'h1': "REPORTE ESTRATEGICO", 'sub': "Inteligencia Competitiva", 'rec': "Recomendaciones"},
    'French 🇫🇷': {'h1': "RAPPORT STRATEGIQUE", 'sub': "Intelligence Concurrentielle", 'rec': "Recommandations"},
    'German 🇩🇪': {'h1': "WAR ROOM REPORT", 'sub': "Wettbewerbsanalyse", 'rec': "Empfehlungen"},
    'Italian 🇮🇹': {'h1': "RAPPORTO STRATEGICO", 'sub': "Analisi Competitiva", 'rec': "Raccomandazioni"},
    'Portuguese 🇧🇷': {'h1': "RELATORIO ESTRATEGICO", 'sub': "Inteligencia Competitiva", 'rec': "Recomendacoes"},
    'Turkish 🇹🇷': {'h1': "STRATEJIK RAPOR", 'sub': "Rekabet Analizi", 'rec': "Oneriler"}
}

def create_pdf(data, comp, lang_key):
    pdf = FPDF()
    USE_ARABIC = False
    try:
        if os.path.exists(FONT_REG) and os.path.getsize(FONT_REG) > 50000:
            pdf.add_font('Cairo', '', FONT_REG, uni=True)
            pdf.add_font('Cairo', 'B', FONT_BOLD, uni=True)
            F = 'Cairo'
            if "Arabic" in lang_key: USE_ARABIC = True
        else: raise Exception("Font Missing")
    except:
        F = 'Arial'
        USE_ARABIC = False

    txt = TRANSLATIONS.get(lang_key, TRANSLATIONS['English 🇺🇸'])
    
    # PAGE 1: COVER
    pdf.add_page()
    pdf.set_fill_color(10, 10, 10)
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.set_text_color(212, 175, 55)
    pdf.set_font(F, 'B', 30)
    pdf.set_y(30)
    pdf.cell(0, 10, safe_text(txt['h1'], USE_ARABIC), align='C', ln=True)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(F, '', 14)
    pdf.cell(0, 10, safe_text(txt['sub'], USE_ARABIC), align='C', ln=True)

    if comp:
        pdf.set_y(80)
        pdf.set_font(F, 'B', 20)
        pdf.set_text_color(212, 175, 55)
        pdf.cell(95, 10, safe_text(f"@{data['username']}", USE_ARABIC), align='C')
        pdf.set_text_color(200, 50, 50)
        pdf.set_x(115)
        pdf.cell(95, 10, safe_text(f"@{comp['username']}", USE_ARABIC), align='C', ln=True)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(F, 'B', 40)
        pdf.set_y(75)
        pdf.cell(0, 20, "VS", align='C', ln=True)
        
        y = 120
        metrics = [
            ("Followers", data['followers'], comp['followers']),
            ("Engagement", f"{data['eng_rate']}%", f"{comp['eng_rate']}%"),
            ("Value/Post", f"${data['price_high']}", f"${comp['price_high']}")
        ]
        for label, s1, s2 in metrics:
            pdf.set_y(y)
            pdf.set_font(F, '', 12)
            pdf.set_text_color(200, 200, 200)
            pdf.cell(0, 10, label, align='C', ln=True)
            pdf.set_y(y+8)
            pdf.set_font(F, 'B', 16)
            pdf.set_text_color(212, 175, 55)
            pdf.cell(95, 10, str(s1), align='C')
            pdf.set_x(115)
            pdf.set_text_color(200, 50, 50)
            pdf.cell(95, 10, str(s2), align='C')
            y += 30
    else:
        pdf.set_y(100)
        pdf.set_font(F, 'B', 24)
        pdf.cell(0, 10, safe_text(f"@{data['username']}", USE_ARABIC), align='C', ln=True)

    # PAGES 2-8
    sections = [
        ("Key Metrics Dashboard", data['followers'], f"{data['eng_rate']}%", f"${data['price_high']}"),
        ("Growth & Velocity", "chart_growth_vs.png"),
        ("Content Strategy Mix", "chart_pie_vs.png"),
        ("Hashtag Intelligence", data['top_hashtags']),
        ("Strategic Recommendations", "recs"),
        ("Final Verdict", data['eng_rate'])
    ]
    
    for title, content1, *rest in sections:
        pdf.add_page()
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_fill_color(20, 20, 20)
        pdf.rect(0, 0, 210, 30, 'F')
        pdf.set_text_color(212, 175, 55)
        pdf.set_font(F, 'B', 16)
        pdf.set_y(10)
        pdf.cell(0, 10, safe_text(title, USE_ARABIC), align='C', ln=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_y(50)
        
        if title == "Key Metrics Dashboard":
            pdf.set_font(F, 'B', 14)
            pdf.cell(60, 30, "Followers", border=1, align='C')
            pdf.cell(60, 30, "Engagement", border=1, align='C')
            pdf.cell(60, 30, "Value", border=1, align='C', ln=True)
            pdf.set_font(F, 'B', 20)
            pdf.cell(60, 20, clean_number(content1), align='C')
            pdf.cell(60, 20, str(rest[0]), align='C')
            pdf.set_text_color(0, 150, 0)
            pdf.cell(60, 20, str(rest[1]), align='C')
        elif title == "Hashtag Intelligence":
            pdf.set_font(F, '', 12)
            for tag, count in content1:
                pdf.cell(0, 10, safe_text(f"#{tag} ({count})", USE_ARABIC), ln=True)
        elif title == "Strategic Recommendations":
            pdf.set_font(F, '', 12)
            recs = []
            if data['eng_rate'] < 2: recs.append("❌ Low Engagement. Recommendation: Increase Reels frequency to 3x/week.")
            if comp and comp['followers'] > data['followers']:
                diff = comp['followers'] - data['followers']
                recs.append(f"⚠️ Competitor Gap: @{comp['username']} leads by {clean_number(diff)} followers.")
                recs.append("-> Action: Analyze their Hashtag strategy.")
            if not recs: recs.append("✅ Account is performing at Top Tier levels.")
            for r in recs: pdf.multi_cell(0, 10, safe_text(r, USE_ARABIC)); pdf.ln(5)
        elif title == "Final Verdict":
            score = 100
            if content1 < 2: score -= 20
            pdf.set_font(F, 'B', 60)
            if score > 80: pdf.set_text_color(0, 150, 0)
            else: pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 50, f"{score}/100", align='C')
        elif isinstance(content1, str) and ".png" in content1:
            if os.path.exists(content1): pdf.image(content1, x=10, w=190)

    filename = f"{data['username']}_WarReport.pdf"
    pdf.output(filename)
    return filename

def send_email_report(user_email, pdf_path):
    if "YOUR_EMAIL" in SENDER_EMAIL: return False
    try:
        yag = yagmail.SMTP(SENDER_EMAIL, SENDER_PASSWORD)
        yag.send(to=user_email, subject="TripleS Report", contents="Attached.", attachments=pdf_path)
        return True
    except: return False

# --- FRONTEND ---
st.set_page_config(page_title="TripleS Analysis", page_icon="📈")

st.markdown("""
<style>
    .stApp { background-color: #000000; color: #D4AF37; }
    input { background-color: #ffffff !important; color: #000000 !important; }
    div[data-testid="stForm"] { border: 2px solid #D4AF37; padding: 20px; border-radius: 10px; }
    section[data-testid="stSidebar"] label { color: #ffffff !important; font-weight: bold; font-size: 14px; }
    section[data-testid="stSidebar"] input { background-color: #ffffff !important; color: #000000 !important; }
    div.stButton > button { background-color: #D4AF37 !important; color: #000000 !important; font-weight: bold; border: none; width: 100%; }
    button[aria-label="Show password"] { background-color: transparent !important; color: #000000 !important; }
</style>
""", unsafe_allow_html=True)

if os.path.exists("logo.png"): st.sidebar.image("logo.png")

st.sidebar.markdown("### 🔐 Secure Login")
with st.sidebar.form("login_form"):
    user_session = st.text_input("Username")
    pass_session = st.text_input("Password", type="password")
    login_btn = st.form_submit_button("Login & Verify")

if login_btn:
    if user_session and pass_session:
        try:
            L = instaloader.Instaloader()
            L.login(user_session, pass_session)
            st.toast(f"✅ Authenticated: {user_session}")
            st.sidebar.success("✅ Connected")
        except Exception as e:
            err_msg = str(e)
            if "checkpoint" in err_msg.lower() or "challenge" in err_msg.lower():
                 st.error("⚠️ Instagram Security Check Required")
                 st.sidebar.error("Please open Instagram on your phone/browser, approve 'This was me', then click Login again.")
            else:
                 st.error(f"Login Blocked: {e}")
                 st.sidebar.warning("Connection Failed")
    else:
        st.sidebar.warning("Enter details first")

st.sidebar.caption("🔒 Passwords are RAM-only. Never saved.")

st.markdown("<h1 style='text-align: center; color: #D4AF37;'>⚔️ TripleS War Room</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #FFF;'>Automated Intelligence System</p>", unsafe_allow_html=True)

with st.form("run"):
    c1, c2 = st.columns(2)
    with c1: platform = st.selectbox("Platform", ["Instagram"])
    with c2: lang = st.selectbox("Language / اللغة", list(TRANSLATIONS.keys()))
    
    col_a, col_b = st.columns(2)
    with col_a: user = st.text_input("Your Username")
    with col_b: comp = st.text_input("Competitor Account (Optional)")
        
    email = st.text_input("Email Report To (Optional)")
    
    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns([1, 1, 1])
    with b2:
        btn = st.form_submit_button("🚀 Generate PDF 🚀", use_container_width=True)

if btn and user:
    # 1. SCAN MAIN USER
    with st.spinner(f"Scanning @{user}..."):
        data = get_instagram_data(user, user_session, pass_session)
        if data: generate_comparison_charts(data, None)
        
    # 2. SCAN COMPETITOR
    comp_data = None
    if data and comp:
        with st.spinner(f"Scanning Competitor @{comp}..."):
            # EXTRA SAFETY DELAY FOR COMPETITOR SCAN
            time.sleep(3) 
            comp_data = get_instagram_data(comp, user_session, pass_session)
            if comp_data: generate_comparison_charts(data, comp_data)
            
    # 3. GENERATE REPORT
    if data:
        pdf = create_pdf(data, comp_data, lang)
        if email: send_email_report(email, pdf)
        st.success("✅ Report Ready!")
        with open(pdf, "rb") as f:
            st.download_button("📥 Download Report", f, file_name=pdf)
    else:
        st.error("User not found or Private. (Try Logging In via Sidebar)")
