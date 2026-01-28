import React, { useEffect, useRef, useState } from 'react';
import ForceGraph from 'force-graph';
import api, { API_BASE_URL } from '../api';

const NetworkGraph = ({ user }) => {
    const containerRef = useRef(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (containerRef.current) containerRef.current.innerHTML = "";
        
        api.get(`/network-graph/?user=${user}`)
            .then(res => {
                setLoading(false);
                const graphData = res.data;

                if (!graphData.nodes || graphData.nodes.length <= 1) {
                    if (containerRef.current) containerRef.current.innerHTML = "<div class='text-center text-slate-500 mt-20 text-lg'>Henüz bir eşleşme bulunmuyor.</div>";
                    return;
                }

                const width = containerRef.current.clientWidth;
                const height = 600;

                const Graph = ForceGraph()(containerRef.current)
                    .graphData(graphData)
                    .nodeId('id')
                    .width(width)
                    .height(height)
                    .backgroundColor('#ffffff')
                    .linkColor(() => '#bfdbfe')
                    .linkWidth(2)
                    .nodeCanvasObject((node, ctx, globalScale) => {
                        const size = node.isCenter ? 30 : 18;
                        const borderColor = node.isCenter ? '#f59e0b' : '#003d82';

                        // Resim Yolu Düzeltme
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

                        // Gölge
                        ctx.save();
                        ctx.shadowColor = "rgba(0,0,0,0.2)";
                        ctx.shadowBlur = 6;
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
                        ctx.fillStyle = '#fff';
                        ctx.fill();
                        ctx.restore();

                        // Resim Kırpma
                        ctx.save();
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
                        ctx.clip();

                        if (node.imgObj && node.imgObj.complete && node.imgObj.naturalWidth !== 0) {
                            try { ctx.drawImage(node.imgObj, node.x - size, node.y - size, size * 2, size * 2); } 
                            catch (e) { ctx.fillStyle = borderColor; ctx.fill(); }
                        } else {
                            ctx.fillStyle = borderColor; ctx.fill();
                        }
                        ctx.restore();

                        // Çerçeve
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
                        ctx.lineWidth = node.isCenter ? 4 : 2.5;
                        ctx.strokeStyle = borderColor;
                        ctx.stroke();

                        // İsim
                        const label = node.id;
                        const fontSize = (node.isCenter ? 14 : 11) / globalScale;
                        ctx.font = `bold ${fontSize}px Sans-Serif`;
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'top';
                        ctx.fillStyle = '#1e293b';
                        ctx.fillText(label, node.x, node.y + size + 4);
                    });

                Graph.d3Force('charge').strength(-400);
                Graph.d3Force('link').distance(120);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
                setError("Veri alınamadı.");
            });
    }, [user]);

    return (
        <div className="flex-1 bg-slate-50 border border-slate-200 rounded-xl overflow-hidden relative" style={{minHeight: '600px'}}>
            {loading && <div className="absolute inset-0 flex items-center justify-center"><div className="loader"></div></div>}
            {error && <div className="text-red-500 text-center p-10 font-bold">{error}</div>}
            <div ref={containerRef} className="w-full h-full cursor-move"></div>
            
            <div className="absolute bottom-4 right-4 bg-white/95 p-3 rounded-lg shadow text-xs text-slate-700 border border-slate-200">
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-[#f59e0b] border border-[#f59e0b]"></span> Siz (Merkez)</div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-[#003d82] border border-[#003d82]"></span> Proje Ortaklarınız</div>
            </div>
        </div>
    );
};

export default NetworkGraph;