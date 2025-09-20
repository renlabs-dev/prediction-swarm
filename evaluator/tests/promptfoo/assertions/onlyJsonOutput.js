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
  // Also scan top-level string fields as a last resort
  if (ctx && typeof ctx === 'object') {
    for (const [, v] of Object.entries(ctx)) {
      if (typeof v === 'string') candidates.push(v);
    }
  }
  // Prefer any string that looks like it contains JSON braces
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

// Promptfoo passes (output, context). Keep backward compatibility if only one arg is provided.
module.exports = async (output, context) => {
  const { validateOnlyJsonOutput } = require('../validators.js');
  // If called with single-arg style, treat that as context and try to coerce
  const hasSeparateArgs = arguments.length >= 2;
  const effOutput =
    typeof output !== 'undefined' && output !== null && hasSeparateArgs
      ? output
      : coerceOutput(hasSeparateArgs ? context : output);
  const ctx = hasSeparateArgs ? context : (typeof output === 'object' ? output : null);
  if (effOutput == null) {
    return false;
  }
  const res = await validateOnlyJsonOutput({ output: effOutput, vars: ctx && ctx.vars, context: ctx });
  if (res && res.pass) return true;
  return false;
};
