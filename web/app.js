const $ = id => document.getElementById(id);
let state = {}, mutationNonce = '', lastRequest = null, progressTimer = null;

const operationStages = {
  '/api/reset': 'Candidate workspace',
  '/api/rehearse': 'Task execution — then diff measured, tests, and contract proof',
  '/api/correct': 'Contract — then task execution and review',
  '/api/approve': 'Apply — then reverify the exact approved state',
  '/api/rollback': 'Rollback — then verify the original state'
};

const workspaceMessages = {
  ready: 'Preview only — your project has not changed.',
  unsafe: 'Preview only — your project has not changed. Blocked — issues must be fixed.',
  safe: 'Ready for review — no changes applied yet.',
  applied: 'Applied — exact approved preview verified.',
  rolled_back: 'Rollback complete — original state restored.'
};

async function post(path, body = {}) {
  lastRequest = {path, body};
  busy(true);
  beginProgress(path);
  try {
    const response = await fetch(path, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Rehearsal-Nonce': mutationNonce},
      body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) {
      failProgress(path);
      showError(data, path);
      return;
    }
    state = data;
    busy(false);
    endProgress();
    clearError();
    render();
  } catch (error) {
    failProgress(path);
    showError({
      operation: path.replace('/api/', ''), workspace_changed: state.stage === 'applied',
      message: 'Network or response failure; the operation failed closed.',
      detail: error.message, run_id: 'client-' + Date.now().toString(36)
    }, path);
  } finally {
    busy(false);
  }
}

function beginProgress(path) {
  clearTimeout(progressTimer);
  $('progressStage').textContent = operationStages[path] || 'Review';
  progressTimer = setTimeout(() => $('progressPanel').classList.remove('hidden'), 500);
}

function endProgress() {
  clearTimeout(progressTimer);
  $('progressPanel').classList.add('hidden');
}

function failProgress(path) {
  clearTimeout(progressTimer);
  $('progressStage').textContent = `Failed at ${operationStages[path] || 'Review'} — choose a recovery action below`;
  $('progressPanel').classList.remove('hidden');
}

function busy(on) {
  $('app').setAttribute('aria-busy', String(on));
  document.querySelectorAll('button').forEach(button => button.disabled = on);
}

function showError(data, path) {
  $('errorOperation').textContent = data.operation || path.replace('/api/', '');
  $('errorWorkspace').textContent = data.workspace_changed === null ? 'Unknown — recovery could not prove workspace state.' : data.workspace_changed ? 'Changed — last applied state remains authoritative.' : 'Not changed by this failed operation.';
  $('errorMessage').textContent = data.message || 'Operation failed closed.';
  $('errorDetail').textContent = data.detail || data.error || 'No additional detail.';
  $('errorRunId').textContent = data.run_id || 'unavailable';
  $('errorRollback').classList.toggle('hidden', state.stage !== 'applied');
  $('errorPanel').classList.remove('hidden');
  $('errorTitle').focus();
}

function clearError() {
  $('errorPanel').classList.add('hidden');
}

function fileRows(preview) {
  const groups = [
    [preview.added, 'ADDED', 'pass'], [preview.changed, 'CHANGED', ''],
    [preview.deleted, 'DELETED', 'deleted'], [preview.broken_references, 'BROKEN REF', 'fail']
  ];
  return groups.flatMap(([paths, label, className]) => paths.map(path =>
    `<div class="file"><span>${esc(path)}</span><span class="${className}">${label}</span></div>`
  )).join('');
}

