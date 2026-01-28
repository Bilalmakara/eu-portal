import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import ForceGraph from 'force-graph';

// --- API AYARLARI ---
const API_BASE_URL = "http://127.0.0.1:8000";
const api = axios.create({ baseURL: API_BASE_URL + "/api" });

// --- YARDIMCI FONKSİYONLAR ---
const getTitle = (profile) => {
    // Duties dizisi varsa ve boş değilse
    if (profile.Duties && Array.isArray(profile.Duties) && profile.Duties.length > 0) {
        // Dizinin kopyasını alıp yıla göre sıralayalım
        const sortedDuties = [...profile.Duties].sort((a, b) => {
            const yearA = parseInt(a.Year) || 0;
            const yearB = parseInt(b.Year) || 0;
            return yearB - yearA;
        });

        // En üstteki (en yeni) kaydın ünvanını döndür
        if (sortedDuties[0] && sortedDuties[0].Title) {
            return sortedDuties[0].Title;
        }
    }

    // Hiçbiri yoksa varsayılan
    return "Akademisyen";
};

// --- MODAL: NOT VE PUANLAMA ---
const NoteModal = ({ isOpen, onClose, onSubmit, type }) => {
    const [note, setNote] = useState("");
    const [rating, setRating] = useState(10);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-[fadeIn_0.2s]">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden transform transition-all scale-100">
                <div className={`p-4 text-white flex justify-between items-center ${type === 'rejected' ? 'bg-red-600' : 'bg-green-600'}`}>
                    <h3 className="font-bold text-lg">{type === 'rejected' ? 'Proje Reddi' : 'Proje Kabulü'}</h3>
                    <button onClick={onClose} className="hover:bg-white/20 p-1 rounded-full">✕</button>
                </div>
                <div className="p-6">
                    <p className="text-slate-600 text-sm mb-4">
                        {type === 'rejected' ? 'Projeyi reddetme sebebinizi belirtiniz.' : 'Proje için değerlendirme notunuzu ve puanınızı giriniz.'}
                    </p>
                    <div className="mb-6">
                        <label className="flex justify-between text-sm font-bold text-slate-700 mb-2">
                            <span>Değerlendirme Puanı</span>
                            <span className="text-[#003d82] text-lg">{rating}/10</span>
                        </label>
                        <input type="range" min="1" max="10" value={rating} onChange={(e)=>setRating(e.target.value)} className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#003d82]"/>
                        <div className="flex justify-between text-xs text-slate-400 mt-1"><span>Düşük</span><span>Yüksek</span></div>
                    </div>
                    <label className="block text-sm font-bold text-slate-700 mb-2">Değerlendirme Notu</label>
                    <textarea className="w-full border border-slate-300 rounded-lg p-3 text-sm focus:ring-2 focus:ring-[#003d82] outline-none min-h-[100px] resize-none bg-slate-50" placeholder={type === 'rejected' ? 'Reddetme sebebi...' : 'Eklemek istediğiniz notlar...'} value={note} onChange={(e)=>setNote(e.target.value)}></textarea>
                    <div className="flex justify-end gap-3 mt-6">
                        <button onClick={onClose} className="px-5 py-2.5 text-slate-600 hover:bg-slate-100 rounded-lg font-bold text-sm transition">İptal</button>
                        <button onClick={()=>onSubmit(note, rating)} className={`px-6 py-2.5 text-white rounded-lg font-bold text-sm shadow-md transition transform active:scale-95 ${type==='rejected'?'bg-red-600 hover:bg-red-700':'bg-green-600 hover:bg-green-700'}`}>Onayla</button>
                    </div>
                </div>
            </div>
        </div>
    );
};

