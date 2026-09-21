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
  const authHeaders = () => token ? {"Authorization": `Bearer ${token}`} : {};

  const recorderRef = useRef(null);
  const chunksRef = useRef([]);

  async function generate() {
    setBusy(true); setStatus("कविता लिखी जा रही है…");
    try {
      const r = await fetch(`${API}/api/poems/generate`, {
        method: "POST",
        headers: {"Content-Type": "application/json", ...authHeaders()},
        body: JSON.stringify({prompt, style, emotion, lines: Number(lines), rhyme, language: "hi"})
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Generation failed");
      setPoem(data.poem);
      setValidation(data.validation);
      setStatus("कविता तैयार है।");
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
        <div className="orb">कविता</div>
      </section>

      <section className="grid">
        <div className="card">
          <h2>1 · आपकी प्रेरणा</h2>
          <input type="password" value={token} onChange={e=>{setToken(e.target.value); localStorage.setItem("hindi_poem_token", e.target.value)}} placeholder="Production access token" />
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
