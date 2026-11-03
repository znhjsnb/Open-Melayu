const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[c]);
const markdown = value => escapeHtml(value).replace(/([\\`*_[\]#|])/g, '\\$1');

export function quoteLabel(head, sense) {
  return head.status === 'official' ? (sense.ms_is_verbatim === true ? 'DBP 原文:' : '马来语释义 (基于 DBP 官方词条):') : (head.status === 'root_derived' ? '马来语释义 (基于 DBP 词根推导):' : '马来语释义 (字幕高频语料用法):');
}

// Export from the data model so language/display preferences never remove content.
export function formatEntryMarkdown(entry) {
  const head = entry.headword || {};
  const morph = entry.morphology || {};
  const lines = [`# ${markdown(head.word || entry.word)}`, '',
    [head.jawi, head.ipa, head.syllables].filter(Boolean).map(markdown).join(' · '),
    `词频 #${markdown(entry.id)} · ${markdown(entry.data_state || '')}`, '', '## 构词',
    [morph.root_word, morph.root_jawi, morph.formula, morph.pattern_note].filter(Boolean).map(markdown).join(' · '),
    ...(morph.word_family || []).map(f => `- ${markdown(f.word)}: ${markdown(f.gloss)}`), '', '## 释义与搭配'];
  for (const sense of entry.senses || []) {
    lines.push(`### ${markdown(sense.id)}. ${markdown(sense.pos)} · ${markdown(sense.zh_definition)}`,
      markdown(sense.en_definition), `> ${quoteLabel(head, sense)} ${markdown(sense.ms_definition)}`, markdown(sense.nuances || sense.nuance_note || sense.nuance));
    for (const c of sense.collocations || []) lines.push(`- ${markdown(c.ms)} — ${markdown(c.zh)} — ${markdown(c.en)}`);
  }
  lines.push('', '## 双境语料');
  for (const sc of entry.dual_scenarios || []) {
    lines.push(`### ${markdown(sc.scenario || sc.type || sc.register || '')} · ${markdown(sc.context)}`,
      ...[sc.ms, sc.ms_spoken, sc.ms_standard, sc.zh, sc.en].filter(Boolean).map(markdown));
    for (const m of sc.messages || []) lines.push(`- ${markdown(m.speaker)}: ${markdown(m.ms_spoken)} / ${markdown(m.ms_standard)} / ${markdown(m.zh)} / ${markdown(m.en)}`);
    if (sc.spoken_features?.length) lines.push(`口语特征: ${sc.spoken_features.map(markdown).join('；')}`);
  }
  lines.push('', '## 口语速查', ...(entry.spoken_shortcuts || []).map(s => `- ${markdown(s.abbr)} → ${markdown(s.full_form)}: ${markdown(s.note)}`));
  const prag = entry.cultural_pragmatics || entry.sociolinguistic_register || {};
  lines.push('', '## 社交礼仪', ...Object.values(prag).map(v => markdown(Array.isArray(v) ? v.join('；') : v)));
  lines.push('', '## 词源与记忆', ...Object.values(entry.etymology || {}).map(markdown));
  return lines.filter(line => line !== undefined).join('\n');
}

export function formatEntryAnkiTsv(entry) {
  const clean = text => String(text ?? '').replace(/[\t\r\n]+/g, ' ').trim();
  const front = escapeHtml(clean(entry.headword?.word || entry.word));
  // Escape the complete text before introducing our own safe HTML line breaks.
  const back = formatEntryMarkdown(entry).split(/\r?\n/).map(clean).join('<br>');
  return `${front}\t${back}`;
}