// --- MODAL: EN POPÜLER PROJELER ---
const TopProjectsModal = ({ onClose }) => {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get('/top-projects/')
            .then(res => { setProjects(res.data); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    return (
        <div className="fixed inset-0 bg-slate-900/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white w-full max-w-5xl h-[85vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-slate-200">
                <div className="bg-[#003d82] p-5 flex justify-between items-center text-white shadow-md z-10">
                    <h2 className="text-xl font-bold flex items-center gap-2">En Çok Önerilen 50 Proje</h2>
                    <button onClick={onClose} className="bg-white/10 hover:bg-white/20 p-2 rounded-full transition">✕</button>
                </div>
                <div className="flex-1 overflow-y-auto p-6 bg-slate-50">
                    {loading ? <div className="text-center py-20"><div className="loader"></div></div> : (
                        <div className="grid grid-cols-1 gap-4">
                            {projects.map((p, index) => (
                                <div key={p.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex gap-5 items-start group hover:border-[#003d82] transition">
                                    <div className="bg-slate-100 text-[#003d82] font-black text-xl w-12 h-12 flex items-center justify-center rounded-lg flex-shrink-0 border border-slate-200 group-hover:bg-[#003d82] group-hover:text-white transition">
                                        {index + 1}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-start mb-2">
                                            <h3 className="font-bold text-slate-800 text-lg leading-tight hover:text-[#003d82] transition truncate pr-4 cursor-pointer" title={p.title} onClick={()=>p.url && window.open(p.url, '_blank')}>{p.title}</h3>
                                            <span className="bg-orange-100 text-orange-700 px-3 py-1 rounded-full text-xs font-bold border border-orange-200 whitespace-nowrap flex-shrink-0">
                                                {p.count} Öneri
                                            </span>
                                        </div>
                                        <div className="flex flex-wrap gap-3 text-xs font-medium text-slate-500 mb-3">
                                            <span className="bg-slate-50 px-2 py-1 rounded border">ID: {p.id}</span>
                                            <span className="bg-slate-50 px-2 py-1 rounded border">Bütçe: {p.budget}</span>
                                            <span className="bg-slate-50 px-2 py-1 rounded border">Durum: {p.status}</span>
                                        </div>
                                        {p.url && p.url !== "#" && (
                                            <a href={p.url} target="_blank" className="text-sm text-blue-600 hover:underline flex items-center gap-1 font-medium">🔗 Proje Detaylarını Görüntüle </a>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- MODAL: DUYURULAR ---
const AnnouncementModal = ({ onClose }) => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get('/announcements/')
            .then(res => { setData(res.data); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    return (
        <div className="fixed inset-0 bg-slate-900/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white w-full max-w-2xl max-h-[80vh] rounded-xl shadow-2xl flex flex-col">
                <div className="bg-[#003d82] p-4 flex justify-between items-center text-white rounded-t-xl">
                    <h3 className="font-bold text-lg">Güncel Duyurular</h3>
                    <button onClick={onClose} className="hover:bg-white/20 p-1 rounded">✕</button>
                </div>
                <div className="p-6 overflow-y-auto bg-slate-50 flex-1">
                    {loading ? <div className="text-center"><div className="loader"></div></div> :
                        data.length === 0 ? <p className="text-slate-500 text-center">Henüz duyuru yok.</p> : (
                            <div className="space-y-4">
                                {data.map((ann, i) => (
                                    <div key={i} className="bg-white border-l-4 border-[#003d82] p-4 rounded shadow-sm">
                                        <div className="flex justify-between items-center mb-2">
                                            <h4 className="font-bold text-slate-800">{ann.title}</h4>
                                            <span className="text-xs text-slate-400">{ann.date}</span>
                                        </div>
                                        <p className="text-sm text-slate-600 whitespace-pre-line">{ann.content}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                </div>
            </div>
        </div>
    );
};

// --- GİRİŞ EKRANI ---
const LoginPage = ({ onLogin }) => {
    const [view, setView] = useState("login");
    const [u, setU] = useState("");
    const [p, setP] = useState("");
    const [oldPass, setOldPass] = useState("");
    const [newPass, setNewPass] = useState("");
    const [err, setErr] = useState("");
    const [success, setSuccess] = useState("");
    const [loading, setLoading] = useState(false);

    const handleLogin = (e) => {
        e.preventDefault(); setLoading(true); setErr("");
        api.post('/login/', { username: u, password: p })
            .then(res => {
                if(res.data.status === "success") onLogin(res.data.role, res.data.name);
                else { setErr("Kullanıcı adı veya şifre hatalı."); setLoading(false); }
            })
            .catch(() => { setErr("Sunucu hatası veya hatalı giriş."); setLoading(false); });
    };

    const handleChangePass = (e) => {
        e.preventDefault(); setLoading(true); setErr(""); setSuccess("");
        api.post('/change-password/', { email: u, oldPassword: oldPass, newPassword: newPass })
            .then(res => {
                if (res.data.status === 'success') {
                    setSuccess("Şifreniz başarıyla değiştirildi! Giriş ekranına yönlendiriliyorsunuz...");
                    setTimeout(() => { setView("login"); setP(""); setOldPass(""); setNewPass(""); setSuccess(""); setLoading(false); }, 3000);
                } else {
                    setErr(res.data.message || "Şifre değiştirilemedi. Bilgileri kontrol ediniz.");
                    setLoading(false);
                }
            })
            .catch(error => {
                setErr("Bir hata oluştu: " + (error.response?.data?.message || "Sunucu hatası"));
                setLoading(false);
            });
    };

    return (
        <div className="h-screen login-bg flex flex-col justify-start items-center pt-24 px-4 overflow-y-auto">
            <div className="glass-panel p-10 rounded-2xl w-full max-w-md animate-[fadeIn_0.5s]">
                <div className="text-center mb-8">
                    <img src={`${API_BASE_URL}/images/logo-tek.png`} className="h-24 mx-auto mb-4 object-contain drop-shadow-md" />
                    <h1 className="text-2xl font-bold text-slate-800 tracking-tight">ESTÜ Akademik Portal</h1>
                    <p className="text-sm text-slate-600 mt-1 font-medium">Proje Eşleştirme Sistemi</p>
                </div>

                {err && <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-3 mb-6 text-sm rounded flex items-center gap-2 font-medium">{err}</div>}
                {success && <div className="bg-green-50 border-l-4 border-green-500 text-green-700 p-3 mb-6 text-sm rounded flex items-center gap-2 font-medium">{success}</div>}

                {view === "login" ? (
                    <form onSubmit={handleLogin} className="space-y-5">
                        <input type="text" className="w-full p-4 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-[#003d82] bg-white/90 focus:bg-white transition" placeholder="E-Posta" value={u} onChange={e=>setU(e.target.value)} required/>
                        <input type="password" className="w-full p-4 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-[#003d82] bg-white/90 focus:bg-white transition" placeholder="Şifre" value={p} onChange={e=>setP(e.target.value)} required/>
                        <button disabled={loading} className="w-full bg-[#003d82] text-white py-4 rounded-lg font-bold hover:bg-[#002855] transition shadow-lg flex justify-center items-center">{loading ? <span className="loader"></span> : 'Giriş Yap'}</button>
                        <div className="text-center mt-4"><button type="button" onClick={()=>{setView("forgot"); setErr(""); setSuccess("");}} className="text-sm text-[#003d82] hover:underline font-bold">Şifremi Değiştir</button></div>
                    </form>
                ) : (
                    <form onSubmit={handleChangePass} className="space-y-5">
                        <h3 className="text-lg font-bold text-center border-b pb-2 text-slate-700">Şifre Yenileme</h3>
                        <input type="text" className="w-full p-4 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-[#003d82] bg-white/90 transition" placeholder="E-Posta" value={u} onChange={e=>setU(e.target.value)} required/>
                        <input type="password" className="w-full p-4 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-[#003d82] bg-white/90 transition" placeholder="Eski Şifre" value={oldPass} onChange={e=>setOldPass(e.target.value)} required/>
                        <input type="password" className="w-full p-4 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-[#003d82] bg-white/90 transition" placeholder="Yeni Şifre" value={newPass} onChange={e=>setNewPass(e.target.value)} required/>
                        <button disabled={loading} className="w-full bg-green-600 text-white py-4 rounded-lg font-bold hover:bg-green-700 transition shadow-lg flex justify-center items-center">{loading ? <span className="loader"></span> : 'Şifreyi Güncelle'}</button>
                        <div className="text-center mt-4"><button type="button" onClick={()=>{setView("login"); setErr(""); setSuccess("");}} className="text-sm text-slate-500 hover:text-[#003d82] transition">← Giriş'e Dön</button></div>
                    </form>
                )}
            </div>
        </div>
    );
};

// --- MESAJLAŞMA BİLEŞENİ ---
const Messenger = ({ user, initialTarget = null }) => {
    const [conversations, setConversations] = useState([]);
    const [activeChat, setActiveChat] = useState(initialTarget);
    const [messages, setMessages] = useState([]);
    const [msgText, setMsgText] = useState("");
    const messagesEndRef = useRef(null);

    // Tarih Formatlayıcı
    const parseCustomDate = (dateStr) => {
        if (!dateStr) return new Date(0);
        let d = new Date(dateStr);
        if (!isNaN(d.getTime())) return d;
        try {
            const [datePart, timePart] = dateStr.split(' ');
            const [day, month, year] = datePart.split('.');
            const [hour, minute, second = 0] = timePart.split(':');
            return new Date(year, month - 1, day, hour, minute, second);
        } catch (e) {
            return new Date();
        }
    };

    const fetchData = useCallback(() => {
        api.post('/messages/', { action: 'list', user, role: 'academician' }).then(res => {
            const allMsgs = res.data.map((m, index) => ({ ...m, originalIndex: index }));
            const uniqueUsers = new Set();

            allMsgs.forEach(m => {
                if (m.sender !== user) uniqueUsers.add(m.sender);
                if (m.receiver !== user) uniqueUsers.add(m.receiver);
            });

            // --- Sohbet Listesi ---
            const chatList = Array.from(uniqueUsers).map(u => {
                const userMsgs = allMsgs.filter(m => m.sender === u || m.receiver === u);
                userMsgs.sort((a, b) => {
                    const tA = parseCustomDate(a.timestamp).getTime();
                    const tB = parseCustomDate(b.timestamp).getTime();
                    if (tA !== tB) return tA - tB;
                    return (a.id || 0) - (b.id || 0);
                });
                const lastMsg = userMsgs[userMsgs.length - 1];

                return {
                    name: u,
                    lastMessage: lastMsg ? lastMsg.content : "",
                    timestamp: lastMsg ? lastMsg.timestamp : "",
                };
            });

            if (initialTarget && !chatList.find(c => c.name === initialTarget)) {
                chatList.unshift({ name: initialTarget, lastMessage: "Yeni Sohbet Başlat", timestamp: "" });
            }
            setConversations(chatList);

            // --- Mesaj Akışı ---
            if (activeChat) {
                const chatMsgs = allMsgs.filter(m =>
                    (m.sender === user && m.receiver === activeChat) ||
                    (m.sender === activeChat && m.receiver === user)
                );

                chatMsgs.sort((a, b) => {
                    const timeA = parseCustomDate(a.timestamp).getTime();
                    const timeB = parseCustomDate(b.timestamp).getTime();

                    if (timeA !== timeB) return timeA - timeB;

                    if (a.id && b.id) return a.id - b.id;

                    return b.originalIndex - a.originalIndex;
                });

                setMessages(chatMsgs);
            }
        });
    }, [user, activeChat, initialTarget]);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 3000);
        return () => clearInterval(interval);
    }, [fetchData]);

    useEffect(() => {
        if (messagesEndRef.current) {
            setTimeout(() => {
                messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
            }, 100);
        }
    }, [messages, activeChat]);

    const sendMessage = (e) => {
        e.preventDefault();
        if (!msgText.trim() || !activeChat) return;
        api.post('/messages/', { action: 'send', sender: user, receiver: activeChat, content: msgText })
            .then(() => {
                setMsgText("");
                fetchData();
            });
    };

    const formatDisplayTime = (timestamp) => {
        if (!timestamp) return "";
        try {
            return timestamp.split(' ')[1].substring(0, 5);
        } catch (e) {
            return "";
        }
    };

    return (
        <div className="flex h-[600px] bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm animate-[fadeIn_0.3s]">
            {/* SOL MENÜ */}
            <div className="w-1/3 border-r border-slate-200 flex flex-col bg-white">
                <div className="p-4 bg-slate-50 border-b border-slate-200 font-bold text-slate-700">Sohbetler</div>
                <div className="flex-1 overflow-y-auto">
                    {conversations.length === 0 ? (
                        <div className="p-4 text-center text-slate-400 text-sm">Henüz mesaj yok.</div>
                    ) : (
                        conversations.map((c, i) => (
                            <div key={i} onClick={() => setActiveChat(c.name)} className={`p-4 flex items-center gap-3 cursor-pointer hover:bg-slate-50 transition border-b border-slate-50 ${activeChat === c.name ? 'bg-blue-50 border-l-4 border-l-[#003d82]' : ''}`}>
                                <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-bold text-sm shrink-0">{c.name.charAt(0)}</div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-baseline">
                                        <h4 className="font-bold text-sm text-slate-800 truncate">{c.name}</h4>
                                        <span className="text-[10px] text-slate-400">{formatDisplayTime(c.timestamp)}</span>
                                    </div>
                                    <p className="text-xs text-slate-500 truncate">{c.lastMessage}</p>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* SAĞ SOHBET EKRANI */}
            <div className="flex-1 flex flex-col bg-[#e5ddd5] relative">
                {activeChat ? (
                    <>
                        <div className="p-3 bg-white border-b border-slate-200 flex items-center gap-3 shadow-sm z-10">
                            <div className="w-9 h-9 rounded-full bg-[#003d82] text-white flex items-center justify-center font-bold text-sm">{activeChat.charAt(0)}</div>
                            <div><h3 className="font-bold text-slate-800 text-sm">{activeChat}</h3><p className="text-[10px] text-green-600 font-bold"></p></div>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-2 flex flex-col" style={{backgroundImage: "url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png')"}}>
                            {messages.map((m, i) => {
                                const isMe = m.sender === user;
                                return (
                                    <div key={i} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[70%] px-3 py-2 rounded-lg text-sm shadow-sm relative ${isMe ? 'bg-[#d9fdd3] text-slate-800 rounded-tr-none' : 'bg-white text-slate-800 rounded-tl-none'}`}>
                                            {m.content}
                                            <span className="text-[10px] text-slate-400 block text-right mt-1 -mb-1 select-none">{formatDisplayTime(m.timestamp)}</span>
                                        </div>
                                    </div>
                                );
                            })}
                            <div ref={messagesEndRef} className="h-1" />
                        </div>

                        <form onSubmit={sendMessage} className="p-3 bg-[#f0f2f5] flex items-center gap-2 border-t border-slate-200">
                            <input type="text" className="flex-1 p-3 rounded-lg border-none focus:ring-0 outline-none text-sm bg-white" placeholder="Bir mesaj yazın..." value={msgText} onChange={e => setMsgText(e.target.value)}/>
                            <button type="submit" className="p-3 bg-[#003d82] text-white rounded-lg hover:bg-[#002855] transition shadow-md">➤</button>
                        </form>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-slate-400"><div className="text-6xl mb-4">💬</div><p>Mesajlaşmaya başlayın.</p></div>
                )}
            </div>
        </div>
    );
};

// --- PROFİL EKRANI ---
const AcademicianProfile = ({ name, role, onLogout, onBackAdmin }) => {
    const [tab, setTab] = useState("genel");
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [modalOpen, setModalOpen] = useState(false);
    const [activeAction, setActiveAction] = useState(null);
    const [topProjectsOpen, setTopProjectsOpen] = useState(false);
    const [annOpen, setAnnOpen] = useState(false);
    const [chatTarget, setChatTarget] = useState(null);
    const graphRef = useRef(null);

    useEffect(() => {
        api.post('/profile/', { name }).then(res => { setData(res.data); setLoading(false); });
    }, [name]);

    useEffect(() => {
        if(tab === "ag" && graphRef.current) {
            graphRef.current.innerHTML = "";
            loadNetworkGraph();
        }
    }, [tab]);

    const loadNetworkGraph = () => {
        api.get(`/network-graph/?user=${name}`)
            .then(res => {
                if(!graphRef.current) return;
                const graphData = res.data;
                if(graphData.nodes.length <= 1) {
                    graphRef.current.innerHTML = "<div class='text-center text-slate-500 mt-20 text-lg flex flex-col items-center'><span class='text-4xl mb-4'>🕸️</span>Bu kullanıcı için henüz onaylanmış bir işbirliği bağlantısı bulunmuyor.</div>";
                    return;
                }
                const Graph = ForceGraph()(graphRef.current)
                    .graphData(graphData)
                    .nodeId('id')
                    .width(graphRef.current.clientWidth)
                    .height(600)
                    .backgroundColor('#ffffff')
                    .linkColor(() => '#cbd5e1')
                    .linkWidth(2)
                    .nodeCanvasObject((node, ctx, globalScale) => {
                        const size = node.isCenter ? 30 : 18;
                        const borderColor = node.isCenter ? '#f59e0b' : '#003d82';

                        if (node.img && !node.imgObj) {
                            const img = new Image();
                            let src = node.img;
                            if (!src.startsWith('http')) {
                                const cleanPath = src.startsWith('/') ? src.slice(1) : src;
                                src = `${API_BASE_URL}/${cleanPath}`;
                            }
                            if (src.includes('akademisyen_fotograflari/akademisyen_fotograflari')) {
                                src = src.replace('akademisyen_fotograflari/akademisyen_fotograflari', 'akademisyen_fotograflari');
                            }
                            img.src = src;
                            img.crossOrigin = "Anonymous";
                            node.imgObj = img;
                        }

                        ctx.save();
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
                        ctx.fillStyle = '#fff';
                        ctx.fill();
                        ctx.shadowColor = "rgba(0,0,0,0.2)";
                        ctx.shadowBlur = 6;
                        ctx.clip();
                        if (node.imgObj && node.imgObj.complete && node.imgObj.naturalWidth !== 0) {
                            try { ctx.drawImage(node.imgObj, node.x - size, node.y - size, size * 2, size * 2); }
                            catch (e) { ctx.fillStyle = borderColor; ctx.fill(); }
                        } else {
                            ctx.fillStyle = borderColor; ctx.fill();
                            ctx.fillStyle = '#fff';
                            ctx.font = `bold ${size}px Sans-Serif`;
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'middle';
                            ctx.fillText(node.id.charAt(0), node.x, node.y);
                        }
                        ctx.restore();

                        ctx.beginPath();
                        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
                        ctx.lineWidth = node.isCenter ? 4 : 2;
                        ctx.strokeStyle = borderColor;
                        ctx.stroke();

                        const label = node.id;
                        const fontSize = (node.isCenter ? 14 : 11) / globalScale;
                        ctx.font = `bold ${fontSize}px Sans-Serif`;
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'top';
                        ctx.fillStyle = '#334155';
                        ctx.fillText(label, node.x, node.y + size + 6);
                    });

                    Graph.d3Force('charge').strength(-400);
                    Graph.d3Force('link').distance(150);
            });
    };

    const openDecisionModal = (id, title, type) => { setActiveAction({ id, title, type }); setModalOpen(true); };

    const submitDecision = (note, rating) => {
        const { id, title, type } = activeAction;
        const newProjects = data.projects.map(p => {
            if (p.id === id) return { ...p, decision: type, note: note, rating: rating };
            return p;
        });
        setData({ ...data, projects: newProjects });

        api.post('/decision/', { academician: name, projId: id, projectTitle: title, decision: type, note: note, rating: rating })
           .then(() => console.log("Karar kaydedildi"))
           .catch(err => console.error("Karar kaydedilemedi", err));

        setModalOpen(false);
    };

    const resetDecision = (projId) => {
        const newProjects = data.projects.map(p => { if (p.id === projId) return { ...p, decision: 'waiting', note: '', rating: 0 }; return p; });
        setData({ ...data, projects: newProjects });
    };

    if (loading) return <div className="h-screen flex items-center justify-center bg-slate-50"><div className="loader"></div></div>;

    const { profile, projects } = data;
    const profileImage = profile.Image ? (profile.Image.startsWith('http') ? profile.Image : `${API_BASE_URL}/${profile.Image.replace(/^\//, '')}`) : null;
    const displayTitle = getTitle(profile);

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <header className="profile-header bg-white sticky top-0 z-30 shadow-sm border-b border-slate-200">
                <div className="container mx-auto px-4 py-3 flex justify-between items-center relative">
                    <div className="flex items-center gap-6">
                        <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-slate-200 shadow-sm flex items-center justify-center bg-slate-100 text-2xl relative">
                            {profileImage ? <img src={profileImage} alt={profile.Fullname} className="w-full h-full object-cover"/> : "👤"}
                            <div className="absolute bottom-0 right-0 w-4 h-4 bg-green-500 rounded-full border-2 border-white"></div>
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-slate-800">{profile.Fullname}</h1>
                            <p className="text-[#003d82] font-bold text-sm">{displayTitle}</p>
                        </div>
                    </div>
                    <div className="flex gap-3">
                        <button onClick={() => setTopProjectsOpen(true)} className="bg-orange-50 text-orange-600 border border-orange-200 px-4 py-2 rounded-lg text-sm font-bold shadow-sm hover:bg-orange-100 transition">Top 50</button>
                        <button onClick={() => setAnnOpen(true)} className="bg-white text-[#003d82] border border-[#003d82]/20 px-4 py-2 rounded-lg text-sm font-bold shadow-sm hover:bg-slate-50 transition">Duyurular</button>
                        {role === "admin" && <button onClick={onBackAdmin} className="bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-slate-900 transition">Listeye Dön</button>}
                        <button onClick={onLogout} className="bg-white text-red-600 border border-red-200 px-4 py-2 rounded-lg hover:bg-red-50 text-sm font-bold transition">Çıkış</button>
                    </div>
                </div>
            </header>

            <div className="container mx-auto px-4 py-10 flex flex-col md:flex-row gap-8 flex-1">
                <aside className="w-full md:w-64 flex-shrink-0">
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden sticky top-28">
                        <nav className="flex flex-col">
                            <button onClick={()=>setTab("genel")} className={`p-4 text-left font-medium border-l-4 transition flex items-center gap-2 ${tab==="genel" ? "border-[#003d82] bg-slate-50 text-[#003d82]" : "border-transparent hover:bg-slate-50 text-slate-600"}`}>📝 Genel Bilgiler</button>
                            <button onClick={()=>setTab("proje")} className={`p-4 text-left font-medium border-l-4 transition flex items-center gap-2 ${tab==="proje" ? "border-[#003d82] bg-slate-50 text-[#003d82]" : "border-transparent hover:bg-slate-50 text-slate-600"}`}>🚀 Projeler <span className="ml-auto bg-slate-200 text-slate-700 px-2 rounded-full text-xs">{projects.length}</span></button>
                            <button onClick={()=>setTab("mesajlar")} className={`p-4 text-left font-medium border-l-4 transition flex items-center gap-2 ${tab==="mesajlar" ? "border-[#003d82] bg-slate-50 text-[#003d82]" : "border-transparent hover:bg-slate-50 text-slate-600"}`}>💬 Mesajlar</button>
                            <button onClick={()=>setTab("ag")} className={`p-4 text-left font-medium border-l-4 transition flex items-center gap-2 ${tab==="ag" ? "border-[#003d82] bg-slate-50 text-[#003d82]" : "border-transparent hover:bg-slate-50 text-slate-600"}`}>🕸️ İşbirliği Ağı</button>
                        </nav>
                    </div>
                </aside>

                <main className="flex-1 bg-white rounded-xl shadow-sm border border-slate-200 p-8 min-h-[600px]">
                    {/* --- GENEL BİLGİLER TAB --- */}
                    {tab === "genel" && (
                        <div className="animate-[fadeIn_0.3s]">
                            <h2 className="text-xl font-bold text-slate-800 mb-6 border-b pb-4">Kişisel Bilgiler</h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                                <div className="p-5 bg-slate-50 rounded-xl border border-slate-100 shadow-sm flex flex-col">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Ad Soyad</span>
                                    <span className="text-lg font-medium text-slate-800">{profile.Fullname}</span>
                                </div>
                                <div className="p-5 bg-slate-50 rounded-xl border border-slate-100 shadow-sm flex flex-col">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Ünvan</span>
                                    <span className="text-lg font-medium text-[#003d82]">{displayTitle}</span>
                                </div>
                                <div className="p-5 bg-slate-50 rounded-xl border border-slate-100 shadow-sm flex flex-col">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">E-Posta</span>
                                    <span className="text-lg font-medium text-slate-800 break-all">{profile.Email}</span>
                                </div>
                                <div className="p-5 bg-slate-50 rounded-xl border border-slate-100 shadow-sm flex flex-col">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Birim / Bölüm</span>
                                    <span className="text-lg font-medium text-slate-800">{profile.Field || "Belirtilmemiş"}</span>
                                </div>
                                <div className="p-5 bg-slate-50 rounded-xl border border-slate-100 shadow-sm flex flex-col">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">İş Telefonu</span>
                                    <span className="text-lg font-medium text-slate-800">{profile.Phone || "-"}</span>
                                </div>
                            </div>

                            <h2 className="text-xl font-bold text-slate-800 mb-4 border-b pb-2">Akademik Geçmiş</h2>
                            <div className="overflow-hidden rounded-lg border border-slate-200">
                                <table className="w-full text-left">
                                    <thead className="bg-slate-50 border-b border-slate-200">
                                        <tr>
                                            <th className="p-3 text-xs font-bold text-slate-500 uppercase">Yıl</th>
                                            <th className="p-3 text-xs font-bold text-slate-500 uppercase">Ünvan</th>
                                            <th className="p-3 text-xs font-bold text-slate-500 uppercase">Kurum</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100">
                                        {profile.Duties && profile.Duties.length > 0 ? profile.Duties.map((d, i) => (
                                            <tr key={i} className="hover:bg-slate-50">
                                                <td className="p-3 font-bold text-[#003d82]">{d.Year}</td>
                                                <td className="p-3 font-medium text-slate-700">{d.Title}</td>
                                                <td className="p-3 text-slate-600">{d.University}</td>
                                            </tr>
                                        )) : <tr><td colSpan="3" className="p-4 text-center text-slate-400 italic">Bilgi Bulunamadı.</td></tr>}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* --- PROJELER TAB --- */}
                    {tab === "proje" && (
                        <div className="animate-[fadeIn_0.3s]">
                            <h2 className="text-xl font-bold text-slate-800 mb-6 border-b pb-4 flex justify-between items-center">
                                ÖNERİLEN PROJELER
                                <span className="text-xs font-bold bg-blue-50 text-blue-700 border border-blue-100 px-3 py-1.5 rounded-full">Yapay Zeka Destekli</span>
                            </h2>
                            <div className="space-y-6">
                                {projects.map((p, i) => (
                                    <div key={i} className={`p-6 rounded-xl border transition-all ${p.decision==='accepted'?'border-green-200 bg-green-50/20 shadow-sm':p.decision==='rejected'?'border-red-200 bg-red-50/20 shadow-sm':'border-slate-200 hover:border-[#003d82] hover:shadow-md bg-white'}`}>
                                        <div className="flex flex-col sm:flex-row justify-between items-start gap-4 mb-3">
                                            <h3 className="font-bold text-[#003d82] text-lg leading-tight flex-1">{p.title}</h3>
                                            <span className="bg-slate-800 text-white px-3 py-1 rounded text-sm font-bold shadow-sm flex-shrink-0 ml-auto">%{p.score} Uyum</span>
                                        </div>
                                        <div className="flex flex-wrap gap-2 text-xs font-medium text-slate-500 mb-4">
                                            <span className="bg-white px-2 py-1 rounded border">ID: {p.id}</span>
                                            <span className="bg-white px-2 py-1 rounded border">Bütçe: {p.budget}</span>
                                            <span className="bg-white px-2 py-1 rounded border">Durum: {p.status}</span>
                                        </div>
                                        <div className="text-sm text-slate-600 mb-5 bg-white/50 p-3 rounded border border-transparent hover:border-slate-100 transition leading-relaxed text-justify">{p.objective}</div>

                                        {p.url && p.url !== "#" && (
                                            <div className="mb-4">
                                                <a href={p.url} target="_blank" className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 text-sm font-bold rounded-lg border border-blue-200 hover:bg-blue-100 transition">
                                                    🔗 Proje Detaylarını Görüntüle
                                                </a>
                                            </div>
                                        )}

                                        {p.collaborators && p.collaborators.length > 0 && (
                                            <div className="mb-4 bg-indigo-50 border-l-4 border-indigo-400 p-3 rounded-r">
                                                <p className="text-xs font-bold text-indigo-800 mb-2">Bu projeyi kabul eden diğer hocalar:</p>
                                                <div className="flex flex-wrap gap-2">
                                                    {p.collaborators.map((col, k) => (
                                                        <span key={k} onClick={()=>{setChatTarget(col); setTab("mesajlar");}} className="bg-white text-indigo-700 border border-indigo-200 px-2 py-1 rounded text-xs font-medium cursor-pointer hover:bg-indigo-100 transition shadow-sm">
                                                            ✉️ {col}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        <div className="flex flex-wrap justify-end border-t pt-4 border-slate-100 items-center gap-3">
                                            {p.decision === 'waiting' ? (
                                                <>
                                                    <button onClick={() => openDecisionModal(p.id, p.title, 'accepted')} className="bg-green-600 text-white px-5 py-2 rounded-lg hover:bg-green-700 text-sm font-bold shadow-sm transition transform active:scale-95 flex items-center gap-2"><span>✓</span> Kabul Et</button>
                                                    <button onClick={() => openDecisionModal(p.id, p.title, 'rejected')} className="bg-white text-red-600 border border-red-200 px-5 py-2 rounded-lg hover:bg-red-50 text-sm font-bold transition transform active:scale-95 flex items-center gap-2"><span>✕</span> Reddet</button>
                                                </>
                                            ) : (
                                                <div className="flex items-center gap-4">
                                                    <div className="text-right">
                                                        <span className={`font-bold text-sm block ${p.decision === 'accepted' ? 'text-green-700' : 'text-red-700'}`}>
                                                            {p.decision === 'accepted' ? '✓ KABUL EDİLDİ' : '✕ REDDEDİLDİ'}
                                                        </span>
                                                        {p.rating > 0 && <span className="text-xs text-slate-500 font-medium">Puan: {p.rating}/10</span>}
                                                    </div>
                                                    <button onClick={() => resetDecision(p.id)} className="text-xs text-slate-400 hover:text-blue-600 underline font-medium">Değiştir</button>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* MESAJLAR TAB */}
                    {tab === "mesajlar" && (
                        <div className="animate-[fadeIn_0.3s]">
                            <h2 className="text-xl font-bold text-slate-800 mb-6 border-b pb-4">MESAJLAR</h2>
                            <Messenger user={name} initialTarget={chatTarget} />
                        </div>
                    )}

                    {tab === "ag" && (
                        <div className="h-full flex flex-col animate-[fadeIn_0.3s]">
                            <h2 className="text-xl font-bold text-slate-800 mb-6 border-b pb-4">KİŞİSEL İŞBİRLİĞİ AĞI</h2>
                            <div className="flex-1 bg-white border border-slate-200 rounded-xl overflow-hidden relative shadow-inner" style={{minHeight: '600px'}}>
                                <div ref={graphRef} className="w-full h-full cursor-move"></div>
                                <div className="absolute bottom-4 right-4 bg-white/90 p-4 rounded-lg shadow-lg text-xs text-slate-600 border border-slate-100 backdrop-blur-sm">
                                    <div className="font-bold mb-2 text-slate-800">Lejant</div>
                                    <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#f59e0b]"></span> Siz</div>
                                    <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#003d82]"></span> Ortaklar</div>
                                </div>
                            </div>
                        </div>
                    )}
                </main>
            </div>

            <NoteModal isOpen={modalOpen} onClose={()=>setModalOpen(false)} onSubmit={submitDecision} type={activeAction?.type} />
            {topProjectsOpen && <TopProjectsModal onClose={() => setTopProjectsOpen(false)} />}
            {annOpen && <AnnouncementModal onClose={() => setAnnOpen(false)} />}
        </div>
    );
};

// --- ADMIN DASHBOARD ---
const AdminDashboard = ({ onSelectUser, onLogout }) => {
    const [data, setData] = useState({ academicians: [], feedbacks: [], logs: [], announcements: [] });
    const [search, setSearch] = useState("");
    const [load, setLoad] = useState(true);
    const [viewMode, setViewMode] = useState("list");
    const [topProjectsOpen, setTopProjectsOpen] = useState(false);
    const [annForm, setAnnForm] = useState({ title: "", content: "" });
    const [allMessages, setAllMessages] = useState([]);

    const fetchAdminData = () => {
        setLoad(true);
        api.get('/admin-data/').then(r => {
            if(r.data) setData(r.data);
            setLoad(false);
        });
        if (viewMode === "messages") {
            api.post('/messages/', { action: 'list', role: 'admin' }).then(r => setAllMessages(r.data));
        }
    };

    useEffect(() => { fetchAdminData(); }, [viewMode]);

    const sendAnnouncement = (e) => {
        e.preventDefault();
        api.post('/announcements/', annForm).then(res => {
            if (res.data.status === 'success') {
                alert("Duyuru yayınlandı!");
                setAnnForm({ title: "", content: "" });
                fetchAdminData();
            }
        });
    };

    const filtered = (data.academicians || []).filter(i => i.name.toLowerCase().includes(search.toLowerCase()));

    return (
        <div className="min-h-screen bg-slate-100 font-sans">
            <header className="bg-[#003d82] text-white p-4 shadow flex justify-between items-center sticky top-0 z-20">
                <div className="font-bold flex items-center gap-2 text-lg"><img src={`${API_BASE_URL}/images/logo-tek.png`} className="h-9 bg-white rounded-full p-0.5" /> Yönetici Paneli</div>
                <div className="flex gap-2">
                    <button onClick={() => setTopProjectsOpen(true)} className="text-sm bg-orange-500 text-white px-3 py-2 rounded-lg hover:bg-orange-600 font-bold mr-2 shadow-sm flex items-center gap-1">Top 50</button>
                    <button onClick={() => setViewMode("list")} className={`text-sm px-4 py-2 rounded-lg font-medium transition ${viewMode === "list" ? "bg-white text-[#003d82] shadow" : "hover:bg-white/10"}`}>Akademisyenler</button>
                    <button onClick={() => setViewMode("feedbacks")} className={`text-sm px-4 py-2 rounded-lg font-medium transition ${viewMode === "feedbacks" ? "bg-white text-[#003d82] shadow" : "hover:bg-white/10"}`}>
                        Geri Bildirimler <span className="ml-1 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">{data.feedbacks ? data.feedbacks.length : 0}</span>
                    </button>
                    <button onClick={() => setViewMode("logs")} className={`text-sm px-4 py-2 rounded-lg font-medium transition ${viewMode === "logs" ? "bg-white text-[#003d82] shadow" : "hover:bg-white/10"}`}>Kayıtlar</button>
                    <button onClick={() => setViewMode("announcements")} className={`text-sm px-4 py-2 rounded-lg font-medium transition ${viewMode === "announcements" ? "bg-white text-[#003d82] shadow" : "hover:bg-white/10"}`}>Duyurular</button>
                    <button onClick={() => setViewMode("messages")} className={`text-sm px-4 py-2 rounded-lg font-medium transition ${viewMode === "messages" ? "bg-white text-[#003d82] shadow" : "hover:bg-white/10"}`}>Mesajlar</button>
                    <button onClick={onLogout} className="text-sm bg-red-600 px-4 py-2 rounded-lg hover:bg-red-700 ml-4 font-bold shadow-md">Çıkış</button>
                </div>
            </header>

            <div className="container mx-auto p-6 max-w-7xl">
                {viewMode === "list" && (
                    <>
                        <div className="mb-8 sticky top-20 z-10 pt-4 bg-slate-100 pb-2">
                            <input type="text" placeholder="Akademisyen ara..." className="w-full p-4 pl-6 rounded-full border border-slate-200 shadow-lg outline-none focus:ring-4 focus:ring-[#003d82]/20 text-lg transition text-slate-700" onChange={e => setSearch(e.target.value)} />
                        </div>
                        {load ? <div className="text-center mt-20"><div className="loader"></div></div> : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {filtered.map((item, i) => (
                                    <div key={i} onClick={() => onSelectUser(item.name)} className="bg-white p-6 rounded-xl shadow-sm border border-transparent hover:border-[#003d82] cursor-pointer transition group hover:shadow-xl transform hover:-translate-y-1">
                                        <div className="flex items-center gap-5">
                                            <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center text-2xl group-hover:bg-[#003d82] group-hover:text-white transition shadow-inner overflow-hidden border-2 border-white ring-2 ring-slate-100">
                                                {item.image ? <img src={`${API_BASE_URL}/${item.image}`} className="w-full h-full object-cover" /> : "👤"}
                                            </div>
                                            <div className="overflow-hidden">
                                                <h3 className="font-bold text-slate-800 truncate group-hover:text-[#003d82] text-lg">{item.name}</h3>
                                                <p className="text-xs text-slate-500 truncate">{item.email}</p>
                                            </div>
                                        </div>
                                        <div className="mt-5 flex justify-between items-center text-sm text-gray-500 border-t pt-4">
                                            <span className="font-medium bg-slate-50 px-2 py-1 rounded">{item.project_count} Proje</span>
                                            <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full font-bold border border-green-200">En iyi: %{item.best_score}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </>
                )}

                {viewMode === "feedbacks" && (
                    <div className="bg-white rounded-xl shadow-md p-8 border border-slate-200 animate-[fadeIn_0.3s]">
                        <h2 className="text-2xl font-bold mb-6 text-slate-800 border-b pb-4">Akademisyen Geri Bildirimleri</h2>
                        <div className="overflow-x-auto rounded-lg border border-slate-200">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-slate-100 text-slate-600 text-xs uppercase tracking-wider">
                                        <th className="p-4 border-b font-bold">Akademisyen</th>
                                        <th className="p-4 border-b font-bold">Proje ID</th>
                                        <th className="p-4 border-b font-bold">Karar</th>
                                        <th className="p-4 border-b font-bold">Puan</th>
                                        <th className="p-4 border-b font-bold">Açıklama</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.feedbacks && data.feedbacks.map((fb, idx) => (
                                        <tr key={idx} className="hover:bg-slate-50 text-sm transition border-b last:border-0 border-slate-100">
                                            <td className="p-4 font-bold text-slate-700">{fb.academician}</td>
                                            <td className="p-4 font-mono text-xs text-slate-500">{fb.projId}</td>
                                            <td className="p-4"><span className={`px-3 py-1 rounded-full text-xs font-bold border ${fb.decision === 'accepted' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{fb.decision}</span></td>
                                            <td className="p-4 font-bold text-blue-600">{fb.rating || '-'}</td>
                                            <td className="p-4 text-slate-600 italic">{fb.note || "-"}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {viewMode === "logs" && (
                    <div className="bg-white rounded-xl shadow-md p-8 border border-slate-200 animate-[fadeIn_0.3s]">
                        <h2 className="text-2xl font-bold mb-6 text-slate-800 border-b pb-4">Sistem Erişim Kayıtları</h2>
                        <div className="overflow-x-auto rounded-lg border border-slate-200">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-slate-100 text-slate-600 text-xs uppercase tracking-wider">
                                        <th className="p-4 border-b font-bold">Saat</th>
                                        <th className="p-4 border-b font-bold">Kullanıcı</th>
                                        <th className="p-4 border-b font-bold">Rol</th>
                                        <th className="p-4 border-b font-bold">İşlem</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.logs && data.logs.map((log, idx) => (
                                        <tr key={idx} className="hover:bg-slate-50 text-sm transition border-b last:border-0 border-slate-100">
                                            <td className="p-4 text-slate-500 font-mono text-xs">{log.timestamp}</td>
                                            <td className="p-4 font-bold text-slate-700">{log.name}</td>
                                            <td className="p-4"><span className="bg-slate-100 text-slate-600 px-2 py-1 rounded text-xs border">{log.role}</span></td>
                                            <td className="p-4"><span className={`px-2 py-1 rounded text-xs font-bold ${log.action.includes('Giriş') ? 'text-green-700 bg-green-50' : 'text-red-700 bg-red-50'}`}>{log.action}</span></td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {viewMode === "announcements" && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 animate-[fadeIn_0.3s]">
                        <div className="bg-white rounded-xl shadow-md p-8 border border-slate-200 h-fit">
                            <h2 className="text-2xl font-bold mb-6 text-slate-800 border-b pb-4">Yeni Duyuru Ekle</h2>
                            <form onSubmit={sendAnnouncement} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 mb-1">Duyuru Başlığı</label>
                                    <input type="text" required className="w-full p-3 border border-slate-300 rounded outline-none focus:ring-2 focus:ring-[#003d82]"
                                        value={annForm.title} onChange={e=>setAnnForm({...annForm, title:e.target.value})} />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 mb-1">İçerik</label>
                                    <textarea required className="w-full p-3 border border-slate-300 rounded outline-none focus:ring-2 focus:ring-[#003d82] min-h-[150px]"
                                        value={annForm.content} onChange={e=>setAnnForm({...annForm, content:e.target.value})}></textarea>
                                </div>
                                <button type="submit" className="w-full bg-green-600 text-white py-3 rounded font-bold hover:bg-green-700 transition">Yayınla</button>
                            </form>
                        </div>
                        <div className="bg-white rounded-xl shadow-md p-8 border border-slate-200">
                            <h2 className="text-2xl font-bold mb-6 text-slate-800 border-b pb-4">Aktif Duyurular</h2>
                            <div className="space-y-4 max-h-[500px] overflow-y-auto">
                                {data.announcements && data.announcements.length > 0 ? data.announcements.map((ann, i) => (
                                    <div key={i} className="bg-slate-50 p-4 rounded border border-slate-200">
                                        <div className="flex justify-between items-start mb-2">
                                            <h3 className="font-bold text-[#003d82]">{ann.title}</h3>
                                            <button onClick={() => { if(confirm("Bu duyuruyu silmek istediğinize emin misiniz?")) { api.post('/announcements/', { action: 'delete', index: i }).then(() => fetchAdminData()); } }} className="text-red-500 text-xs font-bold hover:text-red-700 hover:bg-red-50 px-2 py-1 rounded transition">Sil 🗑️</button>
                                        </div>
                                        <p className="text-sm text-slate-600 mt-1 whitespace-pre-line">{ann.content}</p>
                                        <div className="text-xs text-slate-400 mt-2 text-right">{ann.date}</div>
                                    </div>
                                )) : <p className="text-slate-500 italic">Henüz duyuru eklenmemiş.</p>}
                            </div>
                        </div>
                    </div>
                )}

                {viewMode === "messages" && (
                    <div className="bg-white rounded-xl shadow-md p-8 border border-slate-200 animate-[fadeIn_0.3s]">
                        <h2 className="text-2xl font-bold mb-6 text-slate-800 border-b pb-4">Tüm Mesaj Trafiği</h2>
                        <div className="space-y-3">
                            {allMessages.map((m, i) => (
                                <div key={i} className="p-3 border-b border-slate-100 hover:bg-slate-50">
                                    <div className="flex justify-between text-xs text-slate-500 mb-1">
                                        <span className="font-bold text-[#003d82]">{m.sender} ➝ {m.receiver}</span>
                                        <span>{m.timestamp}</span>
                                    </div>
                                    <div className="text-sm text-slate-700">{m.content}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
            {topProjectsOpen && <TopProjectsModal onClose={() => setTopProjectsOpen(false)} />}
        </div>
    );
};

// --- ANA UYGULAMA ---
function App() {
    const [user, setUser] = useState(null);

    const onLogin = (role, name) => { setUser({ role, name }); };
    const onLogout = () => {
        if (user) api.post('/logout/', { name: user.name, role: user.role });
        setUser(null);
    };

    if (!user) return <LoginPage onLogin={onLogin} />;
    if (user.role === "admin") {
        if (user.viewingProfile) return <AcademicianProfile name={user.viewingProfile} role="admin" onLogout={onLogout} onBackAdmin={() => setUser({ ...user, viewingProfile: null })} />;
        return <AdminDashboard onSelectUser={(name) => setUser({ ...user, viewingProfile: name })} onLogout={onLogout} />;
    }
    return <AcademicianProfile name={user.name} role="academician" onLogout={onLogout} />;
}

export default App;