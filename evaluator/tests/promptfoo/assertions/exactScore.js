function coerceOutput(ctx) {
  if (!ctx) return null;
  if (typeof ctx === 'string') return ctx;
  const candidates = [
    ctx.output,
    ctx.outputText,
    ctx.text,
    ctx.completion,
    ctx.message && ctx.message.content,
    ctx.response && (ctx.response.outputText || ctx.response.text || ctx.response.completion),
    ctx.result && (ctx.result.outputText || ctx.result.text || ctx.result.completion || ctx.result.output),
    ctx.raw,
  ];
  if (ctx && typeof ctx === 'object') {
    for (const [, v] of Object.entries(ctx)) {
      if (typeof v === 'string') candidates.push(v);
    }
  }
  for (const v of candidates) {
    if (typeof v === 'string') {
      const t = v.trim();
      if (t.startsWith('{') && t.endsWith('}')) return t;
      if (t.includes('{') && t.includes('}')) return t;
    }
  }
  for (const v of candidates) {
    if (typeof v !== 'undefined' && v !== null) return v;
  }
  return null;
}

module.exports = async (output, context) => {
  const { validateExactScore } = require('../validators.js');
  const hasSeparateArgs = arguments.length >= 2;
  const effOutput =
    typeof output !== 'undefined' && output !== null && hasSeparateArgs
      ? output
      : coerceOutput(hasSeparateArgs ? context : output);
  const ctx = hasSeparateArgs ? context : (typeof output === 'object' ? output : null);
  if (effOutput == null) {
    return false;
  }
  const res = await validateExactScore({ output: effOutput, vars: ctx && ctx.vars, context: ctx });
  if (res && res.pass) return true;
  // Provide GradingResult with numeric score and reason so Promptfoo displays details
  const actual = res && typeof res.actual === 'number' ? res.actual : null;
  const score = actual != null ? Math.max(0, Math.min(1, actual / 100)) : 0;
  const reason = (res && res.reason) || 'exact-score failed';
  return { pass: false, score, reason };
};