function render() {
  $('mode').textContent = state.model_mode || 'MODEL';
  $('workspaceState').textContent = workspaceMessages[state.stage] || workspaceMessages.ready;
  updateTimeline();
  if (!state.preview) {
    $('result').classList.add('hidden');
    $('empty').classList.remove('hidden');
    return;
  }
  $('empty').classList.add('hidden');
  $('result').classList.remove('hidden');
  const preview = state.preview;
  const safe = state.stage === 'safe' || state.stage === 'applied';
  $('iteration').textContent = safe ? '02' : '01';
  $('verdict').textContent = state.stage === 'applied' ? 'Applied state verified' : state.stage === 'rolled_back' ? 'Original state restored' : safe ? 'Contract satisfied' : 'Unsafe consequence found';
  $('badge').textContent = state.stage === 'applied' ? 'VERIFIED' : state.stage === 'rolled_back' ? 'ROLLED BACK' : safe ? 'READY TO APPROVE' : 'BLOCKED';
  $('badge').className = 'badge ' + (safe || state.stage === 'rolled_back' ? 'good' : 'bad');
  $('explanation').textContent = `${preview.explanation} [${preview.explanation_mode}]`;
  $('metrics').innerHTML = `<span class="metric"><strong>${preview.deleted.length}</strong> deleted</span><span class="metric"><strong>${preview.disk_delta}</strong> bytes</span><span class="metric ${preview.tests.passed ? 'pass' : 'fail'}">tests <strong>${preview.tests.passed ? 'PASS' : 'FAIL'}</strong></span>`;
  $('files').innerHTML = fileRows(preview);
  $('intent').textContent = preview.contract.intent;
  $('clauses').innerHTML = preview.contract_proof.clauses.map(clause => `<div class="clause"><span>${esc(clause.clause)}</span><span class="${clause.passed ? 'pass' : 'fail'}">${clause.passed ? 'PASS' : 'VIOLATED'}</span></div>`).join('');
  $('correction').classList.toggle('hidden', state.stage !== 'unsafe');
  $('approve').textContent = `Approve deletion of ${preview.deleted.length} files`;
  $('approve').classList.toggle('hidden', state.stage !== 'safe');
  $('approve').disabled = state.stage !== 'safe' || !preview.tests.passed || !preview.contract_proof.passed;
  $('rollback').classList.toggle('hidden', state.stage !== 'applied');
  $('receipt').classList.toggle('hidden', !state.receipt);
  if (state.receipt) {
    const receipt = state.receipt;
    $('receiptBody').innerHTML = `<dl class="receipt-facts"><div><dt>Transaction</dt><dd><code>${esc(receipt.transaction_id)}</code></dd></div><div><dt>Preview</dt><dd><code>${esc(receipt.preview_id)}</code></dd></div><div><dt>Branch</dt><dd>${esc(receipt.branch)}</dd></div><div><dt>Checks</dt><dd>${receipt.checks_passed}/${receipt.checks_total} passed</dd></div><div><dt>Patch digest</dt><dd><code>${esc(receipt.patch_digest)}</code></dd></div><div><dt>Base state</dt><dd><code>${esc(receipt.base_state_digest)}</code></dd></div><div><dt>Observed state</dt><dd><code>${esc(receipt.observed_state_digest)}</code></dd></div><div><dt>Contract</dt><dd>revision ${receipt.contract_revision} · <code>${esc(receipt.contract_digest)}</code></dd></div><div><dt>Approved</dt><dd>${esc(receipt.approved_at)}</dd></div><div><dt>Rollback</dt><dd>${esc(receipt.rollback)} · ${receipt.rollback_verified ? 'verified' : 'available'}</dd></div></dl>`;
  }
}

function updateTimeline() {
  const active = {ready: 0, unsafe: 5, safe: 5, applied: 7, rolled_back: 8}[state.stage] ?? 0;
  [...$('stageTimeline').children].forEach((item, index) => {
    if (index === active) item.setAttribute('aria-current', 'step');
    else item.removeAttribute('aria-current');
  });
}

function esc(value) {
  const element = document.createElement('div');
  element.textContent = value;
  return element.innerHTML;
}

$('run').onclick = () => post('/api/rehearse', {intent: $('prompt').value});
$('correction').onsubmit = event => {
  event.preventDefault();
  post('/api/correct', {correction: $('fix').value});
};
$('approve').onclick = () => post('/api/approve', {preview_id: state.preview.id, patch_digest: state.preview.patch_digest});
$('rollback').onclick = () => post('/api/rollback');
$('reset').onclick = () => post('/api/reset');
$('errorRetry').onclick = () => lastRequest && post(lastRequest.path, lastRequest.body);
$('errorReset').onclick = () => post('/api/reset');
$('errorRollback').onclick = () => post('/api/rollback');
$('errorDismiss').onclick = clearError;
$('copyDigest').onclick = () => state.receipt && navigator.clipboard.writeText(state.receipt.patch_digest);
$('downloadReceipt').onclick = () => {
  if (!state.receipt) return;
  const blob = new Blob([JSON.stringify(state.receipt, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = `rehearsal-receipt-${state.receipt.id}.json`; link.click();
  URL.revokeObjectURL(url);
};
$('prompt').onkeydown = event => { if (event.key === 'Enter') $('run').click(); };

async function bootstrap() {
  const response = await fetch('/api/state');
  const data = await response.json();
  mutationNonce = data.mutation_nonce;
  await post('/api/reset');
}
bootstrap();
