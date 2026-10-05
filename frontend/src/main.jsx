import React, { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
    const [prompt, setPrompt] = useState("");
    const [style, setStyle] = useState("muktak");
    const [emotion, setEmotion] = useState("गंभीर और आशावादी");
    const [lines, setLines] = useState(8);
    const [rhyme, setRhyme] = useState("auto");
    const [poem, setPoem] = useState("");
    const [validation, setValidation] = useState(null);
    const [txtUrl, setTxtUrl] = useState("");
    const [csvUrl, setCsvUrl] = useState("");
    const [voiceFile, setVoiceFile] = useState(null);
    const [photo, setPhoto] = useState(null);
    const [voiceId, setVoiceId] = useState("");
    const [audioUrl, setAudioUrl] = useState("");
    const [videoUrl, setVideoUrl] = useState("");
    const [busy, setBusy] = useState(false);
    const [status, setStatus] = useState("");
    const [token, setToken] = useState(localStorage.getItem("hindi_poem_token") || "");
    const authHeaders = () => token ? { "Authorization": `Bearer ${token}` } : {};
    const recorderRef = useRef(null);
    const chunksRef = useRef([]);
  const [authPrompt, setAuthPrompt] = useState(false);
  const [authScreen, setAuthScreen] = useState(null); // 'signin' | null
  const [signinToken, setSigninToken] = useState("");
  const [page, setPage] = useState(window.location.hash ? window.location.hash.replace('#','') : 'home');
  const [loginMobile, setLoginMobile] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [signupFirst, setSignupFirst] = useState("");
  const [signupLast, setSignupLast] = useState("");
  const [signupMobile, setSignupMobile] = useState("");
  const [signupDob, setSignupDob] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupErrors, setSignupErrors] = useState({});
  const [loginErrors, setLoginErrors] = useState({});
  const [toasts, setToasts] = useState([]);

  function showToast(message, type = 'info', duration = 4000) {
    const id = Math.random().toString(36).slice(2,9);
    const toast = {id, message, type};
    setToasts(t => [...t, toast]);
    // add simple fade-in/out by setting a visible flag
    setTimeout(()=> setToasts(t => t.map(x => x.id===id?{...x, visible:true}:x)), 20);
    setTimeout(()=> setToasts(t => t.map(x => x.id===id?{...x, visible:false}:x)), duration - 300);
    setTimeout(()=> setToasts(t => t.filter(x=>x.id !== id)), duration);
  }

  // keep hash in sync with page state
  React.useEffect(()=>{ if(window.location.hash.replace('#','') !== page) window.location.hash = page; }, [page]);

  // On initial load, check URL fragment for token (from Google callback)
  React.useEffect(()=>{
    try {
      const hash = window.location.hash || "";
      // Support fragments like "#signin?token=..." or "#token=..."
      const q = hash.includes('?') ? hash.split('?')[1] : hash.replace('#','');
      const params = new URLSearchParams(q || '');
      const tokenParam = params.get('token');
      if (tokenParam) {
        setToken(tokenParam);
        localStorage.setItem('hindi_poem_token', tokenParam);
        setStatus(messages[uiLang()].signInSuccess);
        // remove token from fragment and navigate home
        window.location.hash = 'home';
        showToast(messages[uiLang()].signInSuccess, 'success');
      }
    } catch (e) { /* ignore */ }
  }, []);

  // Localization and auth helpers
  const messages = {
    hi: {
      signInPrompt: "कृपया अपना एक्सेस टोकन दर्ज करें:",
      signInSuccess: "सफलतापूर्वक साइन-इन हुआ।",
      signOut: "साइन-आउट कर दिया गया।",
      signUp: "साइन-अप करने के लिये रेपो पर जाएँ और टोकन प्राप्त करें।",
      signInButton: "साइन इन",
      signUpButton: "साइन अप",
      signOutButton: "साइन आउट"
    },
    en: {
      signInPrompt: "Enter your access token:",
      signInSuccess: "Signed in successfully.",
      signOut: "Signed out.",
      signUp: "To sign up, visit the project repo and obtain an access token.",
      signInButton: "Sign In",
      signUpButton: "Sign Up",
      signOutButton: "Sign Out"
    }
  };

  function uiLang() { return navigator.language && navigator.language.startsWith("hi") ? "hi" : "en"; }

  function handleSignIn() {
    // navigate to dedicated signin page
    setPage('signin');
  }

  function handleSignOut() {
    const lang = uiLang();
    setToken("");
    localStorage.removeItem("hindi_poem_token");
    setStatus(messages[lang].signOut);
  }

  function handleSignUp() {
    // navigate to dedicated signup page (could open repo as well)
    setPage('signup');
  }

  async function startGoogleSignIn() {
    try {
      const r = await fetch(`${API}/api/auth/google/url`);
      const data = await r.json();
      if (data && data.url) window.location.href = data.url;
    } catch (e) { setStatus("Failed to start Google sign-in."); }
  }

  async function doLogin(e) {
    e?.preventDefault();
    setBusy(true); setStatus("Signing in…");
    // client-side validation
    const errors = {};
    if (!/^\d{10}$/.test(loginMobile)) errors.mobile = 'Mobile must be 10 digits';
    if (!loginPassword || loginPassword.length < 8) errors.password = 'Password must be at least 8 characters';
    setLoginErrors(errors);
    if (Object.keys(errors).length) { setBusy(false); return; }
    try {
      const r = await fetch(`${API}/api/auth/login`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mobile: loginMobile, password: loginPassword})});
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || data.error || 'Login failed');
      setToken(data.token); localStorage.setItem('hindi_poem_token', data.token); setStatus(messages[uiLang()].signInSuccess); setPage('home');
      showToast(messages[uiLang()].signInSuccess, 'success');
    } catch (err) { setStatus(err.message); showToast(err.message, 'error'); }
    finally { setBusy(false); }
  }

  async function doSignup(e) {
    e?.preventDefault();
    setBusy(true); setStatus("Signing up…");
    // client-side validation
    const errors = {};
    if (!signupFirst) errors.first = 'First name required';
    if (!signupLast) errors.last = 'Last name required';
    if (!/^\d{10}$/.test(signupMobile)) errors.mobile = 'Mobile must be 10 digits';
    if (!/^\d{4}-\d{2}-\d{2}$/.test(signupDob)) errors.dob = 'DOB must be YYYY-MM-DD';
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(signupEmail)) errors.email = 'Email is invalid';
    if (!signupPassword || signupPassword.length < 8) errors.password = 'Password must be at least 8 characters';
    setSignupErrors(errors);
    if (Object.keys(errors).length) { setBusy(false); return; }
    try {
      const r = await fetch(`${API}/api/auth/signup`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({first_name: signupFirst, last_name: signupLast, mobile: signupMobile, dob: signupDob, email: signupEmail, password: signupPassword})});
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || data.error || 'Signup failed');
      setToken(data.token); localStorage.setItem('hindi_poem_token', data.token); setStatus(messages[uiLang()].signInSuccess); setPage('home');
      showToast(messages[uiLang()].signInSuccess, 'success');
    } catch (err) { setStatus(err.message); showToast(err.message, 'error'); }
    finally { setBusy(false); }
  }

  async function generate() {
    const uiLang = navigator.language && navigator.language.startsWith("hi") ? "hi" : "en";
    const messages = {
      hi: { busy: "कविता लिखी जा रही है…", auth: "कृपया पहले साइन-अप/साइन-इन करें ताकि आप कविताएँ बना सकें।", ok: "कविता तैयार है।" },
      en: { busy: "Generating poem…", auth: "Please sign up / sign in first to create poems.", ok: "Poem ready." }
    };

    // If no token, short-circuit and show sign-in flow without hitting backend
    if (!token) {
      setStatus(messages[uiLang].auth);
      setAuthPrompt(true);
      setPage('signin');
      return;
    }

    setBusy(true); setStatus(messages[uiLang].busy);
    try {
      const r = await fetch(`${API}/api/poems/generate`, {
        method: "POST",
        headers: {"Content-Type": "application/json", ...authHeaders()},
        // backend currently only supports Hindi ("hi"); always send "hi"
        body: JSON.stringify({prompt, style, emotion, lines: Number(lines), rhyme, language: "hi"})
      });

      // If unauthorized, show sign-in flow
      if (r.status === 401) {
        setStatus(messages[uiLang].auth);
        setAuthPrompt(true);
        setPage('signin');
        return;
      }

      let data = {};
      try { data = await r.json(); } catch { /* ignore parse errors */ }

      if (!r.ok) throw new Error(data.detail || "Generation failed");
      setPoem(data.poem);
      setValidation(data.validation);
      setStatus(messages[uiLang].ok);
    } catch (e) { setStatus(e.message); }
    finally { setBusy(false); }
  }

  async function transcribe() {
    if (!voiceFile) return setStatus("पहले voice recording चुनें।");
    const fd = new FormData(); fd.append("file", voiceFile);
    setBusy(true); setStatus("आवाज़ को text में बदला जा रहा है…");
    try {
      const r = await fetch(`${API}/api/speech/transcribe`, {method:"POST", headers:authHeaders(), body:fd});
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Transcription failed");
      setPrompt(data.text);
      setStatus("Voice input text में बदल दिया गया है।");
    } catch (e) { setStatus(e.message); }
    finally { setBusy(false); }
  }

  async function cloneVoice() {
    if (!voiceFile) return setStatus("पहले voice sample चुनें।");
    if (!window.confirm("क्या यह आपकी अपनी आवाज़ है और आपके पास इसे clone करने का अधिकार है?")) return;
    const fd = new FormData();
    fd.append("consent", "true");
    fd.append("name", "Hindi Poem Writer User Voice");
    fd.append("files", voiceFile);
    setBusy(true); setStatus("Voice clone बनाया जा रहा है…");
    try {
      const r = await fetch(`${API}/api/voice/clone`, {method:"POST", headers:authHeaders(), body:fd});
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Voice cloning failed");
      setVoiceId(data.voice_id);
      setStatus("Voice clone तैयार है।");
    } catch (e) { setStatus(e.message); }
    finally { setBusy(false); }
  }

  async function synthesize() {
    if (!poem) return setStatus("पहले कविता बनाइए।");
    if (!voiceId) return setStatus("पहले अपना voice clone बनाइए।");
    setBusy(true); setStatus("कविता आपकी आवाज़ में तैयार हो रही है…");
    try {
      const r = await fetch(`${API}/api/speech/synthesize`, {
        method:"POST", headers:{"Content-Type":"application/json", ...authHeaders()},
        body: JSON.stringify({text: poem, voice_id: voiceId})
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "TTS failed");
      setAudioUrl(`${API}${data.audio_url}`);
      setStatus("Voice poem तैयार है।");
    } catch (e) { setStatus(e.message); }
    finally { setBusy(false); }
  }

  async function makeVideo() {
    if (!photo || !audioUrl) return setStatus("Photo और generated audio दोनों चाहिए।");
    const audioBlob = await fetch(audioUrl).then(r => r.blob());
    const fd = new FormData();
    fd.append("photo", photo);
    fd.append("audio", audioBlob, "poem.mp3");
    setBusy(true); setStatus("Cartoon poem video बन रहा है…");
    try {
      const r = await fetch(`${API}/api/video/create`, {method:"POST", headers:authHeaders(), body:fd});
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Video creation failed");
      setVideoUrl(`${API}${data.video_url}`);
      setStatus("Video तैयार है।");
    } catch (e) { setStatus(e.message); }
    finally { setBusy(false); }
  }

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({audio:true});
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    recorder.ondataavailable = e => chunksRef.current.push(e.data);
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, {type:"audio/webm"});
      setVoiceFile(new File([blob], "user-voice.webm", {type:"audio/webm"}));
      stream.getTracks().forEach(t => t.stop());
      setStatus("Recording तैयार है।");
    };
    recorder.start(); recorderRef.current = recorder; setStatus("Recording… फिर Stop दबाएँ।");
  }

  function stopRecording() { recorderRef.current?.stop(); }

  return (
    <main className="page">
      <section className="hero">
        <div>
          <div className="badge">AI AGENT · हिंदी</div>
          <h1>Hindi Poem Writer</h1>
          <p>भाव, छंद, मात्रा और लय के साथ आपकी प्रेरणा से एक नई हिंदी कविता।</p>
        </div>

        {/* Signin / Signup overlays */}
        {page === 'signin' && (
          <div style={{position:'fixed',inset:0,display:'grid',placeItems:'center',background:'rgba(0,0,0,0.4)'}}>
            <div style={{width:420,background:'white',padding:20,borderRadius:12}}>
              <h3>Sign In</h3>
              <div style={{marginBottom:8}}>
                <button onClick={startGoogleSignIn} style={{marginRight:8}}>Sign in with Google</button>
                <span className="muted">or use mobile</span>
              </div>
              <form onSubmit={doLogin}>
                <input placeholder="Mobile" value={loginMobile} onChange={e=>setLoginMobile(e.target.value)} style={{width:'100%',padding:8,marginBottom:8}} />
                {loginErrors.mobile && <div className="validation">{loginErrors.mobile}</div>}
                <input placeholder="Password" type="password" value={loginPassword} onChange={e=>setLoginPassword(e.target.value)} style={{width:'100%',padding:8,marginBottom:8}} />
                {loginErrors.password && <div className="validation">{loginErrors.password}</div>}
                <div style={{display:'flex',justifyContent:'flex-end',gap:8}}>
                  <button type="button" onClick={()=>setPage('home')}>Cancel</button>
                  <button type="submit" disabled={busy}>Sign In</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {page === 'signup' && (
          <div style={{position:'fixed',inset:0,display:'grid',placeItems:'center',background:'rgba(0,0,0,0.4)'}}>
            <div style={{width:520,background:'white',padding:20,borderRadius:12}}>
              <h3>Sign Up</h3>
              <form onSubmit={doSignup}>
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8}}>
                  <input placeholder="First name" value={signupFirst} onChange={e=>setSignupFirst(e.target.value)} />
                  <input placeholder="Last name" value={signupLast} onChange={e=>setSignupLast(e.target.value)} />
                </div>
                {signupErrors.first && <div className="validation">{signupErrors.first}</div>}
                {signupErrors.last && <div className="validation">{signupErrors.last}</div>}
                <input placeholder="Mobile" value={signupMobile} onChange={e=>setSignupMobile(e.target.value)} style={{width:'100%',padding:8,marginTop:8}} />
                {signupErrors.mobile && <div className="validation">{signupErrors.mobile}</div>}
                <input placeholder="DOB (YYYY-MM-DD)" value={signupDob} onChange={e=>setSignupDob(e.target.value)} style={{width:'100%',padding:8,marginTop:8}} />
                {signupErrors.dob && <div className="validation">{signupErrors.dob}</div>}
                <input placeholder="Email (Gmail)" value={signupEmail} onChange={e=>setSignupEmail(e.target.value)} style={{width:'100%',padding:8,marginTop:8}} />
                {signupErrors.email && <div className="validation">{signupErrors.email}</div>}
                <input placeholder="Password" type="password" value={signupPassword} onChange={e=>setSignupPassword(e.target.value)} style={{width:'100%',padding:8,marginTop:8}} />
                {signupErrors.password && <div className="validation">{signupErrors.password}</div>}
                <div style={{display:'flex',justifyContent:'flex-end',gap:8,marginTop:12}}>
                  <button type="button" onClick={()=>setPage('home')}>Cancel</button>
                  <button type="submit" disabled={busy}>Sign Up</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Toast stack */}
        <div style={{position:'fixed',right:16,top:16,display:'flex',flexDirection:'column',gap:8}}>
          {toasts.map(t => (
            <div key={t.id} className={`toast ${t.type==='error'?'toast-error': t.type==='success'?'toast-success':'toast-info'} ${t.visible? 'visible':''}`}>
              <div style={{fontWeight:600, marginBottom:6}}>{t.type==='error'?'Error': t.type==='success'?'Success':'Info'}</div>
              <div>{t.message}</div>
            </div>
          ))}
        </div>

        {/* Inline signin modal */}
        {authScreen === 'signin' && (
          <div style={{position:'fixed',inset:0,display:'grid',placeItems:'center',background:'rgba(0,0,0,0.4)'}}>
            <div style={{width:360,background:'white',padding:20,borderRadius:12}}>
              <h3 style={{marginTop:0}}>{messages[uiLang()].signInButton}</h3>
              <div style={{marginBottom:8}}>{messages[uiLang()].signInPrompt}</div>
              <input type="password" value={signinToken} onChange={e=>setSigninToken(e.target.value)} style={{width:'100%',padding:8,marginBottom:12}} />
              <div style={{display:'flex',justifyContent:'flex-end',gap:8}}>
                <button onClick={()=>{ setAuthScreen(null); setSigninToken(''); }}>Cancel</button>
                <button onClick={()=>{ setToken(signinToken); localStorage.setItem('hindi_poem_token', signinToken); setAuthScreen(null); setAuthPrompt(false); setStatus(messages[uiLang()].signInSuccess); }}>{messages[uiLang()].signInButton}</button>
              </div>
            </div>
          </div>
        )}
        <div className="orb">कविता</div>
      </section>

      <section className="grid">
        <div className="card">
          <h2>1 · आपकी प्रेरणा</h2>
          <div style={{display:'flex',gap:8,alignItems:'center'}}>
            <input type="password" value={token} onChange={e=>{setToken(e.target.value); localStorage.setItem("hindi_poem_token", e.target.value)}} placeholder="Production access token" style={{flex:1}} />
            <button type="button" onClick={handleSignIn}>{messages[uiLang()].signInButton}</button>
            <button type="button" onClick={handleSignUp}>{messages[uiLang()].signUpButton}</button>
            <button type="button" onClick={handleSignOut}>{messages[uiLang()].signOutButton}</button>
          </div>
          <textarea value={prompt} onChange={e=>setPrompt(e.target.value)}
            placeholder="विषय लिखें या अपनी कविता की कुछ पंक्तियाँ दें…"/>
          <div className="row">
            <select value={style} onChange={e=>setStyle(e.target.value)}>
              <option value="muktak">मुक्तक</option>
              <option value="doha">दोहा</option>
              <option value="chaupai">चौपाई</option>
              <option value="free">मुक्त छंद</option>
            </select>
            <select value={rhyme} onChange={e=>setRhyme(e.target.value)}>
              <option value="auto">तुकबंदी: Auto</option>
              <option value="AABB">AABB</option>
              <option value="ABAB">ABAB</option>
              <option value="none">बिना तुक</option>
            </select>
          </div>
          <div className="row">
            <input value={emotion} onChange={e=>setEmotion(e.target.value)} placeholder="भाव"/>
            <input type="number" min="2" max="32" value={lines} onChange={e=>setLines(e.target.value)}/>
          </div>
          <div className="record">
            <button onClick={startRecording}>🎙️ Record voice</button>
            <button onClick={stopRecording}>⏹ Stop</button>
            <button onClick={transcribe} disabled={!voiceFile}>Voice → Text</button>
          </div>
          <button className="primary" disabled={busy} onClick={generate}>✦ नई कविता लिखें</button>

          {authPrompt && (
            <div style={{marginTop:12,padding:12,background:'#fff4e6',borderRadius:12,border:'1px solid #efd9b8'}}>
              <div style={{marginBottom:8}}>{messages[uiLang()].signInPrompt || messages[uiLang()].auth}</div>
              <div style={{display:'flex',gap:8}}>
                <button onClick={() => { setAuthPrompt(false); setAuthScreen('signin'); setSigninToken(token || ''); }}>{messages[uiLang()].signInButton}</button>
                <button onClick={() => { setAuthPrompt(false); handleSignUp(); }}>{messages[uiLang()].signUpButton}</button>
                <button onClick={() => setAuthPrompt(false)} style={{background:'#eee'}}>Dismiss</button>
              </div>
            </div>
          )}
        </div>

        <div className="card poem-card">
          <h2>2 · आपकी कविता</h2>
          <div className="poem">
            {poem || "आपकी नई कविता यहाँ दिखाई देगी…"}
          </div>
          {validation && <div className="validation">
            <b>मात्रा जाँच:</b> {validation.matra_counts.join(" · ")}
            <br/><small>यह production heuristic है; शास्त्रीय प्रकाशन के लिए मानव छंद-परीक्षण आवश्यक है।</small>
          </div>}
          <div className="downloads">
            {validation && <>
              <a href={txtUrl} download>TXT</a>
              <a href={csvUrl} download>CSV</a>
            </>}
          </div>
        </div>

        <div className="card">
          <h2>3 · आपकी आवाज़</h2>
          <p className="muted">केवल अपनी/अधिकृत आवाज़ के लिए voice cloning इस्तेमाल करें।</p>
          <button onClick={cloneVoice} disabled={!voiceFile || busy}>🎧 Create my voice clone</button>
          <button onClick={synthesize} disabled={!poem || !voiceId || busy}>🔊 कविता मेरी आवाज़ में</button>
          {audioUrl && <audio controls src={audioUrl}/>}
        </div>

        <div className="card">
          <h2>4 · Cartoon Poem Video</h2>
          <input type="file" accept="image/*" onChange={e=>setPhoto(e.target.files?.[0] || null)}/>
          <button onClick={makeVideo} disabled={!photo || !audioUrl || busy}>🎬 Video बनाएँ</button>
          {videoUrl && <video controls src={videoUrl}/>}
          {videoUrl && <a className="download" href={videoUrl} download>Download Video</a>}
        </div>
      </section>
      <footer>{busy ? "Processing…" : status || "Ready"} · Hindi Poem Writer</footer>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
