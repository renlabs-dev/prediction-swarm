/* Promptfoo validators for evaluator JSON outputs */

function parseOutput(output) {
  // output may be a string or an object depending on provider
  if (output == null) return { err: 'No output' };

  if (typeof output === 'object') {
    // If it's already the structured JSON, accept it
    if (
      Object.prototype.hasOwnProperty.call(output, 'valid') &&
      Object.prototype.hasOwnProperty.call(output, 'scores')
    ) {
      return { json: output };
    }
    // Try to extract a text field to parse
    const candidateText =
      (typeof output.outputText === 'string' && output.outputText) ||
      (typeof output.text === 'string' && output.text) ||
      (typeof output.completion === 'string' && output.completion) ||
      (output.message && typeof output.message.content === 'string' && output.message.content) ||
      null;
    if (candidateText) {
      output = candidateText; // fall through to string parsing
    } else {
      return { err: 'Output object does not contain model JSON or a text field' };
    }
  }

  const text = String(output).trim();
  
  // 1) Try direct JSON parse first (strict-only check happens in a separate validator)
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
  if (!obj || typeof obj !== 'object') return false;
  if (typeof obj.valid !== 'boolean') return false;
  if (!Object.prototype.hasOwnProperty.call(obj, 'brief_rationale')) return false;
  // For valid=true, require scores to be an object
  if (obj.valid === true) {
    return obj.scores && typeof obj.scores === 'object';
  }
  // For valid=false, allow scores to be null or an object
  return Object.prototype.hasOwnProperty.call(obj, 'scores') && (obj.scores === null || typeof obj.scores === 'object');
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

// Latest dimension weights (must mirror evaluator config)
const SCORE_WEIGHTS = {
  consequentiality: 0.25,
  actionability: 0.15,
  foresightedness: 0.2,
  resolution_clarity: 0.2,
  verifiability: 0.1,
  conviction: 0.06,
  temporal_horizon: 0.04,
};

// Python-like rounding (bankers rounding for .5 ties), then cast to int
function pythonRound(x) {
  const floor = Math.floor(x);
  const frac = x - floor;
  if (frac !== 0.5) return Math.round(x);
  return floor % 2 === 0 ? floor : floor + 1;
}

function weightedAverage(scores) {
  let total = 0;
  for (const k of SCORE_KEYS) {
    const v = scores[k];
    const w = SCORE_WEIGHTS[k] || 0;
    if (typeof v !== 'number') return null;
    total += v * w;
  }
  // Clamp to [0, 100] and round like the Python evaluator
  const rounded = pythonRound(total);
  return Math.max(0, Math.min(100, rounded));
}

// Average is no longer used for pass/fail, but keep if needed elsewhere
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

  // For valid=true, require scores object with required keys
  // For valid=false, allow scores=null or an object with required keys
  if (json.valid === true || (json.valid === false && json.scores !== null)) {
    for (const key of SCORE_KEYS) {
      if (!Object.prototype.hasOwnProperty.call(json.scores, key)) {
        return { pass: false, reason: `scores.${key} is missing` };
      }
    }
    for (const k of Object.keys(json.scores)) {
      if (!SCORE_KEYS.includes(k)) {
        return { pass: false, reason: `scores contains unexpected key: ${k}` };
      }
    }
  }

  // Enforce only the declared top-level keys
  const topKeys = Object.keys(json);
  const allowedTop = ['valid', 'scores', 'brief_rationale'];
  for (const k of topKeys) {
    if (!allowedTop.includes(k)) {
      return { pass: false, reason: `unexpected top-level key: ${k}` };
    }
  }

  // brief_rationale is required as a string for both valid=true and valid=false
  if (typeof json.brief_rationale !== 'string') {
    return { pass: false, reason: 'brief_rationale must be a string for both valid=true and valid=false' };
  }

  // brief_rationale must be <= 300 words
  const words = json.brief_rationale.trim().split(/\s+/).filter(Boolean);
  if (words.length > 300) {
    return { pass: false, reason: `brief_rationale exceeds 300 words (${words.length})` };
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
  if (valid) {
    // valid=true requires integer scores in range
    for (const key of SCORE_KEYS) {
      const v = scores[key];
      if (typeof v !== 'number' || !isInt(v) || v < 0 || v > 100) {
        return { pass: false, reason: `scores.${key} must be an integer in [0,100] when valid=true` };
      }
    }
  } else {
    // valid=false allows scores to be null entirely, or an object with all nulls
    if (scores === null) return { pass: true };
    for (const key of SCORE_KEYS) {
      const v = scores[key];
      if (v !== null) {
        return { pass: false, reason: `scores.${key} must be null when valid=false` };
      }
    }
  }
  return { pass: true };
}

// 3) Output must be JSON; prefer ONLY JSON, but accept if a parsable JSON object is present without code fences
async function validateOnlyJsonOutput({ output }) {
  if (output == null) return { pass: false, reason: 'No output' };
  if (typeof output === 'object') {
    // Provider may already return parsed JSON or a structured object
    // If it already looks like our schema, accept
    if (
      Object.prototype.hasOwnProperty.call(output, 'valid') &&
      Object.prototype.hasOwnProperty.call(output, 'scores') &&
      Object.prototype.hasOwnProperty.call(output, 'brief_rationale')
    ) {
      return { pass: true };
    }
    // Otherwise, try to locate a text field to validate
    const candidateText =
      (typeof output.outputText === 'string' && output.outputText) ||
      (typeof output.text === 'string' && output.text) ||
      (typeof output.completion === 'string' && output.completion) ||
      (output.message && typeof output.message.content === 'string' && output.message.content) ||
      null;
    if (!candidateText) return { pass: true }; // allow provider object
    output = candidateText;
  }
  const text = String(output);
  const trimmed = text.trim();
  // Try strict parse
  try {
    const maybe = JSON.parse(trimmed);
    if (maybe && typeof maybe === 'object') return { pass: true };
  } catch (_) {}

  // Try fenced code block extraction ```json ... ``` or ``` ... ```
  const fence = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) {
    const inner = fence[1].trim();
    try {
      const obj = JSON.parse(inner);
      if (obj && typeof obj === 'object') return { pass: true };
    } catch (_) {}
  }

  // Try largest braced block
  const first = trimmed.indexOf('{');
  const last = trimmed.lastIndexOf('}');
  if (first !== -1 && last !== -1 && last > first) {
    const candidate = trimmed.slice(first, last + 1).trim();
    try {
      const obj = JSON.parse(candidate);
      if (obj && typeof obj === 'object') return { pass: true };
    } catch (_) {}
  }

  return { pass: false, reason: 'Output must be a single JSON object' };
}

