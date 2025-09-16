/* Promptfoo validators for evaluator JSON outputs */

function parseOutput(output) {
  // output may be a string or already-parsed object
  if (output == null) return { err: 'No output' };
  if (typeof output === 'object') return { json: output };
  const text = String(output).trim();
  
  // 1) Try direct JSON parse first
  try {
    return { json: JSON.parse(text) };
  } catch (_) {
    // ignore and try extraction below
  }

  // 2) Try to extract JSON inside a fenced code block ```json ... ```
  const fenceMatch = text.match(/```json\s*([\s\S]*?)```/i);
  if (fenceMatch) {
    const inner = fenceMatch[1].trim();
    try {
      return { json: JSON.parse(inner) };
    } catch (_) {}
  }

  // 3) Fallback: attempt to parse the largest braced block
  const first = text.indexOf('{');
  const last = text.lastIndexOf('}');
  if (first !== -1 && last !== -1 && last > first) {
    const candidate = text.slice(first, last + 1).trim();
    try {
      return { json: JSON.parse(candidate) };
    } catch (_) {}
  }

  return { err: 'Output is not valid JSON (could not extract)' };
}

function isInt(n) {
  return Number.isInteger(n);
}

// Helpers for the new structured shape
function isStructured(obj) {
  return (
    obj &&
    typeof obj === 'object' &&
    typeof obj.valid === 'boolean' &&
    obj.scores && typeof obj.scores === 'object' &&
    Object.prototype.hasOwnProperty.call(obj, 'brief_rationale')
  );
}

const SCORE_KEYS = [
  'consequentiality',
  'actionability',
  'foresightedness',
  'resolution_clarity',
  'verifiability',
  'conviction',
  'temporal_horizon',
];

function averageScore(scores) {
  const vals = SCORE_KEYS
    .map((k) => scores[k])
    .filter((v) => typeof v === 'number' && isInt(v));
  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

// 1) JSON shape for structured output
async function validateJsonShape({ output }) {
  const { json, err } = parseOutput(output);
  if (err) return { pass: false, reason: err };

  if (!isStructured(json)) {
    return { pass: false, reason: 'Missing required fields: valid, scores, brief_rationale' };
  }

  // Check scores object has required keys
  for (const key of SCORE_KEYS) {
    if (!Object.prototype.hasOwnProperty.call(json.scores, key)) {
      return { pass: false, reason: `scores.${key} is missing` };
    }
  }

  // brief_rationale is required as a string for both valid=true and valid=false
  if (typeof json.brief_rationale !== 'string') {
    return { pass: false, reason: 'brief_rationale must be a string for both valid=true and valid=false' };
  }

  return { pass: true };
}

// 2) Score type sanity: if valid, all present scores are ints 0-100; if invalid, all are null
async function validateScoreType({ output }) {
  const { json, err } = parseOutput(output);
  if (err) return { pass: false, reason: err };
  if (!isStructured(json)) {
    return { pass: false, reason: 'Output does not match required structured format' };
  }
  const { valid, scores } = json;
  for (const key of SCORE_KEYS) {
    const v = scores[key];
    if (valid) {
      if (typeof v !== 'number' || !isInt(v) || v < 0 || v > 100) {
        return { pass: false, reason: `scores.${key} must be an integer in [0,100] when valid=true` };
      }
    } else {
      if (v !== null) {
        return { pass: false, reason: `scores.${key} must be null when valid=false` };
      }
    }
  }
  return { pass: true };
}

// 3) Trivial cases must be INVALID
async function validateTrivialInvalid({ output, vars }) {
  const { json, err } = parseOutput(output);
  if (err) return { pass: false, reason: err };
  if (vars && vars.kind && vars.kind !== 'trivial') {
    // If misused, don’t fail the run — only enforce when kind=trivial
    return { pass: true };
  }
  if (!isStructured(json)) {
    return { pass: false, reason: 'Output does not match required structured format' };
  }
  return { pass: json.valid === false, reason: json.valid !== false ? 'Trivial case must be invalid (valid=false)' : undefined };
}

// 4) Vague cases must be INVALID or <= 30
async function validateVagueLowOrInvalid({ output, vars }) {
  const { json, err } = parseOutput(output);
  if (err) return { pass: false, reason: err };
  if (vars && vars.kind && vars.kind !== 'vague') {
    return { pass: true };
  }
  if (!isStructured(json)) {
    return { pass: false, reason: 'Output does not match required structured format' };
  }
  if (json.valid === false) return { pass: true };
  const avg = averageScore(json.scores);
  if (avg !== null && avg <= 30) return { pass: true };
  return { pass: false, reason: 'Vague case should be invalid or have average score <= 30' };
}

// 5) Valid cases should be >= 60
async function validateValidAtLeast60({ output, vars }) {
  const { json, err } = parseOutput(output);
  if (err) return { pass: false, reason: err };
  if (vars && vars.kind && vars.kind !== 'valid') {
    return { pass: true };
  }
  if (!isStructured(json)) {
    return { pass: false, reason: 'Output does not match required structured format' };
  }
  if (json.valid !== true) {
    return { pass: false, reason: 'Expected a valid prediction' };
  }
  const avg = averageScore(json.scores);
  if (avg !== null && avg >= 60) return { pass: true };
  return { pass: false, reason: 'Valid case should have average score >= 60' };
}

module.exports = {
  validateJsonShape,
  validateScoreType,
  validateTrivialInvalid,
  validateVagueLowOrInvalid,
  validateValidAtLeast60,
};
