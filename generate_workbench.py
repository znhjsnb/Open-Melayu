"""
Generate a beautiful standalone HTML viewer for the 20 enriched Open-Melayu words.
"""
import os
import json

ENRICHED_DIR = r"c:\Users\d\Documents\open-melayu\data\enriched"
HTML_PATH = r"c:\Users\d\Documents\open-melayu\词典预览工作台.html"

words_data = []
for fname in sorted(os.listdir(ENRICHED_DIR)):
    if fname.startswith("batch_") or not fname.endswith(".json"):
        continue
    fpath = os.path.join(ENRICHED_DIR, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        words_data.append(json.load(f))

# Sort by frequency rank
words_data.sort(key=lambda x: x.get('headword', {}).get('frequency_rank', 999))

html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Open-Melayu 词典成品验收工作台 (前 20 词预览)</title>
    <style>
        :root {{
            --primary: #0284c7;
            --primary-dark: #0369a1;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-sub: #475569;
            --border: #e2e8f0;
            --badge-bg: #f1f5f9;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }}
        /* Sidebar */
        .sidebar {{
            width: 320px;
            background: #ffffff;
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }}
        .sidebar-header {{
            padding: 20px;
            border-bottom: 1px solid var(--border);
            background: #ffffff;
        }}
        .sidebar-header h1 {{
            font-size: 18px;
            font-weight: 700;
            color: #0369a1;
            margin-bottom: 4px;
        }}
        .sidebar-header p {{
            font-size: 12px;
            color: var(--text-sub);
        }}
        .word-list {{
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }}
        .word-item {{
            padding: 12px 16px;
            margin-bottom: 6px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid transparent;
        }}
        .word-item:hover {{
            background: #f1f5f9;
        }}
        .word-item.active {{
            background: #e0f2fe;
            border-color: #bae6fd;
            color: #0369a1;
            font-weight: 600;
        }}
        .word-item .rank {{
            font-size: 11px;
            padding: 2px 6px;
            background: var(--badge-bg);
            border-radius: 4px;
            color: var(--text-sub);
        }}
        .word-item.active .rank {{
            background: #bae6fd;
            color: #0369a1;
        }}
        /* Main View */
        .main-content {{
            flex: 1;
            overflow-y: auto;
            padding: 30px 40px;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            max-width: 900px;
            margin: 0 auto;
        }}
        .word-header {{
            display: flex;
            align-items: baseline;
            gap: 16px;
            border-bottom: 2px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        .word-title {{
            font-size: 36px;
            font-weight: 800;
            color: var(--primary-dark);
        }}
        .word-jawi {{
            font-size: 32px;
            font-family: "Traditional Arabic", "Scheherazade", serif;
            direction: rtl;
            color: #b45309;
        }}
        .word-meta {{
            font-size: 15px;
            color: var(--text-sub);
            font-family: monospace;
        }}
        .audio-pill {{
            background: #f0fdf4;
            color: #15803d;
            border: 1px solid #bbf7d0;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 13px;
            cursor: pointer;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }}
        .audio-pill:hover {{
            background: #dcfce7;
        }}
        /* Sections */
        .section {{
            margin-bottom: 26px;
        }}
        .section-title {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            font-weight: 700;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .formula-box {{
            background: #f8fafc;
            border-left: 4px solid var(--primary);
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            font-family: monospace;
            font-size: 15px;
            color: #0f172a;
        }}
        .sense-box {{
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        .sense-pos {{
            display: inline-block;
            background: #e0e7ff;
            color: #4338ca;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .sense-zh {{ font-size: 16px; font-weight: 600; color: #1e293b; margin-bottom: 4px; }}
        .sense-en {{ font-size: 14px; color: #475569; margin-bottom: 4px; }}
        .sense-ms {{ font-size: 13px; color: #64748b; font-style: italic; margin-bottom: 8px; }}
        .sense-nuance {{ font-size: 13px; color: #b45309; background: #fef3c7; padding: 6px 10px; border-radius: 6px; }}
        
        .scenario-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }}
        .scenario-card {{
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            background: #fafafa;
        }}
        .scenario-badge {{
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 700;
            text-transform: uppercase;
            display: inline-block;
            margin-bottom: 8px;
        }}
        .badge-formal {{ background: #e0f2fe; color: #0284c7; }}
        .badge-colloquial {{ background: #fef08a; color: #854d0e; }}
        .scenario-text {{ font-size: 14px; margin-bottom: 6px; line-height: 1.5; }}
        .scenario-zh {{ font-size: 13px; color: #475569; }}
        .spoken-notes {{ font-size: 12px; color: #854d0e; margin-top: 8px; padding-top: 8px; border-top: 1px dashed #fde047; }}
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h1>Open-Melayu 词典验收</h1>
            <p>已生成展示 20 个完整 7 维认知词条</p>
        </div>
        <div class="word-list" id="wordList"></div>
    </div>
    <div class="main-content">
        <div class="card" id="cardView">
            <p style="color: #64748b;">请在左侧选择一个词条查看详细 7 维认知 Schema...</p>
        </div>
    </div>

    <script>
        const wordsData = {json.dumps(words_data, ensure_ascii=False)};
        const wordList = document.getElementById('wordList');
        const cardView = document.getElementById('cardView');

        function renderList() {{
            wordList.innerHTML = '';
            wordsData.forEach((item, index) => {{
                const div = document.createElement('div');
                div.className = 'word-item' + (index === 0 ? ' active' : '');
                div.innerHTML = `
                    <span><strong>${{item.headword.word}}</strong> <span style="font-family: Traditional Arabic; color: #b45309; margin-left: 6px;">${{item.headword.jawi || ''}}</span></span>
                    <span class="rank">#${{item.headword.frequency_rank}}</span>
                `;
                div.onclick = () => {{
                    document.querySelectorAll('.word-item').forEach(el => el.classList.remove('active'));
                    div.classList.add('active');
                    renderCard(item);
                }};
                wordList.appendChild(div);
            }});
            if (wordsData.length > 0) {{
                renderCard(wordsData[0]);
            }}
        }}

        function speak(text) {{
            if ('speechSynthesis' in window) {{
                const u = new SpeechSynthesisUtterance(text);
                u.lang = 'ms-MY';
                window.speechSynthesis.speak(u);
            }} else {{
                alert('您的浏览器不支持语音合成');
            }}
        }}

        function renderCard(item) {{
            const h = item.headword || {{}};
            const m = item.morphology || {{}};
            const senses = item.senses || [];
            const dual = item.dual_scenarios || [];
            const shortcuts = item.spoken_shortcuts || [];
            const cult = item.cultural_pragmatics || {{}};
            const etym = item.etymology || {{}};

            let sensesHtml = senses.map(s => `
                <div class="sense-box">
                    <div class="sense-pos">${{s.pos || 'n'}}</div>
                    <div class="sense-zh">${{s.zh_definition || ''}}</div>
                    <div class="sense-en">${{s.en_definition || ''}}</div>
                    <div class="sense-ms">${{s.ms_definition || ''}}</div>
                    ${{s.nuances ? `<div class="sense-nuance">💡 辨析：${{s.nuances}}</div>` : ''}}
                </div>
            `).join('');

            let scenariosHtml = '';
            if (dual.length > 0) {{
                scenariosHtml = '<div class="scenario-grid">';
                dual.forEach(sc => {{
                    const isFormal = sc.scenario === 'formal';
                    scenariosHtml += `
                        <div class="scenario-card">
                            <span class="scenario-badge ${{isFormal ? 'badge-formal' : 'badge-colloquial'}}">
                                ${{isFormal ? '🏛️ 规范书面 / Berita Harian' : '💬 真实口语 / WhatsApp'}}
                            </span>
                            <div class="scenario-text"><strong>${{sc.ms || sc.ms_spoken || ''}}</strong></div>
                            ${{sc.ms_standard ? `<div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">规范对齐：${{sc.ms_standard}}</div>` : ''}}
                            <div class="scenario-zh">${{sc.zh || ''}}</div>
                            ${{sc.spoken_features ? `<div class="spoken-notes">口语特征：${{sc.spoken_features.join('； ')}}</div>` : ''}}
                        </div>
                    `;
                }});
                scenariosHtml += '</div>';
            }}

            cardView.innerHTML = `
                <div class="word-header">
                    <div class="word-title">${{h.word}}</div>
                    <div class="word-jawi">${{h.jawi || ''}}</div>
                    <div class="word-meta">[${{h.syllables || ''}}] &nbsp; ${{h.ipa || ''}}</div>
                    <button class="audio-pill" onclick="speak('${{h.word}}')">🔊 发音</button>
                    <span style="margin-left: auto; font-size: 13px; color: #64748b;">语料频次 #${{h.frequency_rank}}</span>
                </div>

                <div class="section">
                    <div class="section-title">📐 词形形态学与词根演化</div>
                    <div class="formula-box">${{m.formula || '∅'}}</div>
                    ${{m.pattern_note ? `<p style="font-size: 13px; color: #64748b; margin-top: 6px;">${{m.pattern_note}}</p>` : ''}}
                </div>

                <div class="section">
                    <div class="section-title">📖 三语对齐义项 (${{senses.length}})</div>
                    ${{sensesHtml}}
                </div>

                <div class="section">
                    <div class="section-title">🎭 双场景实景对白与口语缩写</div>
                    ${{scenariosHtml}}
                </div>

                <div class="section">
                    <div class="section-title">🤝 文化交际与礼貌语级</div>
                    <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 14px; font-size: 14px; line-height: 1.6;">
                        <p><strong>语体语域：</strong>${{cult.register || '通用'}}</p>
                        <p><strong>礼貌等级：</strong>${{cult.politeness_level || '标准'}}</p>
                        ${{cult.social_rules ? `<p style="color: #b45309; margin-top: 6px;">⚠️ <strong>交际禁忌：</strong>${{cult.social_rules}}</p>` : ''}}
                    </div>
                </div>

                <div class="section">
                    <div class="section-title">🌱 词源溯源与记忆钩子</div>
                    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 14px; font-size: 14px;">
                        <p><strong>语言来源：</strong>${{etym.origin || '马来原生词'}}</p>
                        <p><strong>同源对照：</strong>${{etym.cognates || '无'}}</p>
                        <p style="color: #15803d; margin-top: 6px;">🧠 <strong>记忆助记：</strong>${{etym.memory_hook || ''}}</p>
                    </div>
                </div>
            `;
        }}

        renderList();
    </script>
</body>
</html>
"""

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"Generated visual workbench with {len(words_data)} words at: {HTML_PATH}")