// Exact score match with tolerance (±5 max) using weighted dimensions
async function validateExactScore({ output, vars }) {
  const { json, err } = parseOutput(output);
  if (err) return { pass: false, reason: err };
  if (!isStructured(json)) {
    return { pass: false, reason: 'Output does not match required structured format' };
  }

  if (json.valid !== true) {
    return { pass: false, reason: 'Expected valid=true for scored example' };
  }

  const expected = vars && typeof vars.score === 'number' ? vars.score : null;
  if (expected == null) {
    return { pass: false, reason: 'Missing vars.score for exact score check' };
  }

  const actual = weightedAverage(json.scores);
  if (actual == null) {
    return { pass: false, reason: 'Could not compute weighted score from scores' };
  }

  // Fixed tolerance of ±5
  const TOL = 5;
  const diff = Math.abs(actual - expected);
  if (diff <= TOL) {
    return { pass: true, actual, expected, diff, tolerance: TOL };
  }
  return {
    pass: false,
    actual,
    expected,
    diff,
    tolerance: TOL,
    reason: `Weighted score ${actual} differs from expected ${expected} by ${diff} (tolerance ±${TOL})`,
  };
}

// Invalid cases: require valid=false and all scores=null
async function validateInvalid({ output }) {
  const { json, err } = parseOutput(output);
  if (err) return { pass: false, reason: err };
  if (!isStructured(json)) {
    return { pass: false, reason: 'Output does not match required structured format' };
  }
  if (json.valid !== false) {
    return { pass: false, reason: 'Expected invalid case with valid=false' };
  }
  if (json.scores === null) {
    return { pass: true };
  }
  for (const key of SCORE_KEYS) {
    if (json.scores[key] !== null) {
      return { pass: false, reason: `scores.${key} must be null when valid=false` };
    }
  }
  // brief_rationale must still be a string per schema (shape validator checks this)
  return { pass: true };
}

module.exports = {
  validateOnlyJsonOutput,
  validateJsonShape,
  validateScoreType,
  validateExactScore,
  validateInvalid,
};
